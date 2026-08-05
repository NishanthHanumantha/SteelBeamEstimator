"""
Phase T1.8.2 orchestrator — Adaptive Beam Render Extent.
MODEL_VERSION: 9.5.2
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PhaseT181_beam_render_validation.comparison_engine import (
    make_diff_image,
    make_side_by_side,
)
from PhaseT181_beam_render_validation.image_exporter import export_manual_image
from PhaseT181_beam_render_validation.ownership_renderer import render_owned_beam

from .render_extent_builder import (
    apply_extent_to_scoped_copy,
    build_render_extent,
)
from .render_extent_qa import (
    write_qa_report,
    write_render_extent_qa_json,
    write_visual_summary,
)
from .visibility_validator import validate_regression_vs_t181, validate_visibility

MODEL_VERSION = "9.5.2"
PHASE_ID = "T1.8.2"
_OUT_NAME = "PhaseT182_adaptive_render_extent"


class PhaseT182Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        run_root: Path,
        output_root: Optional[Path] = None,
    ):
        self.engine_root = Path(engine_root)
        self.run_root = Path(run_root)
        self.output_root = (
            Path(output_root) if output_root else self.run_root / "data" / "output"
        )
        self.out_dir = self.output_root / _OUT_NAME

    def run(self, *, beam_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        rendered_dir = self.out_dir / "RenderedBeams"
        compare_dir = self.out_dir / "Comparison"
        diff_dir = self.out_dir / "Diff"
        qa_dir = self.out_dir / "QA"
        for d in (rendered_dir, compare_dir, diff_dir, qa_dir, self.out_dir):
            d.mkdir(parents=True, exist_ok=True)

        scoped_path = (
            self.output_root / "PhaseT18_beam_ownership" / "BeamScopedAnnotations.json"
        )
        if not scoped_path.exists():
            return {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "BeamScopedAnnotations.json missing",
            }
        scoped_doc = json.loads(scoped_path.read_text(encoding="utf-8"))
        t181 = self._load_t181_validation()
        inv_by_h = self._load_inventory_index()

        ids = list(beam_ids) if beam_ids else sorted(
            (scoped_doc.get("by_beam") or {}).keys()
        )
        rows: List[Dict[str, Any]] = []
        extent_qa: Dict[str, Any] = {}

        for bid in ids:
            scoped = (scoped_doc.get("by_beam") or {}).get(bid)
            if not scoped:
                continue
            print(f"[T1.8.2] Adaptive extent {bid}...")

            extent = build_render_extent(
                bid, scoped, inventory_by_handle=inv_by_h
            )
            vis = validate_visibility(extent)
            if not extent.get("success"):
                print(f"  extent failed: {extent}")
                rows.append(
                    {
                        "beam_id": bid,
                        "extent": extent,
                        "visibility": vis,
                        "regression": {"regression_ok": False},
                    }
                )
                extent_qa[bid] = {**extent, **vis}
                continue

            scoped_adapt = apply_extent_to_scoped_copy(
                scoped, extent["computed_render_bbox"]
            )

            render_path = rendered_dir / f"{bid}_render.png"
            manual_path = compare_dir / f"{bid}_manual.png"
            side_path = compare_dir / f"{bid}_side_by_side.png"
            render_copy = compare_dir / f"{bid}_render.png"
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
                scoped=scoped_adapt,
                out_path=render_path,
                inventory_by_handle=inv_by_h,
            )
            if not rend.get("success"):
                print(f"  render failed: {rend}")
                continue

            try:
                render_copy.write_bytes(render_path.read_bytes())
            except OSError:
                pass

            make_side_by_side(manual_path, render_path, side_path, beam_id=bid)
            diff = make_diff_image(manual_path, render_path, diff_path, beam_id=bid)

            reg = validate_regression_vs_t181(
                bid,
                t182_render_counts=rend.get("counts") or {},
                t181_validation=(t181.get("by_beam") or {}).get(bid),
                t182_ann_texts=list(rend.get("rendered_annotation_texts") or []),
            )

            overall = (
                "PASS"
                if vis.get("visual_validation") == "PASS" and reg.get("regression_ok")
                else "FAIL"
            )
            row = {
                "beam_id": bid,
                "extent": extent,
                "visibility": vis,
                "regression": reg,
                "render": rend,
                "diff": diff,
                "overall": overall,
                "artefacts": {
                    "manual": str(manual_path),
                    "render": str(render_path),
                    "side_by_side": str(side_path),
                    "diff": str(diff_path),
                },
            }
            rows.append(row)
            extent_qa[bid] = {
                "beam": bid,
                "computed_render_bbox": extent.get("computed_render_bbox"),
                "beam_bbox": extent.get("beam_bbox"),
                "owned_union_bbox": extent.get("owned_union_bbox"),
                "margin_applied": extent.get("margin_applied"),
                "visibility_failures": vis.get("visibility_failures"),
                "objects_touching_border": vis.get("objects_touching_border"),
                "largest_margin_used": extent.get("largest_margin_used"),
                "annotation_clipped": vis.get("annotation_clipped"),
                "leader_clipped": vis.get("leader_clipped"),
                "text_bbox_outside_image": vis.get("text_bbox_outside_image"),
                "arrowhead_outside_image": vis.get("arrowhead_outside_image"),
                "render_bbox_contains_all_owned_objects": vis.get(
                    "render_bbox_contains_all_owned_objects"
                ),
                "visual_validation": vis.get("visual_validation"),
                "regression_ok": reg.get("regression_ok"),
                "overall": overall,
            }
            print(
                f"  {bid} -> {overall} "
                f"vis={vis.get('visual_validation')} "
                f"reg={reg.get('regression_ok')} "
                f"ymax {extent['beam_bbox'][3] if extent.get('beam_bbox') else '?'} "
                f"-> {extent['computed_render_bbox'][3]:.1f}"
            )

        generated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        write_render_extent_qa_json(
            self.out_dir / "RenderExtentQA.json", extent_qa, generated_at
        )
        write_render_extent_qa_json(
            qa_dir / "RenderExtentQA.json", extent_qa, generated_at
        )
        write_qa_report(
            self.out_dir / "T182_ADAPTIVE_EXTENT_QA_REPORT.md",
            rows=rows,
            generated_at=generated_at,
            out_dir=self.out_dir,
        )
        write_qa_report(
            qa_dir / "T182_ADAPTIVE_EXTENT_QA_REPORT.md",
            rows=rows,
            generated_at=generated_at,
            out_dir=self.out_dir,
        )
        write_visual_summary(
            self.out_dir / "T182_VISUAL_SUMMARY.md",
            rows=rows,
            generated_at=generated_at,
        )
        write_visual_summary(
            qa_dir / "T182_VISUAL_SUMMARY.md",
            rows=rows,
            generated_at=generated_at,
        )

        summary = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": generated_at,
            "out_dir": str(self.out_dir),
            "beam_count": len(rows),
            "pass_count": sum(1 for r in rows if r.get("overall") == "PASS"),
            "fail_count": sum(1 for r in rows if r.get("overall") != "PASS"),
            "visibility_pass": sum(
                1 for r in rows if r["visibility"]["visual_validation"] == "PASS"
            ),
            "regression_pass": sum(
                1 for r in rows if (r.get("regression") or {}).get("regression_ok")
            ),
        }
        (self.out_dir / "t182_run_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return {"success": True, **summary, "rows": rows}

    def _load_t181_validation(self) -> Dict[str, Any]:
        path = (
            self.output_root / "PhaseT181_render_validation" / "RenderValidation.json"
        )
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

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
