"""
Phase T1.8.3 orchestrator — Shared Engineering Ownership.
MODEL_VERSION: 9.5.3
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PhaseT181_beam_render_validation.comparison_engine import (
    make_diff_image,
    make_side_by_side,
)
from PhaseT181_beam_render_validation.image_exporter import export_manual_image
from PhaseT181_beam_render_validation.ownership_renderer import render_owned_beam
from PhaseT182_adaptive_render_extent.render_extent_builder import (
    apply_extent_to_scoped_copy,
    build_render_extent,
)

from .engineering_scope_builder import build_engineering_scopes
from .multi_owner_assignment import assign_multi_owners
from .ownership_diff_report import write_ownership_diff, write_shared_ownership_qa
from .ownership_merger import merge_beam_ownership
from .shared_annotation_registry import build_registry
from .shared_render_adapter import build_effective_scoped
from .shared_scope_detector import detect_shared_candidates
from .shared_scope_validator import validate_shared_ownership

MODEL_VERSION = "9.5.3"
PHASE_ID = "T1.8.3"
_OUT_NAME = "PhaseT183_shared_engineering_ownership"
FOCUS = ["B8", "B9", "B10"]


class PhaseT183Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        run_root: Path,
        output_root: Optional[Path] = None,
        *,
        enable_shared_ownership: bool = True,
    ):
        self.engine_root = Path(engine_root)
        self.run_root = Path(run_root)
        self.output_root = (
            Path(output_root) if output_root else self.run_root / "data" / "output"
        )
        self.out_dir = self.output_root / _OUT_NAME
        self.enable_shared = enable_shared_ownership

    def run(self, *, beam_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        rendered_dir = self.out_dir / "RenderedBeams"
        compare_dir = self.out_dir / "Comparison"
        diff_dir = self.out_dir / "Diff"
        for d in (rendered_dir, compare_dir, diff_dir, self.out_dir):
            d.mkdir(parents=True, exist_ok=True)

        graph_path = (
            self.output_root / "PhaseT17_annotation_graph" / "AnnotationGraph.json"
        )
        own_path = (
            self.output_root / "PhaseT18_beam_ownership" / "BeamOwnership.json"
        )
        scoped_path = (
            self.output_root / "PhaseT18_beam_ownership" / "BeamScopedAnnotations.json"
        )
        if not graph_path.exists() or not own_path.exists() or not scoped_path.exists():
            return {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "T1.7/T1.8 artefacts missing",
            }

        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        own_doc = json.loads(own_path.read_text(encoding="utf-8"))
        scoped_doc = json.loads(scoped_path.read_text(encoding="utf-8"))
        envelopes = self._load_envelopes()
        inv_by_h = self._load_inventory_index()

        ownership_by_beam = own_doc.get("by_beam") or {}
        ids = list(beam_ids) if beam_ids else sorted(ownership_by_beam.keys())

        print(f"[T1.8.3] Detect shared SFR (enable={self.enable_shared})...")
        candidates = detect_shared_candidates(
            graph=graph, ownership_by_beam=ownership_by_beam
        )
        scopes = build_engineering_scopes(candidates, envelopes)
        shared_anns = (
            assign_multi_owners(scopes, candidates) if self.enable_shared else []
        )
        registry = build_registry(shared_anns)

        merges: Dict[str, Dict[str, Any]] = {}
        legacy_owned = {}
        for bid in ids:
            own = ownership_by_beam.get(bid) or {}
            legacy_owned[bid] = len(own.get("accepted_annotations") or [])
            merges[bid] = merge_beam_ownership(
                bid,
                own,
                registry.get("by_beam") or {},
                enable_shared=self.enable_shared,
            )

        # Persist engineering artefacts (additive; never overwrite T1.8)
        generated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        (self.out_dir / "EngineeringScopes.json").write_text(
            json.dumps(
                {
                    "model_version": MODEL_VERSION,
                    "scopes": scopes,
                    "candidate_count": len(candidates),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (self.out_dir / "SharedAnnotationRegistry.json").write_text(
            json.dumps(registry, indent=2), encoding="utf-8"
        )
        (self.out_dir / "MergedOwnership.json").write_text(
            json.dumps(
                {"model_version": MODEL_VERSION, "by_beam": merges}, indent=2
            ),
            encoding="utf-8",
        )

        render_texts: Dict[str, List[str]] = {}
        # Render focus beams + full set for regression evidence
        render_ids = list(dict.fromkeys(list(FOCUS) + list(ids)))
        for bid in render_ids:
            if bid not in ownership_by_beam:
                continue
            print(f"[T1.8.3] Effective render {bid}...")
            base_scoped = (scoped_doc.get("by_beam") or {}).get(bid) or {
                "beam_id": bid,
                "nodes": [],
                "edges": [],
                "annotations": [],
            }
            effective = build_effective_scoped(
                bid,
                base_scoped,
                merges[bid],
                graph,
                enable_shared=self.enable_shared,
            )
            extent = build_render_extent(
                bid, effective, inventory_by_handle=inv_by_h
            )
            if extent.get("success"):
                effective = apply_extent_to_scoped_copy(
                    effective, extent["computed_render_bbox"]
                )

            render_path = rendered_dir / f"{bid}_render.png"
            manual_path = compare_dir / f"{bid}_manual.png"
            side_path = compare_dir / f"{bid}_side_by_side.png"
            diff_path = diff_dir / f"{bid}_diff.png"

            export_manual_image(
                engine_root=self.engine_root,
                run_root=self.run_root,
                output_root=self.output_root,
                beam_id=bid,
                dest=manual_path,
            )
            rend = render_owned_beam(
                engine_root=self.engine_root,
                run_root=self.run_root,
                output_root=self.output_root,
                beam_id=bid,
                scoped=effective,
                out_path=render_path,
                inventory_by_handle=inv_by_h,
            )
            if rend.get("success"):
                try:
                    (compare_dir / f"{bid}_render.png").write_bytes(
                        render_path.read_bytes()
                    )
                except OSError:
                    pass
                make_side_by_side(
                    manual_path, render_path, side_path, beam_id=bid
                )
                make_diff_image(manual_path, render_path, diff_path, beam_id=bid)
                render_texts[bid] = list(
                    rend.get("rendered_annotation_texts") or []
                )
                print(
                    f"  {bid} owned={merges[bid]['counts']['owned']} "
                    f"shared={merges[bid]['counts']['shared']} "
                    f"eff={merges[bid]['counts']['effective']} "
                    f"render_sfr={any('SIDE' in (t or '').upper() for t in render_texts[bid])}"
                )
            else:
                print(f"  render failed: {rend}")
                render_texts[bid] = [
                    a.get("text") or ""
                    for a in merges[bid].get("effective_annotations") or []
                ]

        validation = validate_shared_ownership(
            scopes=scopes,
            merges=merges,
            registry=registry,
            render_texts=render_texts,
            legacy_owned_counts=legacy_owned,
            enable_shared=self.enable_shared,
        )

        write_shared_ownership_qa(
            self.out_dir / "SharedOwnershipQA.json",
            merges,
            generated_at=generated_at,
            validation=validation,
        )
        write_ownership_diff(
            self.out_dir / "OwnershipDiff.md",
            merges,
            generated_at=generated_at,
            focus=FOCUS,
        )

        # Copy package docs into out dir
        pkg = Path(__file__).resolve().parent
        for name in ("README.md", "Architecture.md"):
            src = pkg / name
            if src.exists():
                shutil.copy2(src, self.out_dir / name)

        summary = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": generated_at,
            "success": True,
            "out_dir": str(self.out_dir),
            "enable_shared_ownership": self.enable_shared,
            "shared_scope_count": sum(1 for s in scopes if s.get("shared")),
            "validation": validation.get("visual_validation"),
            "checks": validation.get("checks"),
            "focus": {
                bid: merges.get(bid, {}).get("counts") for bid in FOCUS
            },
        }
        (self.out_dir / "t183_run_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return summary

    def _load_envelopes(self) -> Dict[str, Dict[str, Any]]:
        path = (
            self.output_root
            / "PhaseT1_geometric_stirrup_evidence"
            / "geometry_envelopes.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): v for k, v in (data.get("by_beam") or {}).items()}

    def _load_inventory_index(self) -> Dict[str, Dict[str, Any]]:
        path = self.output_root / "PhaseT16_entity_ownership" / "entity_inventory.json"
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            str(e["entity_handle"]).upper(): e
            for e in (data.get("entities") or [])
            if e.get("entity_handle")
        }
