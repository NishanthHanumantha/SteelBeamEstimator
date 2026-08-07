"""
QA.3.3 orchestrator — ownership explainability (read-only).
MODEL_VERSION: 10.0.3
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
from .competing_beam_analyzer import build_competition_index
from .explainability_engine import explain_beam
from .qa_validator import QAValidator
from .report_builder import write_all, write_execution_summary
from .visualizer import generate_beam_visuals

MODEL_VERSION = "10.0.3"
PHASE_ID = "QA.3.3"


def _load_annotation_graph(output_root: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not output_root:
        return None
    path = Path(output_root) / "PhaseT17_annotation_graph" / "AnnotationGraph.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class PhaseQA33Orchestrator:
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
            else self.engine_root
            / "data"
            / "output"
            / "PhaseQA33_ownership_explainability"
        )
        self.qa30_root = qa30_root
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Ownership Explainability & Decision Trace")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Engine        : {self.engine_root}")
        print(f"Set           : {self.set_key}")
        print(f"Beams         : {', '.join(self.beam_ids)}")
        print("Mode          : READ-ONLY (no ownership decision changes)")
        print("=" * 72)
        t0 = time.perf_counter()

        locator = ArtefactLocator(self.engine_root, self.qa30_root)
        art = locator.locate_set(self.set_key)
        bundle = locator.load_bundle(art)
        graph_doc = _load_annotation_graph(art.output_root)

        print(f"\n[{PHASE_ID}] mirror={art.mirror_dir}")
        print(f"[{PHASE_ID}] run_root={art.run_root}")
        print(f"[{PHASE_ID}] annotation_graph={'YES' if graph_doc else 'NO'}")

        # Stage 3 global competition index (all beams, priority tagged)
        competition_index = build_competition_index(
            bundle.get("beam_ownership"),
            priority_beams=self.beam_ids,
        )
        print(
            f"[{PHASE_ID}] competition entities={competition_index.get('entity_count')} "
            f"multi_beam={competition_index.get('multi_beam_entity_count')}"
        )

        env_dir = self.output_root / "CandidateEnvelopeOverlays"
        comp_dir = self.output_root / "CompetingBeamOverlays"
        flow_dir = self.output_root / "DecisionFlowCharts"
        for d in (env_dir, comp_dir, flow_dir):
            d.mkdir(parents=True, exist_ok=True)

        records: List[Dict[str, Any]] = []
        visual_paths: Dict[str, Any] = {}
        for bid in self.beam_ids:
            print(f"\n[{PHASE_ID}] explaining {bid} ...")
            rec = explain_beam(
                bid,
                drawing_set=art.drawing_set,
                set_key=art.set_key,
                bundle=bundle,
                graph_doc=graph_doc,
                competition_index=competition_index,
            )
            vp = generate_beam_visuals(
                rec,
                envelope_dir=env_dir,
                competing_dir=comp_dir,
                flow_dir=flow_dir,
            )
            rec["visuals"] = vp
            visual_paths[bid] = vp
            records.append(rec)
            f = rec.get("stage6_failure_classification") or {}
            c = rec.get("stage5_coverage") or {}
            print(
                f"  primary={f.get('primary_cause')} conf={f.get('confidence')} "
                f"owned={c.get('entities_owned')} rejected={c.get('entities_rejected')} "
                f"traces={(rec.get('stage4_decision_traces') or {}).get('trace_count')}"
            )
            if vp.get("error"):
                print(f"  visual_warn: {vp.get('error')}")

        agg = aggregate(records, competition_index)
        recs = build_recommendations(agg, records)

        meta = {
            "engine_root": str(self.engine_root),
            "drawing_set": art.drawing_set,
            "set_key": art.set_key,
            "run_root": str(art.run_root) if art.run_root else None,
            "beam_ids": list(self.beam_ids),
            "production_regenerated": False,
            "engineering_modules_modified": False,
            "ownership_decisions_mutated": False,
            "estimation_rerun": False,
            "read_only": True,
            "rule_catalogue_exposed": True,
        }

        paths = write_all(
            self.output_root,
            records,
            agg,
            recs,
            competition_index,
            visual_paths,
            meta,
        )
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
            "failure_frequency": agg.get("failure_frequency_by_category"),
            "most_common_rejection_reason": agg.get("most_common_rejection_reason"),
            "most_common_filtering_rule": agg.get("most_common_filtering_rule"),
            "priority_1": (recs.get("priorities") or [{}])[0],
            "validation_overall_pass": validation.get("overall_pass"),
            "paths": paths,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.output_root / "PhaseQA33_result.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )

        print("")
        print("=" * 72)
        print(f"Phase {PHASE_ID} COMPLETE - MODEL_VERSION {MODEL_VERSION}")
        print("=" * 72)
        print(f"Beams analysed              : {len(records)}")
        print(f"Failure frequency           : {agg.get('failure_frequency_by_category')}")
        print(f"Most common rejection       : {agg.get('most_common_rejection_reason')}")
        print(f"Most common filter rule     : {agg.get('most_common_filtering_rule')}")
        print(f"Ownership acceptance rate   : {agg.get('ownership_acceptance_rate')}")
        print(f"Conflict frequency          : {agg.get('conflict_frequency')}")
        p1 = (recs.get("priorities") or [{}])[0]
        print(f"Priority 1                  : {p1.get('title')}")
        print("Ownership decisions mutated : NO")
        print("Engineering modules modified: NO")
        print(f"QA overall_pass             : {validation.get('overall_pass')}")
        print("=" * 72)
        return result
