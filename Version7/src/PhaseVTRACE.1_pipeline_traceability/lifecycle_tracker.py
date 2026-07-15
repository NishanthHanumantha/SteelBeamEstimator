"""
lifecycle_tracker.py — Generates the complete beam lifecycle matrix.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List
from .engineering_trace_models import BeamLifecycle, BeamStatus


class LifecycleTracker:
    """
    Given the fully annotated lifecycle map (with loss categories assigned),
    generates the lifecycle matrix (beam_id × stage grid).
    """

    def __init__(self, stage_order: List[str]):
        self._stage_order = stage_order

    def build_matrix(
        self,
        lifecycles: Dict[str, BeamLifecycle],
    ) -> Dict[str, dict]:
        """
        Returns a dict keyed by beam_id.  Each value is a dict:
          { stage_id: "PRESENT" | "MISSING" | "ADDED" | ... }
        """
        matrix = {}
        for beam_id, lc in sorted(lifecycles.items()):
            row = {}
            for stage_id in self._stage_order:
                entry = lc.stages.get(stage_id)
                row[stage_id] = entry.status.value if entry else "UNKNOWN"
            matrix[beam_id] = row
        return matrix

    def summary_table(
        self,
        lifecycles: Dict[str, BeamLifecycle],
    ) -> List[dict]:
        rows = []
        for beam_id, lc in sorted(lifecycles.items()):
            stage_statuses = {
                sid: lc.stages[sid].status.value
                for sid in self._stage_order
                if sid in lc.stages
            }
            rows.append({
                "beam_id":       beam_id,
                "first_seen":    lc.first_seen,
                "last_seen":     lc.last_seen,
                "lost_at":       lc.lost_at,
                "loss_category": lc.loss_category.value if lc.loss_category else None,
                "loss_reason":   lc.loss_reason,
                **stage_statuses,
            })
        return rows
