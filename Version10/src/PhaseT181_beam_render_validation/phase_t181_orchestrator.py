"""
Phase T1.8.1 orchestrator — Beam Ownership Render Validation.
MODEL_VERSION: 9.5.1
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .comparison_engine import make_diff_image, make_side_by_side
from .image_exporter import export_manual_image
from .ownership_renderer import render_owned_beam
from .qa_report import write_qa_report, write_visual_summary
from .validation_engine import validate_render

MODEL_VERSION = "9.5.1"
PHASE_ID = "T1.8.1"
_OUT_NAME = "PhaseT181_render_validation"


class PhaseT181Orchestrator:
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
        own_path = (
            self.output_root / "PhaseT18_beam_ownership" / "BeamOwnership.json"
        )
        if not scoped_path.exists() or not own_path.exists():
            return {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "T1.8 artefacts missing — run T1.8 first",
            }

        scoped_doc = json.loads(scoped_path.read_text(encoding="utf-8"))
        own_doc = json.loads(own_path.read_text(encoding="utf-8"))
        inv_by_h = self._load_inventory_index()

        ids = list(beam_ids) if beam_ids else sorted(
            (own_doc.get("by_beam") or {}).keys()
        )
        rows: List[Dict[str, Any]] = []
        validations: List[Dict[str, Any]] = []

        for bid in ids:
            scoped = (scoped_doc.get("by_beam") or {}).get(bid)
            ownership = (own_doc.get("by_beam") or {}).get(bid)
            if not scoped or not ownership:
                print(f"[T1.8.1] skip {bid}: missing scoped/ownership")
                continue
            print(f"[T1.8.1] Render validation {bid}...")

            render_path = rendered_dir / f"{bid}_render.png"
            manual_path = compare_dir / f"{bid}_manual.png"
            side_path = compare_dir / f"{bid}_side_by_side.png"
            # Also place render copy next to manual for prompt layout
            render_copy = compare_dir / f"{bid}_render.png"
            diff_path = diff_dir / f"{bid}_diff.png"

            man = export_manual_image(
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
                scoped=scoped,
                out_path=render_path,
                inventory_by_handle=inv_by_h,
            )
            if not rend.get("success"):
                print(f"  render failed: {rend}")
                continue

            # Mirror render into Comparison/
            try:
                render_copy.write_bytes(render_path.read_bytes())
            except OSError:
                pass

            side = make_side_by_side(
                manual_path, render_path, side_path, beam_id=bid
            )
            diff = make_diff_image(
                manual_path, render_path, diff_path, beam_id=bid
            )

            artefacts = {
                "manual": str(manual_path),
                "render": str(render_path),
                "side_by_side": str(side_path),
                "diff": str(diff_path),
            }
            val = validate_render(
                bid,
                ownership=ownership,
                render_info=rend,
                comparison_path=str(side_path),
                diff_info=diff,
                artefact_paths=artefacts,
            )
            validations.append(val)
            rows.append(
                {
                    "beam_id": bid,
                    "manual": man,
                    "render": rend,
                    "side_by_side": side,
                    "diff": diff,
                    "validation": val,
                }
            )
            print(
                f"  {bid} -> {val['visual_validation']} "
                f"ann={len(val['rendered_annotations'])} "
                f"miss={val['missing_annotations']} "
                f"extra={val['unexpected_annotations']}"
            )

        generated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        render_val_doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": generated_at,
            "by_beam": {v["beam"]: v for v in validations},
        }
        (self.out_dir / "RenderValidation.json").write_text(
            json.dumps(render_val_doc, indent=2), encoding="utf-8"
        )
        (qa_dir / "RenderValidation.json").write_text(
            json.dumps(render_val_doc, indent=2), encoding="utf-8"
        )

        write_qa_report(
            qa_dir / "T181_RENDER_VALIDATION_QA_REPORT.md",
            rows=rows,
            generated_at=generated_at,
            out_dir=self.out_dir,
        )
        write_visual_summary(
            qa_dir / "T181_VISUAL_SUMMARY.md",
            rows=rows,
            generated_at=generated_at,
        )
        # Mirror top-level copies
        write_qa_report(
            self.out_dir / "T181_RENDER_VALIDATION_QA_REPORT.md",
            rows=rows,
            generated_at=generated_at,
            out_dir=self.out_dir,
        )
        write_visual_summary(
            self.out_dir / "T181_VISUAL_SUMMARY.md",
            rows=rows,
            generated_at=generated_at,
        )

        summary = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": generated_at,
            "beam_count": len(rows),
            "pass_count": sum(
                1 for r in rows if r["validation"]["visual_validation"] == "PASS"
            ),
            "fail_count": sum(
                1 for r in rows if r["validation"]["visual_validation"] != "PASS"
            ),
            "out_dir": str(self.out_dir),
        }
        (self.out_dir / "t181_run_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        (qa_dir / "t181_run_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

        return {"success": True, **summary, "rows": rows}

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
