"""Project-wide propagation statistics."""
from __future__ import annotations
from typing import Any, Dict, List

from .propagation_models import BeamPropagationRecord


class PropagationStatistics:

    def compute(
        self,
        records: List[BeamPropagationRecord],
        comparison: Dict[str, Any],
    ) -> Dict[str, Any]:
        total = len(records)
        fully = sum(1 for r in records if r.root_cause == "FULLY_PROPAGATED")
        partial = sum(
            1 for r in records
            if r.steel_weight_kg > 0 and r.root_cause != "FULLY_PROPAGATED"
        )
        failed = total - fully - partial

        groups_discovered = sum(r.r1_group_count for r in records)
        groups_qty = sum(r.r1_total_quantity for r in records)
        eng_bars = sum(r.l2_bar_count for r in records)
        steel_bars = sum(r.steel_bar_count for r in records)
        bbs_rows = sum(r.bbs_engineering_rows for r in records)

        return {
            "model_version": "7.3.2",
            "phase": "R.1.2",
            "beam_summary": {
                "total_beams": total,
                "fully_propagated": fully,
                "partially_propagated": partial,
                "failed": failed,
            },
            "groups_discovered": groups_discovered,
            "groups_total_quantity": groups_qty,
            "engineering_bars_generated_l2": eng_bars,
            "engineering_bars_lost_r1_to_l2": groups_qty - eng_bars,
            "steel_bars_generated": steel_bars,
            "steel_bars_lost_l2_to_steel": eng_bars - steel_bars,
            "bbs_rows_generated": bbs_rows,
            "excel_beams_with_steel": sum(1 for r in records if r.excel_has_steel),
            "overall_propagation_pct": round(100 * fully / total, 1) if total else 0,
            "r1_to_workbook_comparison": comparison,
        }
