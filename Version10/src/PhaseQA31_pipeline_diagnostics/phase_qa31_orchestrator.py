"""
QA.3.1 orchestrator — read-only pipeline diagnostics.
MODEL_VERSION: 10.0.1
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .artefact_locator import PRIORITY_FOURTH_BEAMS, ArtefactLocator
from .beam_diagnostics import diagnose_beam
from .global_aggregator import aggregate, build_recommendations
from .qa_validator import QAValidator
from .report_builder import write_all, write_execution_summary

MODEL_VERSION = "10.0.1"
PHASE_ID = "QA.3.1"


class PhaseQA31Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        qa30_root: Optional[Path] = None,
        set_key: str = "Fourth",
        beam_ids: Optional[Sequence[str]] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root / "data" / "output" / "PhaseQA31_pipeline_diagnostics"
        )
        self.qa30_root = qa30_root
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Ownership & Render Pipeline Diagnostics")
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

        print(f"\n[{PHASE_ID}] mirror={art.mirror_dir}")
        print(f"[{PHASE_ID}] run_root={art.run_root}")
        print(f"[{PHASE_ID}] reinforcement_dxf={art.reinforcement_dxf}")
        for w in art.warnings:
            print(f"  warn: {w}")

        comparison = art.get("t182_comparison") or art.get("mirror_t182")
        renders = art.get("t182_renders")

        records: List[Dict[str, Any]] = []
        for bid in self.beam_ids:
            print(f"\n[{PHASE_ID}] diagnosing {bid} ...")
            rec = diagnose_beam(
                bid,
                art.drawing_set,
                art.set_key,
                bundle,
                comparison,
                renders,
            )
            # Join light QA.3.0 benchmark hint if available
            bench = bundle.get("benchmark_result") or {}
            missing_ids = ((bench.get("beam_matching") or {}).get("missing_ids")) or []
            rec["qa30_crosscheck"] = {
                "listed_as_missing_beam": bid in missing_ids,
            }
            records.append(rec)
            rc = rec.get("root_cause") or {}
            print(
                f"  first_fail={rc.get('first_failing_stage')} "
                f"primary={rc.get('primary_category')} "
                f"conf={rc.get('confidence')}"
            )

        agg = aggregate(records)
        recs = build_recommendations(agg, records)

        meta = {
            "engine_root": str(self.engine_root),
            "drawing_set": art.drawing_set,
            "set_key": art.set_key,
            "run_root": str(art.run_root) if art.run_root else None,
            "reinforcement_dxf": str(art.reinforcement_dxf) if art.reinforcement_dxf else None,
            "beam_ids": list(self.beam_ids),
            "production_regenerated": False,
            "estimator_used_for_ownership": False,
            "engineering_modules_modified": False,
            "read_only": True,
        }

        paths = write_all(self.output_root, records, agg, recs, meta)

        elapsed = round(time.perf_counter() - t0, 2)
        # Write ExecutionSummary before validation so required-output gate can see it.
        # Validation fields filled after; rewrite summary once more below.
        write_execution_summary(
            self.output_root,
            agg,
            recs,
            {"overall_pass": None},
            elapsed,
        )

        validator = QAValidator()
        validation = validator.validate(
            self.output_root, self.beam_ids, records, agg, meta
        )
        write_execution_summary(
            self.output_root, agg, recs, validation, elapsed
        )

        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": bool(validation.get("overall_pass")),
            "output_root": str(self.output_root),
            "elapsed_s": elapsed,
            "beams_analysed": len(records),
            "failure_frequency": agg.get("failure_frequency"),
            "hypothesis": agg.get("hypothesis"),
            "top_primary_root_cause": agg.get("top_primary_root_cause"),
            "priority_1": (recs.get("priorities") or [{}])[0],
            "validation_overall_pass": validation.get("overall_pass"),
            "paths": paths,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.output_root / "PhaseQA31_result.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )

        # Completion summary
        hyp = agg.get("hypothesis") or {}
        print("")
        print("=" * 72)
        print(f"Phase {PHASE_ID} COMPLETE - MODEL_VERSION {MODEL_VERSION}")
        print("=" * 72)
        print(f"Beams analysed              : {len(records)}")
        print(f"Missing-artefact beams      : {agg.get('beams_with_missing_artefacts')}")
        print("Failure frequency by stage:")
        for k, v in (agg.get("failure_frequency") or {}).items():
            print(f"  - {k}: {v}")
        print(f"Top primary root cause      : {agg.get('top_primary_root_cause')}")
        print(
            "ownership_or_scoping_before_render_is_dominant: "
            f"{hyp.get('ownership_or_scoping_before_render_is_dominant')}"
        )
        print(
            "renderer_mostly_faithful_to_owned_set: "
            f"{hyp.get('renderer_mostly_faithful_to_owned_set')}"
        )
        p1 = (recs.get("priorities") or [{}])[0]
        print(f"Priority 1                  : {p1.get('target_stage')} - {p1.get('recommendation')}")
        print("Engineering modules modified: NO")
        print(f"QA overall_pass             : {validation.get('overall_pass')}")
        print("=" * 72)
        return result
