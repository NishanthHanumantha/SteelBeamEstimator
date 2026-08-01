"""
Phase T1 orchestrator — residual-scoped geometric stirrup evidence.
MODEL_VERSION: 9.3.0

Soft-exit when enable_geometry_stirrup_evidence is false.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config_loader import is_enabled, load_config
from .opencv_fallback import detect_ticks_opencv
from .renderer_validation import validate_renderer, write_report
from .residual_targets import (
    included_beam_ids_for_set,
    infer_set_id_from_run_root,
    load_residual_targets,
    target_groups_for_beam,
)
from .vector_stirrup_detector import detect_elevation_ticks, detect_section_rectangles
from .zone_boundary_refiner import parse_type3_spacings, refine_zone_boundaries

MODEL_VERSION = "9.3.0"
PHASE_ID = "T1"
_OUT_NAME = "PhaseT1_geometric_stirrup_evidence"


class PhaseT1Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        run_root: Path,
        output_root: Optional[Path] = None,
    ):
        self.engine_root = Path(engine_root)
        self.run_root = Path(run_root)
        self.output_root = Path(output_root) if output_root else self.run_root / "data" / "output"
        self.out_dir = self.output_root / _OUT_NAME
        self.cfg = load_config(self.engine_root)

    def run(self, *, skip_renderer_validation: bool = False) -> Dict[str, Any]:
        start = time.time()
        self.out_dir.mkdir(parents=True, exist_ok=True)

        if not is_enabled(self.engine_root):
            result = {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "enabled": False,
                "soft_exit": True,
                "success": True,
                "message": "enable_geometry_stirrup_evidence=false — no-op (R6 flag-off)",
                "elapsed_s": round(time.time() - start, 3),
            }
            empty = {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "enabled": False,
                "by_beam": {},
                "note": "flag-off soft-exit — no geometry evidence produced",
            }
            (self.out_dir / "stirrup_geometry_evidence.json").write_text(
                json.dumps(empty, indent=2), encoding="utf-8"
            )
            (self.out_dir / "t1_soft_exit.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            return result

        set_id = infer_set_id_from_run_root(self.run_root)
        targets = load_residual_targets(
            self.engine_root, self.cfg.get("residual_targets_path")
        )
        residual_ids = included_beam_ids_for_set(targets, set_id)
        missing_ids = {
            r["beam_id"]
            for r in (targets.get("rows") or [])
            if r.get("included")
            and r.get("set_id") == set_id
            and r.get("target_group") == "TARGET_MISSING"
        }
        wrong_qty_ids = {
            r["beam_id"]
            for r in (targets.get("rows") or [])
            if r.get("included")
            and r.get("set_id") == set_id
            and r.get("target_group") == "TARGET_WRONG_QTY"
        }

        dxf = self._find_reinforcement_dxf()
        renderer_report = None
        if not skip_renderer_validation and dxf:
            sample_beams = sorted(residual_ids)[:12]
            renderer_report = validate_renderer(
                dxf, engine_src=self.engine_root / "src"
            )
            write_report(
                renderer_report,
                self.out_dir / "t1_1_renderer_validation.json",
            )
            # Also copy summary to Track1_geometric_evidence under engine
            track1 = (
                self.engine_root
                / "data"
                / "output"
                / "Track1_geometric_evidence"
            )
            track1.mkdir(parents=True, exist_ok=True)
            write_report(renderer_report, track1 / "t1_1_renderer_validation.json")
            if not renderer_report.get("all_pass"):
                return {
                    "phase_id": PHASE_ID,
                    "model_version": MODEL_VERSION,
                    "enabled": True,
                    "success": False,
                    "stopped_at": "T1.1",
                    "renderer_validation": renderer_report,
                    "message": "T1.1 renderer validation FAILED — detector not run (R1)",
                    "elapsed_s": round(time.time() - start, 3),
                }

        beam_boxes = self._load_beam_bboxes()
        text_spacing = self._load_text_spacings()
        supports = self._load_supports()

        import ezdxf
        msp = ezdxf.readfile(str(dxf)).modelspace() if dxf else None

        det_cfg = self.cfg.get("detection") or {}
        evidence_by_beam: Dict[str, Dict[str, Any]] = {}
        timings: Dict[str, float] = {}
        opencv_used: List[Dict[str, str]] = []
        rejected_filters: List[Dict[str, Any]] = []

        for beam_id in sorted(residual_ids):
            t0 = time.time()
            bbox = beam_boxes.get(beam_id)
            if not bbox or msp is None:
                evidence_by_beam[beam_id] = {
                    "beam_id": beam_id,
                    "detection_method": "none",
                    "accepted": False,
                    "reject_reason": "missing_bbox_or_dxf",
                    "tick_positions_mm": [],
                    "measured_pitch_mm": [],
                    "zone_count_estimate": 0,
                    "text_spacing_agreement": "no_text_to_compare",
                    "confidence": 0.0,
                    "source_entities": [],
                    "target_groups": target_groups_for_beam(targets, set_id, beam_id),
                }
                timings[beam_id] = round(time.time() - t0, 4)
                continue

            text_sp = text_spacing.get(beam_id)
            elev = detect_elevation_ticks(
                msp, bbox, cfg=det_cfg, text_spacing_mm=text_sp
            )
            elev["beam_id"] = beam_id
            elev["target_groups"] = target_groups_for_beam(targets, set_id, beam_id)

            if elev.get("accepted"):
                evidence_by_beam[beam_id] = elev
            else:
                sec = detect_section_rectangles(msp, bbox)
                if sec.get("accepted"):
                    sec["beam_id"] = beam_id
                    sec["target_groups"] = elev["target_groups"]
                    evidence_by_beam[beam_id] = sec
                elif det_cfg.get("enable_opencv_fallback", True) and dxf:
                    # Render geometry-only crop region approx via full render once cached
                    fb = self._opencv_for_beam(
                        dxf, beam_id, bbox, det_cfg, text_sp,
                        reason=elev.get("reject_reason") or "vector_rejected",
                    )
                    fb["beam_id"] = beam_id
                    fb["target_groups"] = elev["target_groups"]
                    evidence_by_beam[beam_id] = fb
                    if fb.get("accepted"):
                        opencv_used.append(
                            {"beam_id": beam_id, "reason": fb.get("fallback_reason", "")}
                        )
                else:
                    evidence_by_beam[beam_id] = elev
                    rejected_filters.append(
                        {"beam_id": beam_id, "reason": elev.get("reject_reason")}
                    )

            # T1.4 zone refinement artefact (for WRONG_QTY / Type3)
            ev = evidence_by_beam[beam_id]
            label = self._stirrup_label(beam_id)
            spacings = parse_type3_spacings(label or "")
            if not spacings and text_sp:
                spacings = [int(round(text_sp))]
            span = max(bbox[2] - bbox[0], 1.0)
            if beam_id in wrong_qty_ids and len(spacings) >= 2:
                zcfg = self.cfg.get("zone_refinement") or {}
                refined = refine_zone_boundaries(
                    span,
                    spacings,
                    geometry_evidence=ev,
                    supports=supports.get(beam_id),
                    prefer_pitch_change=bool(zcfg.get("prefer_pitch_change", True)),
                    prefer_support_locations=bool(
                        zcfg.get("prefer_support_locations", True)
                    ),
                )
                ev["zone_refinement"] = refined
                ev["type3_spacings_mm"] = spacings
                ev["stirrup_label"] = label

            timings[beam_id] = round(time.time() - t0, 4)

        payload = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now().isoformat(),
            "run_root": str(self.run_root),
            "set_id": set_id,
            "residual_beam_count": len(residual_ids),
            "target_missing_count": len(missing_ids),
            "target_wrong_qty_count": len(wrong_qty_ids),
            "by_beam": evidence_by_beam,
            "opencv_fallback_beams": opencv_used,
            "rejected_by_filter": rejected_filters,
            "timings_s": timings,
            "filter_thresholds": {
                "min_tick_count": det_cfg.get("min_tick_count", 3),
                "pitch_min_mm": det_cfg.get("pitch_min_mm", 50),
                "pitch_max_mm": det_cfg.get("pitch_max_mm", 400),
            },
        }
        out_path = self.out_dir / "stirrup_geometry_evidence.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        # fusion summary placeholder (actual fusion in R21D)
        fusion_hook = {
            "note": "Fusion applied inside R.2.1D when this artefact is present",
            "evidence_path": str(out_path),
            "residual_beam_ids": sorted(residual_ids),
            "target_missing_ids": sorted(missing_ids),
        }
        (self.out_dir / "fusion_hook.json").write_text(
            json.dumps(fusion_hook, indent=2), encoding="utf-8"
        )

        elapsed = round(time.time() - start, 3)
        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "enabled": True,
            "success": True,
            "set_id": set_id,
            "residual_beams": len(residual_ids),
            "accepted_detections": sum(
                1 for v in evidence_by_beam.values() if v.get("accepted")
            ),
            "opencv_fallback_count": len(opencv_used),
            "renderer_validation_pass": (
                None if renderer_report is None else renderer_report.get("all_pass")
            ),
            "output": str(out_path),
            "elapsed_s": elapsed,
            "avg_s_per_beam": round(elapsed / max(len(residual_ids), 1), 4),
        }
        (self.out_dir / "t1_run_summary.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result

    def _find_reinforcement_dxf(self) -> Optional[Path]:
        # Prefer manifest
        man = (
            self.output_root
            / "PhaseVROOT.1_dynamic_pipeline_initialization"
            / "drawing_manifest.json"
        )
        if man.exists():
            data = json.loads(man.read_text(encoding="utf-8"))
            for d in data.get("drawings") or data.get("files") or []:
                if isinstance(d, dict):
                    dt = str(d.get("drawing_type") or d.get("type") or "").upper()
                    p = d.get("path") or d.get("staged_path")
                    if "REINFORCE" in dt and p and Path(p).exists():
                        return Path(p)
        # Fallback glob
        for p in self.run_root.rglob("*.dxf"):
            if "reinforc" in p.name.lower() or "stirrup" in p.name.lower():
                return p
        return None

    def _load_beam_bboxes(self) -> Dict[str, Tuple[float, float, float, float]]:
        """Return beam_id -> (xmin, ymin, xmax, ymax)."""
        out: Dict[str, Tuple[float, float, float, float]] = {}
        # Try geometry contexts / validated geometry / R.1 models
        candidates = [
            self.output_root / "PhaseR1_2A_geometry_accuracy" / "validated_beam_geometry.json",
            self.output_root / "PhaseR3_geometry_context_engine" / "GeometryContexts.json",
            self.output_root
            / "PhaseR.1_generalized_reinforcement_discovery"
            / "beam_reinforcement_models.json",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            out.update(self._extract_bboxes(data))
            if out:
                break

        # Annotation centroids fallback from R.1 annotations
        ann_path = (
            self.output_root
            / "PhaseR.1_generalized_reinforcement_discovery"
            / "reinforcement_annotations.json"
        )
        if ann_path.exists():
            anns = json.loads(ann_path.read_text(encoding="utf-8"))
            by = anns.get("by_beam") or {}
            for bid, items in by.items():
                if bid in out or not items:
                    continue
                xs = [float(a["x"]) for a in items if a.get("x") is not None]
                ys = [float(a["y"]) for a in items if a.get("y") is not None]
                if xs and ys:
                    pad = 1500.0
                    out[bid] = (
                        min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
                    )
        return out

    def _extract_bboxes(self, data: Any) -> Dict[str, Tuple[float, float, float, float]]:
        out: Dict[str, Tuple[float, float, float, float]] = {}

        def consider(bid: str, g: Dict[str, Any]) -> None:
            if not bid or not isinstance(g, dict):
                return
            keys = (
                ("x_min", "y_min", "x_max", "y_max"),
                ("xmin", "ymin", "xmax", "ymax"),
                ("min_x", "min_y", "max_x", "max_y"),
            )
            for a, b, c, d in keys:
                if all(k in g for k in (a, b, c, d)):
                    out[bid] = (
                        float(g[a]), float(g[b]), float(g[c]), float(g[d]),
                    )
                    return
            if "bbox" in g and isinstance(g["bbox"], (list, tuple)) and len(g["bbox"]) == 4:
                bb = g["bbox"]
                out[bid] = (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3]))
                return
            # center + length/depth
            if "start_x" in g and "end_x" in g:
                y = float(g.get("y") or g.get("center_y") or 0)
                depth = float(g.get("depth_mm") or g.get("depth") or 800)
                out[bid] = (
                    float(g["start_x"]), y - depth,
                    float(g["end_x"]), y + depth,
                )

        if isinstance(data, dict):
            if "beams" in data and isinstance(data["beams"], dict):
                for bid, b in data["beams"].items():
                    consider(str(bid), b if isinstance(b, dict) else {})
                    if isinstance(b, dict):
                        consider(str(bid), b.get("geometry") or b.get("bbox") or b)
            if "by_beam" in data and isinstance(data["by_beam"], dict):
                for bid, b in data["by_beam"].items():
                    if isinstance(b, dict):
                        consider(str(bid), b.get("geometry") or b)
            if "models" in data and isinstance(data["models"], list):
                for m in data["models"]:
                    if isinstance(m, dict):
                        consider(str(m.get("beam_id")), m.get("geometry") or m)
            # flat list
            for k, v in data.items():
                if isinstance(v, dict) and (
                    "geometry" in v or "bbox" in v or "x_min" in v or "xmin" in v
                ):
                    consider(str(k), v.get("geometry") or v)
        return out

    def _load_text_spacings(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        ann_path = (
            self.output_root
            / "PhaseR.1_generalized_reinforcement_discovery"
            / "reinforcement_annotations.json"
        )
        if not ann_path.exists():
            return out
        anns = json.loads(ann_path.read_text(encoding="utf-8"))
        for bid, items in (anns.get("by_beam") or {}).items():
            for a in items:
                if str(a.get("role") or "").upper() != "STIRRUP":
                    continue
                sp = a.get("spacing_mm")
                if sp:
                    out[str(bid)] = float(sp)
                    break
                # Type3: take first number as representative for agreement check
                text = str(a.get("clean_text") or "")
                multi = parse_type3_spacings(text)
                if multi:
                    out[str(bid)] = float(multi[0])
                    break
        return out

    def _stirrup_label(self, beam_id: str) -> Optional[str]:
        ann_path = (
            self.output_root
            / "PhaseR.1_generalized_reinforcement_discovery"
            / "reinforcement_annotations.json"
        )
        if not ann_path.exists():
            return None
        anns = json.loads(ann_path.read_text(encoding="utf-8"))
        for a in (anns.get("by_beam") or {}).get(beam_id) or []:
            if str(a.get("role") or "").upper() == "STIRRUP":
                return str(a.get("clean_text") or "")
        return None

    def _load_supports(self) -> Dict[str, List[Dict[str, Any]]]:
        path = (
            self.output_root
            / "PhaseR3_geometry_context_engine"
            / "SupportLocations.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        supports = data.get("supports") or {}
        if isinstance(supports, dict):
            return {str(k): list(v or []) for k, v in supports.items()}
        return {}

    def _opencv_for_beam(
        self,
        dxf: Path,
        beam_id: str,
        bbox: Tuple[float, float, float, float],
        det_cfg: Dict[str, Any],
        text_sp: Optional[float],
        reason: str,
    ) -> Dict[str, Any]:
        import importlib.util
        from PIL import Image

        renderer_path = (
            self.engine_root
            / "src"
            / "PhaseM.1_engineering_vision_dataset"
            / "dxf_renderer.py"
        )
        import sys
        spec = importlib.util.spec_from_file_location("dxf_renderer_t1", renderer_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        sys.modules["dxf_renderer_t1"] = mod
        spec.loader.exec_module(mod)

        png = self.out_dir / "opencv_renders" / f"{beam_id}_notext.png"
        xf = mod.render_dxf_to_png(dxf, png, render_text=False)
        # Crop to beam bbox in pixel space
        x0, y0, x1, y1 = bbox
        corners = [
            xf.dxf_to_pixel(x0, y0), xf.dxf_to_pixel(x1, y0),
            xf.dxf_to_pixel(x0, y1), xf.dxf_to_pixel(x1, y1),
        ]
        pxs = [c[0] for c in corners]
        pys = [c[1] for c in corners]
        left, right = int(max(0, min(pxs))), int(min(xf.img_w, max(pxs)))
        top, bottom = int(max(0, min(pys))), int(min(xf.img_h, max(pys)))
        if right - left < 10 or bottom - top < 10:
            return detect_ticks_opencv(
                png, cfg=det_cfg, text_spacing_mm=text_sp,
                mm_per_px=None, fallback_reason=reason,
            )
        img = Image.open(png)
        crop = img.crop((left, top, right, bottom))
        crop_path = self.out_dir / "opencv_renders" / f"{beam_id}_crop.png"
        crop_path.parent.mkdir(parents=True, exist_ok=True)
        crop.save(crop_path)
        x_range = xf.dxf_xlim[1] - xf.dxf_xlim[0]
        mm_per_px = x_range / max(xf.img_w, 1)
        return detect_ticks_opencv(
            crop_path,
            cfg=det_cfg,
            text_spacing_mm=text_sp,
            mm_per_px=mm_per_px,
            fallback_reason=reason,
        )
