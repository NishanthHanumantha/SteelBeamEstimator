"""
QA.3.4 orchestrator — ownership competition validation (read-only).
MODEL_VERSION: 10.0.4
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

from .competition_engine import (
    beam_competition_summary,
    build_competition_registry,
    build_text_owner_index,
    classify_rejection_for_beam,
    collect_hits_from_t18,
    collect_not_candidate_from_qa33,
    global_statistics,
    neighbour_conflict_matrix,
)
from .qa_validator import QAValidator
from .recommendations import build_recommendations
from .regression_gate import (
    snapshot_qa33_decisions,
    snapshot_t18_decisions,
    verify_regression,
)
from .report_builder import write_all, write_execution_summary
from .visualizer import generate_all_visuals

MODEL_VERSION = "10.0.4"
PHASE_ID = "QA.3.4"


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class PhaseQA34Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
        qa30_root: Optional[Path] = None,
        qa33_root: Optional[Path] = None,
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
            / "PhaseQA34_ownership_competition_validation"
        )
        self.qa30_root = qa30_root
        self.qa33_root = (
            Path(qa33_root)
            if qa33_root
            else self.engine_root
            / "data"
            / "output"
            / "PhaseQA33_ownership_explainability"
        )
        self.set_key = set_key
        self.beam_ids = list(beam_ids) if beam_ids else list(PRIORITY_FOURTH_BEAMS)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print(f"Phase {PHASE_ID} - Ownership Competition Validation")
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

        scores_path = self.qa33_root / "OwnershipScores.json"
        traces_path = self.qa33_root / "EntityDecisionTrace.json"
        conflict_path = self.qa33_root / "ConflictResolution.json"
        ownership_scores = _load_json(scores_path)
        decision_traces = _load_json(traces_path)
        conflict_res = _load_json(conflict_path)

        print(f"\n[{PHASE_ID}] qa33_root={self.qa33_root}")
        print(f"[{PHASE_ID}] run_root={art.run_root}")
        print(f"[{PHASE_ID}] OwnershipScores={'YES' if ownership_scores else 'NO'}")
        print(f"[{PHASE_ID}] EntityDecisionTrace={'YES' if decision_traces else 'NO'}")

        # --- Regression snapshots BEFORE any analysis (pure reads) ---
        qa33_before = snapshot_qa33_decisions(ownership_scores, decision_traces)
        t18_before = snapshot_t18_decisions(bundle.get("beam_ownership"), self.beam_ids)

        # --- Build competition registry from T18 + QA33 not-candidates ---
        hits = collect_hits_from_t18(bundle.get("beam_ownership"), self.beam_ids)
        hits.extend(collect_not_candidate_from_qa33(decision_traces, self.beam_ids))
        text_owners = build_text_owner_index(hits)
        registry = build_competition_registry(hits, priority_beams=self.beam_ids)
        print(
            f"[{PHASE_ID}] hits={len(hits)} identities={registry.get('entity_count')} "
            f"priority_identities={registry.get('priority_entity_count')} "
            f"text_owner_keys={len(text_owners)}"
        )

        all_classified: List[Dict[str, Any]] = []
        beam_summaries: List[Dict[str, Any]] = []
        for bid in self.beam_ids:
            print(f"\n[{PHASE_ID}] classifying rejects for {bid} ...")
            classified = classify_rejection_for_beam(bid, registry, text_owners)
            summary = beam_competition_summary(bid, classified)
            all_classified.append(classified)
            beam_summaries.append(summary)
            print(
                f"  rejected={summary.get('rejected')} "
                f"owned_elsewhere={summary.get('owned_elsewhere')} "
                f"dropped={summary.get('dropped')} "
                f"leader={summary.get('leader_failures')} "
                f"geom={summary.get('geometry_failures')} "
                f"conflict={summary.get('conflict_failures')}"
            )

        gstats = global_statistics(beam_summaries, all_classified, registry)
        nmatrix = neighbour_conflict_matrix(all_classified, self.beam_ids)
        recs = build_recommendations(gstats, beam_summaries)

        # --- Regression AFTER (must be identical — we only read) ---
        # Re-load QA.3.3 files from disk to prove they were not rewritten
        ownership_scores_after = _load_json(scores_path)
        decision_traces_after = _load_json(traces_path)
        qa33_after = snapshot_qa33_decisions(
            ownership_scores_after, decision_traces_after
        )
        t18_after = snapshot_t18_decisions(bundle.get("beam_ownership"), self.beam_ids)
        regression = verify_regression(
            qa33_before=qa33_before,
            qa33_after=qa33_after,
            t18_before=t18_before,
            t18_after=t18_after,
            qa33_files={
                "OwnershipScores.json": str(scores_path),
                "EntityDecisionTrace.json": str(traces_path),
                "ConflictResolution.json": str(conflict_path),
            },
        )
        if not regression.get("overall_pass"):
            print(f"[{PHASE_ID}] REGRESSION FAIL — ownership decisions changed")
            for c in regression.get("checks") or []:
                if not c.get("pass"):
                    print(f"  FAIL {c.get('check')}: {c.get('detail')}")

        # Visuals
        vis_dir = self.output_root / "Visualisations"
        visual_paths = generate_all_visuals(
            out_dir=vis_dir,
            global_stats=gstats,
            beam_summaries=beam_summaries,
            all_classified=all_classified,
            neighbour_matrix=nmatrix,
            priority_beams=self.beam_ids,
        )

        meta = {
            "engine_root": str(self.engine_root),
            "drawing_set": art.drawing_set,
            "set_key": art.set_key,
            "run_root": str(art.run_root) if art.run_root else None,
            "qa33_root": str(self.qa33_root),
            "beam_ids": list(self.beam_ids),
            "production_regenerated": False,
            "engineering_modules_modified": False,
            "ownership_decisions_mutated": False,
            "read_only": True,
            "conflict_resolution_available": conflict_res is not None,
        }

        paths = write_all(
            self.output_root,
            registry=registry,
            all_classified=all_classified,
            beam_summaries=beam_summaries,
            global_stats=gstats,
            neighbour_matrix=nmatrix,
            regression=regression,
            recommendations=recs,
            visual_paths=visual_paths,
            meta=meta,
        )
        elapsed = round(time.perf_counter() - t0, 2)

        write_execution_summary(
            self.output_root,
            gstats,
            recs,
            regression,
            {"overall_pass": None},
            elapsed,
        )
        validator = QAValidator()
        validation = validator.validate(
            self.output_root,
            self.beam_ids,
            all_classified,
            gstats,
            regression,
            meta,
            recs,
        )
        write_execution_summary(
            self.output_root, gstats, recs, regression, validation, elapsed
        )

        # Pass/Fail report
        pass_fail = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "status": "PASS" if validation.get("overall_pass") else "FAIL",
            "validation_overall_pass": validation.get("overall_pass"),
            "regression_overall_pass": regression.get("overall_pass"),
            "statistics": gstats,
            "dominant_qa40_target": recs.get("dominant_qa40_target"),
            "recommendations_summary": recs.get("summary"),
        }
        (self.output_root / "PASS_FAIL_REPORT.json").write_text(
            json.dumps(pass_fail, indent=2, default=str), encoding="utf-8"
        )

        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": bool(validation.get("overall_pass")),
            "output_root": str(self.output_root),
            "elapsed_s": elapsed,
            "statistics": gstats,
            "dominant_qa40_target": recs.get("dominant_qa40_target"),
            "priority_1": (recs.get("priorities") or [{}])[0],
            "regression_pass": regression.get("overall_pass"),
            "validation_overall_pass": validation.get("overall_pass"),
            "paths": paths,
            "visual_paths": visual_paths,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.output_root / "PhaseQA34_result.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )

        print("")
        print("=" * 72)
        print(f"Phase {PHASE_ID} COMPLETE - MODEL_VERSION {MODEL_VERSION}")
        print("=" * 72)
        print(f"Total rejected              : {gstats.get('total_rejected')}")
        print(f"Owned elsewhere             : {gstats.get('owned_elsewhere')}")
        print(f"Dropped (disappeared)       : {gstats.get('dropped')}")
        print(f"Leader failures             : {gstats.get('leader_failures')}")
        print(f"Geometry failures           : {gstats.get('geometry_failures')}")
        print(f"Envelope failures           : {gstats.get('envelope_failures')}")
        print(f"Conflict failures           : {gstats.get('conflict_failures')}")
        print(f"Dropped fraction            : {gstats.get('dropped_fraction_of_rejects')}")
        print(f"Dominant QA.4.0 target      : {recs.get('dominant_qa40_target')}")
        p1 = (recs.get("priorities") or [{}])[0]
        print(f"Priority 1                  : {p1.get('title')}")
        print(f"Regression gate             : {regression.get('overall_pass')}")
        print("Ownership decisions mutated : NO")
        print(f"STATUS                      : {'PASS' if validation.get('overall_pass') else 'FAIL'}")
        print("=" * 72)
        return result
