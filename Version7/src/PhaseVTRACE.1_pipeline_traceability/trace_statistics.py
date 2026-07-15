"""
trace_statistics.py — Aggregates pipeline traceability statistics.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List
from .engineering_trace_models import (
    BeamLifecycle, DuplicateRecord, LostBeam, StageSnapshot, TraceStatistics
)


class TraceStatisticsEngine:

    def compute(
        self,
        snapshots:   Dict[str, StageSnapshot],
        lifecycles:  Dict[str, BeamLifecycle],
        lost_beams:  List[LostBeam],
        duplicates:  List[DuplicateRecord],
        flow:        dict,
        stage_order: List[str],
    ) -> TraceStatistics:
        source_count = snapshots.get("VROOT1", _empty_snap()).beam_count
        stage_counts = {sid: snapshots[sid].beam_count for sid in stage_order if sid in snapshots}

        first_failure = flow.get("first_failure_stage")
        first_delta   = flow.get("first_failure_delta", 0)

        # Stages with beam loss vs gain
        comps = flow.get("comparisons", [])
        stages_with_loss  = [c["to_stage"] for c in comps if c.get("delta", 0) < 0]
        stages_with_gain  = [c["to_stage"] for c in comps if c.get("delta", 0) > 0]

        # Pipeline retention = last stage count / source count
        last_snap_id = stage_order[-1] if stage_order else None
        last_count   = snapshots.get(last_snap_id).beam_count if last_snap_id and last_snap_id in snapshots else 0
        ret_pct      = (last_count / source_count * 100) if source_count else 0.0

        pipeline_complete = len(lost_beams) == 0

        return TraceStatistics(
            total_beams_at_source   = source_count,
            stage_counts            = stage_counts,
            first_failure_stage     = first_failure,
            first_failure_delta     = first_delta,
            total_lost_beams        = len(lost_beams),
            total_duplicate_records = len(duplicates),
            pipeline_retention_pct  = ret_pct,
            stages_with_loss        = stages_with_loss,
            stages_with_gain        = stages_with_gain,
            pipeline_complete       = pipeline_complete,
        )


def _empty_snap() -> StageSnapshot:
    return StageSnapshot(
        stage_id="", stage_name="", beam_count=0, beam_ids=[],
        beam_uuids={}, input_files=[], output_file="",
        artefact_exists=False, timestamp=None, raw_metadata={})
