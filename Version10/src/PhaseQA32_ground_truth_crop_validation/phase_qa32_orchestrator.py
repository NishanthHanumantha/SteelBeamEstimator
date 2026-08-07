"""
QA.3.2 orchestrator — ground truth crop verification (read-only).
MODEL_VERSION: 10.0.2
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import (
    PRIORITY_FOURTH_BEAMS,
    ArtefactLocator,
)

from .aggregator import aggregate, build_recommendations
from .beam_crop_validator import validate_beam
from .geometry_utils import as_bbox
from .qa_validator import QAValidator
from .report_builder import write_all, write_execution_summary

MODEL_VERSION = "10.0.2"
PHASE_ID = "QA.3.2"


def _find_run_reinforcement_dxf(run_root: Optional[Path]) -> Optional[Path]:
    if not run_root or not Path(run_root).exists():
        return None
    for p in Path(run_root).rglob("*.dxf"):
        if "reinforc" in p.parent.name.lower() or "reinforc" in p.name.lower():
            return p
    # fallback: any dxf under run
    cands = list(Path(run_root).rglob("*.dxf"))
    return cands[0] if cands else None


def _other_extents(bundle: Dict[str, Any]) -> Dict[str, Any]:
    env = bundle.get("geometry_envelopes") or {}
    by = env.get("by_beam") or {}
    out = {}
    for bid, rec in by.items():
        bb = as_bbox((rec or {}).get("extent"))
        if bb:
            out[str(bid)] = bb
    return out


class PhaseQA32Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        qa30_root: Optional[Path] = None,
        set_key: str = "Fourth",
        beam_ids: Optional[Sequence[str]] = None,
        skip_overlays: bool = False,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root / "data" / "output" / "PhaseQA32_ground_truth_crop_validation"
        )
        self.qa30_root = qa30_root
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.skip_overlays = skip_overlays
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Ground Truth Crop Verification")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Engine        : {self.engine_root}")
        print(f"Set           : {self.set_key}")
        print(f"Beams         : {', '.join(self.beam_ids)}")
        print("Mode          : READ-ONLY (no engineering changes)")
        print("=" * 72)
        t0 = time.perf_counter()

        locator = ArtefactLocator(self.engine_root, self.qa30_root)
        art = locator.locate_set(self.set_key)
        bundle = locator.load_bundle(art)
        other = _other_extents(bundle)
        run_dxf = _find_run_reinforcement_dxf(art.run_root)
        comparison = art.get("t182_comparison") or art.get("mirror_t182")
        renders = art.get("t182_renders")
        overlay_dir = self.output_root / "ExpectedCrop_vs_ManualCrop"
        overlay_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[{PHASE_ID}] mirror={art.mirror_dir}")
        print(f"[{PHASE_ID}] run_root={art.run_root}")
        print(f"[{PHASE_ID}] reinforcement_dxf={art.reinforcement_dxf}")
        print(f"[{PHASE_ID}] run_reinforcement_dxf={run_dxf}")
        print(f"[{PHASE_ID}] comparison={comparison}")

        records: List[Dict[str, Any]] = []
        for bid in self.beam_ids:
            print(f"\n[{PHASE_ID}] validating {bid} ...")
            owned = None
            if renders:
                cand = Path(renders) / f"{bid}.png"
                if not cand.exists():
                    cand = Path(renders) / f"{bid}_render.png"
                if cand.exists():
                    owned = cand
            if comparison and owned is None:
                cand = Path(comparison) / f"{bid}_render.png"
                if cand.exists():
                    owned = cand

            rec = validate_beam(
                bid,
                drawing_set=art.drawing_set,
                set_key=art.set_key,
                engine_root=self.engine_root,
                reinforcement_dxf=art.reinforcement_dxf,
                run_reinforcement_dxf=run_dxf,
                output_root=art.output_root,
                comparison_dir=comparison,
                owned_render_path=owned,
                bundle=bundle,
                other_extents=other,
                overlay_dir=overlay_dir,
                skip_overlays=self.skip_overlays,
            )
            records.append(rec)
            d = rec.get("decision") or {}
            m = rec.get("alignment_metrics") or {}
            print(
                f"  category={d.get('category')} status={d.get('status')} "
                f"iou={m.get('iou')} conf={d.get('confidence')} "
                f"qa31_trust={d.get('qa31_ownership_conclusion_still_valid')}"
            )
            ov = rec.get("overlay") or {}
            if ov.get("error"):
                print(f"  overlay_warn: {ov.get('error')}")

        agg = aggregate(records)
        recs = build_recommendations(agg, records)

        meta = {
            "engine_root": str(self.engine_root),
            "drawing_set": art.drawing_set,
            "set_key": art.set_key,
            "run_root": str(art.run_root) if art.run_root else None,
            "reinforcement_dxf": str(art.reinforcement_dxf) if art.reinforcement_dxf else None,
            "run_reinforcement_dxf": str(run_dxf) if run_dxf else None,
            "beam_ids": list(self.beam_ids),
            "production_regenerated": False,
            "engineering_modules_modified": False,
            "estimation_rerun": False,
            "read_only": True,
        }

        paths = write_all(self.output_root, records, agg, recs, meta)
        elapsed = round(time.perf_counter() - t0, 2)

        write_execution_summary(
            self.output_root, agg, recs, {"overall_pass": None}, elapsed
        )

        validator = QAValidator()
        validation = validator.validate(
            self.output_root, self.beam_ids, records, agg, meta, recs
        )
        write_execution_summary(self.output_root, agg, recs, validation, elapsed)

        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": bool(validation.get("overall_pass")),
            "output_root": str(self.output_root),
            "elapsed_s": elapsed,
            "beams_analysed": len(records),
            "category_counts": agg.get("category_counts"),
            "dominant_finding": agg.get("dominant_finding"),
            "baseline_trustworthy": agg.get("baseline_trustworthy"),
            "average_iou": agg.get("average_iou"),
            "priority_1": (recs.get("priorities") or [{}])[0],
            "validation_overall_pass": validation.get("overall_pass"),
            "paths": paths,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.output_root / "PhaseQA32_result.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )

        print("")
        print("=" * 72)
        print(f"Phase {PHASE_ID} COMPLETE - MODEL_VERSION {MODEL_VERSION}")
        print("=" * 72)
        print(f"Beams analysed              : {len(records)}")
        print(f"Category A/B/C              : {agg.get('category_counts')}")
        print(f"VALID/PARTIAL/INVALID       : "
              f"{agg.get('manual_crops_fully_correct')}/"
              f"{agg.get('manual_crops_partially_correct')}/"
              f"{agg.get('manual_crops_incorrect')}")
        print(f"Average IoU                 : {agg.get('average_iou')}")
        print(f"Average completeness %      : {agg.get('average_completeness_pct')}")
        print(f"Regenerated manual crops    : {agg.get('regenerated_manual_crops')}")
        print(f"QA.3.1 trustworthy beams    : {agg.get('qa31_trustworthy_beam_count')}")
        print(f"Dominant finding            : {agg.get('dominant_finding')}")
        p1 = (recs.get("priorities") or [{}])[0]
        print(f"Priority 1                  : {p1.get('title')}")
        print("Engineering modules modified: NO")
        print(f"QA overall_pass             : {validation.get('overall_pass')}")
        print("=" * 72)
        return result
