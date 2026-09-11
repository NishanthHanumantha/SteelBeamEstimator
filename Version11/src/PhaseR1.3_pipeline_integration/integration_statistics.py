"""Integration statistics for Phase R.1.3."""
from __future__ import annotations
from typing import Any, Dict


class IntegrationStatistics:

    def compute(
        self,
        build_result: Dict[str, Any],
        before_metrics: Dict[str, Any],
        after_metrics: Dict[str, Any],
        processing_report: Dict[str, Any],
        pipeline_timing: Dict[str, float],
    ) -> Dict[str, Any]:
        r1_beams = build_result.get("beams_with_bars", 0) + build_result.get(
            "adapter_stats", {}
        ).get("beams_empty", 0)
        if not r1_beams:
            r1_beams = build_result.get("beam_count", 62)

        beams_with_steel_after = after_metrics.get("beams_reaching_steel", 0)
        beams_with_bars = build_result.get("beams_with_bars", 62)
        propagation_pct = (
            round(100.0 * beams_with_steel_after / max(beams_with_bars, 1), 2)
        )
        propagation_loss = max(0, beams_with_bars - beams_with_steel_after)

        return {
            "engineering_bars_created": build_result.get("total_bars", 0),
            "beam_coverage": {
                "r1_beams_total": r1_beams,
                "beams_with_bars": build_result.get("beams_with_bars", 0),
                "beams_empty": build_result.get("adapter_stats", {}).get(
                    "beams_empty", 0
                ),
                "empty_beam_ids": build_result.get("adapter_stats", {}).get(
                    "empty_beam_ids", []
                ),
            },
            "propagation_pct": propagation_pct,
            "propagation_loss": propagation_loss,
            "engineering_bar_counts": {
                "total_bars": build_result.get("total_bars", 0),
                "role_counts": processing_report.get("role_counts", {}),
                "diameter_counts": processing_report.get("diameter_counts", {}),
            },
            "pipeline_timing": pipeline_timing,
            "before": before_metrics,
            "after": after_metrics,
        }
