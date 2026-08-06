"""
Phase T1.7.1 orchestrator — Graph-Aware Render Validation.
MODEL_VERSION: 9.4.1
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .benchmark_validator import summarize_benchmark, validate_beam_artefacts
from .comparison_renderer import (
    build_difference_report,
    make_side_by_side,
    write_difference_report,
)
from .graph_overlay_renderer import render_graph_aware
from .qa_report import write_qa_report
from .renderer_snapshot import snapshot_original_render

MODEL_VERSION = "9.4.1"
PHASE_ID = "T1.7.1"
_OUT_NAME = "PhaseT171_graph_render_validation"


class PhaseT171Orchestrator:
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
        self.out_dir.mkdir(parents=True, exist_ok=True)
        gallery = self.out_dir / "ValidationGallery"
        gallery.mkdir(parents=True, exist_ok=True)

        graph_path = (
            self.output_root / "PhaseT17_annotation_graph" / "AnnotationGraph.json"
        )
        if not graph_path.exists():
            return {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "AnnotationGraph.json missing — run T1.7 first",
            }
        graph_payload = json.loads(graph_path.read_text(encoding="utf-8"))
        ownership = self._load_ownership()

        ids = list(beam_ids) if beam_ids else ["B1", "B2", "B8", "B9", "B10"]
        rows: List[Dict[str, Any]] = []
        diffs: List[Dict[str, Any]] = []

        for bid in ids:
            print(f"[T1.7.1] Validating {bid}...")
            beam_dir = self.out_dir / bid
            beam_dir.mkdir(parents=True, exist_ok=True)

            snap = snapshot_original_render(
                engine_root=self.engine_root,
                run_root=self.run_root,
                output_root=self.output_root,
                beam_id=bid,
                dest=beam_dir / "Original_Render.png",
            )
            overlay_info = render_graph_aware(
                engine_root=self.engine_root,
                run_root=self.run_root,
                output_root=self.output_root,
                beam_id=bid,
                graph_payload=graph_payload,
                out_graph_aware=beam_dir / "GraphAware_Render.png",
                out_overlay_only=beam_dir / "Overlay_Render.png",
            )
            if not overlay_info.get("success"):
                print(f"  overlay failed: {overlay_info}")
                continue

            make_side_by_side(
                beam_dir / "Original_Render.png",
                beam_dir / "GraphAware_Render.png",
                beam_dir / "SideBySide.png",
                beam_id=bid,
            )
            # Gallery copy
            shutil.copy2(
                beam_dir / "SideBySide.png", gallery / f"{bid}_Comparison.png"
            )

            diff = build_difference_report(
                bid,
                graph_payload,
                ownership.get(bid) or [],
                overlay_counts=overlay_info.get("overlay_counts"),
            )
            write_difference_report(diff, beam_dir / "Difference_Report.json")
            diffs.append(diff)

            val = validate_beam_artefacts(beam_dir, diff)
            rows.append(
                {
                    "beam_id": bid,
                    "snapshot": snap,
                    "overlay": overlay_info,
                    "difference": diff,
                    "validation": val,
                }
            )
            print(
                f"  {bid} -> {val['validation']} "
                f"newly={diff.get('newly_visible')} chains={diff.get('leader_bar_chains')}"
            )

        # Aggregate difference reports
        (self.out_dir / "Difference_Report.json").write_text(
            json.dumps({"model_version": MODEL_VERSION, "by_beam": diffs}, indent=2),
            encoding="utf-8",
        )
        summary = summarize_benchmark([r["validation"] for r in rows])
        (self.out_dir / "validation_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

        generated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        write_qa_report(
            dest=self.out_dir / "T171_GRAPH_RENDER_VALIDATION_QA_REPORT.md",
            rows=rows,
            out_dir=self.out_dir,
            gallery_dir=gallery,
            generated_at=generated_at,
        )

        # Overview PDF of all comparisons
        pdf_path = self._write_overview_pdf(gallery, ids)

        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": True,
            "generated_at": generated_at,
            "out_dir": str(self.out_dir),
            "gallery": str(gallery),
            "overview_pdf": str(pdf_path) if pdf_path else None,
            "summary": summary,
            "beams": [r["beam_id"] for r in rows],
        }
        (self.out_dir / "t171_run_summary.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result

    def _load_ownership(self) -> Dict[str, List[Dict[str, Any]]]:
        path = (
            self.output_root
            / "PhaseT16_entity_ownership"
            / "beam_entity_ownership.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {str(k): list(v or []) for k, v in (data.get("by_beam") or {}).items()}

    @staticmethod
    def _write_overview_pdf(gallery: Path, beam_ids: Sequence[str]) -> Optional[Path]:
        try:
            from PIL import Image
        except ImportError:
            return None
        images = []
        for bid in beam_ids:
            p = gallery / f"{bid}_Comparison.png"
            if p.exists():
                images.append(Image.open(p).convert("RGB"))
        if not images:
            return None
        pdf_path = gallery / "Overview.pdf"
        first, rest = images[0], images[1:]
        first.save(
            str(pdf_path),
            "PDF",
            resolution=100.0,
            save_all=bool(rest),
            append_images=rest,
        )
        return pdf_path
