"""
stage_comparator.py — Compares consecutive stage snapshots to detect beam changes.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List, Tuple
from .engineering_trace_models import StageComparison, StageSnapshot


class StageComparator:
    """Produces a StageComparison for every pair of consecutive stages."""

    def compare_all(
        self,
        snapshots: Dict[str, StageSnapshot],
        stage_order: List[str],
    ) -> List[StageComparison]:
        comparisons = []
        for i in range(len(stage_order) - 1):
            from_id = stage_order[i]
            to_id   = stage_order[i + 1]
            from_snap = snapshots.get(from_id)
            to_snap   = snapshots.get(to_id)
            if from_snap is None or to_snap is None:
                continue
            comparisons.append(self._compare(from_snap, to_snap))
        return comparisons

    def _compare(
        self,
        from_snap: StageSnapshot,
        to_snap: StageSnapshot,
    ) -> StageComparison:
        from_set    = set(from_snap.beam_ids)
        to_set      = set(to_snap.beam_ids)
        removed     = sorted(from_set - to_set)
        added       = sorted(to_set - from_set)
        retained    = sorted(from_set & to_set)
        from_count  = from_snap.beam_count
        to_count    = to_snap.beam_count
        ret_pct     = (len(retained) / from_count * 100) if from_count else 0.0
        loss_pct    = (len(removed)  / from_count * 100) if from_count else 0.0

        return StageComparison(
            from_stage     = from_snap.stage_id,
            to_stage       = to_snap.stage_id,
            from_count     = from_count,
            to_count       = to_count,
            delta          = to_count - from_count,
            beams_removed  = removed,
            beams_added    = added,
            beams_retained = retained,
            retention_pct  = ret_pct,
            loss_pct       = loss_pct,
        )
