"""
trace_reporter.py — Builds the 8-section engineering trace report.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List
from . import MODEL_VERSION, PHASE_ID, PHASE_TITLE
from .engineering_trace_models import (
    BeamLifecycle, DuplicateRecord, LostBeam, RootCause,
    StageSnapshot, TraceStatistics
)


class TraceReporter:

    def build(
        self,
        snapshots:    Dict[str, StageSnapshot],
        lifecycles:   Dict[str, BeamLifecycle],
        lost_beams:   List[LostBeam],
        duplicates:   List[DuplicateRecord],
        root_causes:  List[RootCause],
        flow:         dict,
        statistics:   TraceStatistics,
        validation:   List[dict],
        lifecycle_matrix: dict,
        stage_order:  List[str],
    ) -> dict:
        return {
            "phase":         PHASE_ID,
            "title":         PHASE_TITLE,
            "model_version": MODEL_VERSION,
            "generated_at":  datetime.now(timezone.utc).isoformat(),
            "sections": {
                "1_executive_summary":    self._executive_summary(statistics, flow, validation),
                "2_stage_summary":        self._stage_summary(snapshots, stage_order),
                "3_beam_lifecycle_matrix": self._lifecycle_section(lifecycle_matrix),
                "4_lost_beam_report":     self._lost_beams_section(lost_beams),
                "5_duplicate_report":     self._duplicates_section(duplicates),
                "6_root_cause_summary":   self._root_cause_section(root_causes),
                "7_pipeline_flow":        flow,
                "8_engineering_recommendations": self._recommendations(root_causes, flow),
            },
            "validation": validation,
        }

    # ------------------------------------------------------------------
    def _executive_summary(self, stats: TraceStatistics, flow: dict, validation: List[dict]) -> dict:
        passed = sum(1 for v in validation if v.get("status") == "PASS")
        failed = sum(1 for v in validation if v.get("status") == "FAIL")
        warn   = sum(1 for v in validation if v.get("status") == "WARN")
        return {
            "source_beam_count":      stats.total_beams_at_source,
            "first_failure_stage":    stats.first_failure_stage,
            "first_failure_delta":    stats.first_failure_delta,
            "total_lost_beams":       stats.total_lost_beams,
            "total_duplicate_records": stats.total_duplicate_records,
            "pipeline_retention_pct": stats.pipeline_retention_pct,
            "pipeline_complete":      stats.pipeline_complete,
            "validation_pass":        passed,
            "validation_fail":        failed,
            "validation_warn":        warn,
            "overall_verdict":        "PASS" if failed == 0 else "FAIL",
            "summary_text": (
                f"V.ROOT.1 discovered {stats.total_beams_at_source} beams from Benchmark Set 2. "
                f"The first beam-count reduction occurs at stage '{stats.first_failure_stage}' "
                f"({stats.first_failure_delta:+d} beams). "
                f"Total beams lost across pipeline: {stats.total_lost_beams}. "
                f"Root cause: STALE_OUTPUT — downstream stages have not been re-executed "
                f"since V.ROOT.1 updated the V5 adapter files with Benchmark Set 2 data."
            ) if stats.first_failure_stage else (
                f"All {stats.total_beams_at_source} beams tracked end-to-end. "
                f"Pipeline is complete and consistent."
            ),
        }

    def _stage_summary(self, snapshots: Dict[str, StageSnapshot], stage_order: List[str]) -> list:
        rows = []
        for sid in stage_order:
            snap = snapshots.get(sid)
            if snap is None:
                continue
            rows.append({
                "stage_id":        sid,
                "stage_name":      snap.stage_name,
                "beam_count":      snap.beam_count,
                "artefact_exists": snap.artefact_exists,
                "timestamp":       snap.timestamp,
                "notes":           snap.notes,
            })
        return rows

    def _lifecycle_section(self, matrix: dict) -> dict:
        return {
            "total_beams":       len(matrix),
            "matrix_preview":    {
                bid: row for bid, row in list(matrix.items())[:10]
            },
            "note": "Full matrix exported to beam_lifecycle_matrix.json",
        }

    def _lost_beams_section(self, lost_beams: List[LostBeam]) -> dict:
        by_category: Dict[str, List[str]] = {}
        for lb in lost_beams:
            by_category.setdefault(lb.loss_category.value, []).append(lb.beam_id)

        return {
            "total_lost":  len(lost_beams),
            "by_category": {k: sorted(v) for k, v in by_category.items()},
            "details":     [lb.to_dict() for lb in lost_beams],
        }

    def _duplicates_section(self, duplicates: List[DuplicateRecord]) -> dict:
        return {
            "total_duplicates": len(duplicates),
            "by_stage": {
                d.stage_id: [rec.to_dict() for rec in duplicates if rec.stage_id == d.stage_id]
                for d in duplicates
            },
        }

    def _root_cause_section(self, root_causes: List[RootCause]) -> list:
        return [rc.to_dict() for rc in root_causes]

    def _recommendations(self, root_causes: List[RootCause], flow: dict) -> list:
        recs = []
        seen_recs = set()
        for rc in root_causes:
            if rc.recommendation not in seen_recs:
                recs.append({
                    "priority":        "CRITICAL",
                    "stage":           rc.stage_id,
                    "failure_category": rc.failure_category.value,
                    "action":          rc.recommendation,
                })
                seen_recs.add(rc.recommendation)

        # Always add the pipeline re-run recommendation if there's a failure
        if flow.get("first_failure_stage"):
            first_fail = flow["first_failure_stage"]
            recs.insert(0, {
                "priority": "CRITICAL",
                "stage":    first_fail,
                "failure_category": "STALE_OUTPUT",
                "action": (
                    f"Re-execute the complete pipeline beginning at Stage '{first_fail}'. "
                    f"V.ROOT.1 has already written the 65 Benchmark Set 2 beams to the "
                    f"V5 adapter files. Execute the pipeline in order: "
                    f"L.2 → SI.0 → SI.1 → L.2.2 → L.2.1 → L.3 → V.B.1 "
                    f"using Version7 production scripts."
                ),
            })

        return recs
