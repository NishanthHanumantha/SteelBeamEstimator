"""Beam summary export helpers — Phase I.12."""

from __future__ import annotations

from typing import Any, List


class BeamSummaryExporter:
    """Serialize beam summary artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.12.2",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.12.2",
            "total_beams": summary.get("total_beams", 0),
            "total_summaries": summary.get("total_summaries", 0),
            "total_bars": summary.get("total_bars", 0),
            "average_bars_per_beam": summary.get("average_bars_per_beam", 0.0),
            "average_steel_weight_kg": summary.get("average_steel_weight_kg", 0.0),
            "total_steel_weight_kg": summary.get("total_steel_weight_kg", 0.0),
            "largest_beam": summary.get("largest_beam"),
            "smallest_beam": summary.get("smallest_beam"),
            "beam_with_largest_steel_weight": summary.get("beam_with_largest_steel_weight"),
            "beam_with_longest_reinforcement": summary.get("beam_with_longest_reinforcement"),
            "distribution_by_diameter": summary.get("diameter_distribution", {}),
            "distribution_by_shape": summary.get("shape_distribution", {}),
            "distribution_by_role": summary.get("role_distribution", {}),
            "distribution_by_fabrication_state": summary.get("fabrication_state_distribution", {}),
            "distribution_by_engineering_state": summary.get("engineering_state_distribution", {}),
            "engineering_ready_beams": summary.get("engineering_ready_beams", 0),
            "partial_beams": summary.get("partial_beams", 0),
            "blocked_beams": summary.get("blocked_beams", 0),
            "empty_beams": summary.get("empty_beams", 0),
            "average_completion_percent": summary.get("average_completion_percent", 0.0),
            "beam_completion_report": summary.get("beam_completion_report", []),
            "average_confidence_score": summary.get("average_confidence_score", 0.0),
            "quality_grade_distribution": summary.get("quality_grade_distribution", {}),
            "quality_ready_beams": summary.get("quality_ready_beams", 0),
            "highest_confidence_beam": summary.get("highest_confidence_beam"),
            "lowest_confidence_beam": summary.get("lowest_confidence_beam"),
            "beam_quality_report": summary.get("beam_quality_report", []),
        }

    @staticmethod
    def export_report(reporting: dict[str, Any]) -> dict[str, Any]:
        return reporting

    @staticmethod
    def export_engineering_beam_summary_report(
        summary: dict[str, Any],
        reporting: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.12.2",
            "title": "Engineering Beam Summary Report",
            "summary": summary,
            "reporting": reporting,
        }
