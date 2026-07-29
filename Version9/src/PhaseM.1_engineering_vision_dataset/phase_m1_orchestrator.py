"""
phase_m1_orchestrator.py — Orchestrate Phase M.1 Engineering Vision Dataset.

Entry point for the Vision Dataset Generator.  Coordinates:
  1. Read deterministic pipeline outputs (beam registry, annotations, geometry).
  2. Render the DXF drawing to a full high-resolution PNG.
  3. For every discovered beam:
       a. Compute DXF bounding box (with configurable padding).
       b. Crop beam image from the full render.
       c. Build annotation JSON from R.1 / R.1.3 outputs.
       d. Build per-beam metadata.
       e. Generate quality-inspection preview image.
       f. Write all artefacts to the dataset directory.
  4. Build dataset_manifest.json.
  5. Validate dataset and write dataset_validation.json.
  6. Return a summary dict.

Design principles:
  - DOES NOT modify engineering logic or production pipeline.
  - ALL labels come from deterministic pipeline outputs only.
  - Full engineering traceability on every annotation.
  - Dataset is self-contained; no dependency on web_runs artefacts.

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.0.0"   # keep in sync with __init__.py

from .pipeline_reader   import PipelineReader
from .dxf_renderer      import render_dxf_to_png, CoordTransform
from .beam_cropper      import compute_beam_dxf_bbox, crop_beam_image, DEFAULT_PADDING_MM
from .annotation_builder import build_annotation_json
from .metadata_builder  import build_beam_metadata
from .preview_generator import generate_preview
from .manifest_builder  import build_manifest
from .dataset_validator import validate_dataset
from .dataset_exporter  import (
    create_dataset_dirs,
    image_path, annotation_path, metadata_path, preview_path,
    manifest_path, validation_path,
    write_json,
)


def _run_id() -> str:
    """Generate a timestamp-based run identifier."""
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")


def _resolve_dxf(
    dxf_hint:    Optional[Path],
    data_dict:   Dict[str, Any],
    engine_root: Path,
) -> Optional[Path]:
    """
    Resolve the DXF file to render.

    Priority:
      1. Explicit --dxf-path argument.
      2. 'reinforcement' or 'drawings.reinforcement' from beam_registry.
      3. First *.dxf found in engine_root/data/framing/ or data/Benchmark_Set_*/reinforcement/.
    """
    if dxf_hint and dxf_hint.exists():
        return dxf_hint

    drawings = data_dict.get("drawings") or {}
    for key in ("reinforcement", "framing"):
        candidate = drawings.get(key)
        if candidate:
            p = Path(candidate)
            if p.exists():
                return p
            # Try relative to engine_root
            p2 = engine_root / candidate
            if p2.exists():
                return p2

    # Auto-discover
    for glob_pattern in (
        "data/Benchmark_Set_*/reinforcement/*.dxf",
        "data/framing/*.dxf",
        "data/**/*.dxf",
    ):
        found = sorted(engine_root.glob(glob_pattern))
        if found:
            return found[0]

    return None


class PhaseM1Orchestrator:
    """
    Phase M.1 Engineering Vision Dataset Generator.

    Parameters
    ----------
    engine_root     : Version9 directory (contains src/, data/, Run_PY/).
    output_root     : pipeline data/output/ directory with prior phase results.
    dxf_path        : optional explicit path to the DXF file to render.
    dataset_root    : optional explicit output location for the vision dataset.
                      Defaults to engine_root/data/vision_dataset/<run_id>/.
    padding_mm      : crop padding around each beam in DXF units (mm).
    """

    def __init__(
        self,
        engine_root:  Path,
        output_root:  Path,
        dxf_path:     Optional[Path]  = None,
        dataset_root: Optional[Path]  = None,
        padding_mm:   float           = DEFAULT_PADDING_MM,
    ) -> None:
        self.engine_root  = Path(engine_root).resolve()
        self.output_root  = Path(output_root).resolve()
        self.dxf_path_hint = Path(dxf_path).resolve() if dxf_path else None
        self.padding_mm   = padding_mm

        # Determine dataset root
        if dataset_root:
            self.dataset_root = Path(dataset_root).resolve()
        else:
            self.run_id = _run_id()
            self.dataset_root = (
                self.engine_root / "data" / "vision_dataset" / self.run_id
            )

        if not hasattr(self, "run_id"):
            self.run_id = self.dataset_root.name

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """
        Execute Phase M.1 and return a summary dict.

        Raises RuntimeError if a critical step (DXF rendering) fails.
        Non-critical failures (individual beam crop errors) are captured
        as warnings and processing continues.
        """
        print(f"\n{'='*70}")
        print(f"  Phase M.1 — Engineering Vision Dataset Generator")
        print(f"  MODEL_VERSION : {MODEL_VERSION}")
        print(f"  Run ID        : {self.run_id}")
        print(f"  Dataset root  : {self.dataset_root}")
        print(f"{'='*70}\n")

        # ── Step 1: Load pipeline data ─────────────────────────────────────────
        print("[M.1] Loading pipeline outputs …")
        reader    = PipelineReader(self.output_root)
        data      = reader.load()
        beam_ids  = data["beam_ids"]
        available = data["available"]

        print(f"       Phases available : {available}")
        print(f"       Beams discovered : {len(beam_ids)}")

        if not beam_ids:
            raise RuntimeError(
                "No beams found in pipeline outputs. "
                "Ensure VROOT.1 has been run and beam_registry.json exists."
            )

        # ── Step 2: Resolve DXF file ───────────────────────────────────────────
        print("[M.1] Resolving DXF file …")
        dxf_path = _resolve_dxf(self.dxf_path_hint, data, self.engine_root)
        if dxf_path is None:
            raise RuntimeError(
                "Cannot locate a DXF file to render. "
                "Pass --dxf-path explicitly or ensure a DXF exists under "
                "data/framing/ or data/Benchmark_Set_*/reinforcement/."
            )
        print(f"       DXF : {dxf_path}")

        # ── Step 3: Create dataset directory tree ─────────────────────────────
        create_dataset_dirs(self.dataset_root)
        print(f"[M.1] Dataset directory ready: {self.dataset_root}")

        # ── Step 4: Render full DXF → PNG ─────────────────────────────────────
        full_render_path = self.dataset_root / "_full_render.png"
        print("[M.1] Rendering DXF (vector, matplotlib backend) …")
        try:
            transform = render_dxf_to_png(dxf_path, full_render_path)
        except Exception as exc:
            raise RuntimeError(f"DXF rendering failed: {exc}") from exc
        print(f"       Full render size : {transform.img_w} × {transform.img_h} px")

        # ── Step 5: Per-beam processing ────────────────────────────────────────
        print(f"[M.1] Processing {len(beam_ids)} beams …\n")

        ann_jsons:   List[Dict[str, Any]] = []
        metadatas:   List[Dict[str, Any]] = []
        beam_errors: List[str]            = []

        for beam_id in beam_ids:
            try:
                self._process_beam(
                    beam_id      = beam_id,
                    data         = data,
                    dxf_path     = dxf_path,
                    transform    = transform,
                    full_render  = full_render_path,
                    ann_jsons    = ann_jsons,
                    metadatas    = metadatas,
                )
            except Exception as exc:
                msg = f"Beam {beam_id} FAILED: {exc}"
                print(f"  [WARN] {msg}")
                beam_errors.append(msg)

        print(f"\n[M.1] Beam processing complete: "
              f"{len(ann_jsons)} succeeded, {len(beam_errors)} failed.\n")

        # ── Step 6: Dataset manifest ───────────────────────────────────────────
        print("[M.1] Building dataset manifest …")
        manifest = build_manifest(
            run_id          = self.run_id,
            drawing_files   = [dxf_path.name],
            ann_jsons       = ann_jsons,
            metadatas       = metadatas,
            full_image_size = (transform.img_w, transform.img_h),
        )
        write_json(manifest_path(self.dataset_root), manifest)

        # ── Step 7: Dataset validation ─────────────────────────────────────────
        print("[M.1] Validating dataset …")
        validation = validate_dataset(self.dataset_root, beam_ids)
        write_json(validation_path(self.dataset_root), validation)

        status = validation["validation_status"]
        print(f"       Validation : {status}  "
              f"({validation['error_count']} errors, "
              f"{validation['warning_count']} warnings)")

        # ── Step 8: Summary ────────────────────────────────────────────────────
        summary = self._build_summary(
            manifest    = manifest,
            validation  = validation,
            beam_errors = beam_errors,
        )
        self._print_summary(summary)

        return summary

    # ── Internal per-beam processing ──────────────────────────────────────────

    def _process_beam(
        self,
        beam_id:     str,
        data:        Dict[str, Any],
        dxf_path:    Path,
        transform:   CoordTransform,
        full_render: Path,
        ann_jsons:   List[Dict[str, Any]],
        metadatas:   List[Dict[str, Any]],
    ) -> None:
        beam_entry = (data["beams"] or {}).get(beam_id) or {}
        axis_entry = (data["axes"]  or {}).get(beam_id)
        ann_list   = (data["annotations"] or {}).get(beam_id) or []
        prod_entry = (data["prod_bars"]   or {}).get(beam_id)

        # 5a — Compute DXF bounding box
        dxf_bbox = compute_beam_dxf_bbox(
            beam_id    = beam_id,
            beam_entry = beam_entry,
            axis_entry = axis_entry,
            padding_mm = self.padding_mm,
        )

        img_p      = image_path(self.dataset_root, beam_id)
        ann_p      = annotation_path(self.dataset_root, beam_id)
        meta_p     = metadata_path(self.dataset_root, beam_id)
        preview_p  = preview_path(self.dataset_root, beam_id)

        # 5b — Crop beam image
        crop = None
        if dxf_bbox is not None:
            crop = crop_beam_image(
                full_image_path = full_render,
                beam_id         = beam_id,
                dxf_bbox        = dxf_bbox,
                transform       = transform,
                output_path     = img_p,
            )
            pixel_bbox = crop.pixel_bbox
            image_size = crop.image_size
        else:
            # No geometry — copy full render as fallback
            import shutil
            shutil.copy2(str(full_render), str(img_p))
            pixel_bbox = (0, 0, transform.img_w, transform.img_h)
            image_size = (transform.img_w, transform.img_h)
            dxf_bbox   = (
                transform.dxf_xlim[0], transform.dxf_ylim[0],
                transform.dxf_xlim[1], transform.dxf_ylim[1],
            )

        # 5c — Annotation JSON
        ann_json = build_annotation_json(
            beam_id      = beam_id,
            ann_list     = ann_list,
            prod_entry   = prod_entry,
            dxf_bbox     = dxf_bbox,
            pixel_bbox   = pixel_bbox,
            image_file   = img_p.name,
            drawing_file = dxf_path.name,
            transform    = transform,
        )
        write_json(ann_p, ann_json)
        ann_jsons.append(ann_json)

        # 5d — Metadata
        meta = build_beam_metadata(
            beam_id         = beam_id,
            beam_entry      = beam_entry,
            axis_entry      = axis_entry,
            annotation_json = ann_json,
            image_file      = img_p.name,
            drawing_file    = dxf_path.name,
            dxf_source      = str(dxf_path),
            dxf_bbox        = dxf_bbox,
            pixel_bbox      = pixel_bbox,
            image_size_px   = image_size,
        )
        write_json(meta_p, meta)
        metadatas.append(meta)

        # 5e — Preview image
        try:
            generate_preview(
                beam_crop_path  = img_p,
                annotation_json = ann_json,
                output_path     = preview_p,
            )
        except Exception:
            pass   # preview failure is non-critical

        ann_count = ann_json.get("annotation_count", 0)
        print(f"  ✓ {beam_id:8s}  {ann_count:3d} annotations  crop={pixel_bbox}")

    # ── Summary helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_summary(
        manifest:    Dict[str, Any],
        validation:  Dict[str, Any],
        beam_errors: List[str],
    ) -> Dict[str, Any]:
        return {
            "model_version":     MODEL_VERSION,
            "beam_count":        manifest["beam_count"],
            "image_count":       manifest["image_count"],
            "annotation_count":  manifest["annotation_count"],
            "roles":             manifest["roles"],
            "validation_status": validation["validation_status"],
            "error_count":       validation["error_count"],
            "warning_count":     validation["warning_count"],
            "beam_errors":       beam_errors,
        }

    @staticmethod
    def _print_summary(s: Dict[str, Any]) -> None:
        print(f"\n{'='*70}")
        print(f"  Phase M.1 — Complete")
        print(f"  Beams         : {s['beam_count']}")
        print(f"  Images        : {s['image_count']}")
        print(f"  Annotations   : {s['annotation_count']}")
        print(f"  Roles         : {list(s['roles'].keys())}")
        print(f"  Validation    : {s['validation_status']}")
        if s["error_count"]:
            print(f"  Errors        : {s['error_count']}")
        if s["warning_count"]:
            print(f"  Warnings      : {s['warning_count']}")
        if s["beam_errors"]:
            print(f"  Beam failures : {len(s['beam_errors'])}")
        print(f"{'='*70}\n")
