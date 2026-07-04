"""Steel weight export helpers — Phase I.11."""

from __future__ import annotations

from typing import Any, List


class SteelWeightExporter:
    """Serialize steel weight artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.11",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.11",
            "total_bars": summary.get("bar_count", 0),
            "calculated": summary.get("calculated", 0),
            "deferred": summary.get("deferred", 0),
            "blocked": summary.get("blocked", 0),
            "failed": summary.get("failed", 0),
            "total_steel_weight_kg": summary.get("total_steel_weight_kg", 0.0),
            "average_bar_weight_kg": summary.get("average_bar_weight_kg", 0.0),
            "largest_bar": summary.get("largest_bar"),
            "distribution_by_beam": summary.get("beam_distribution", {}),
            "distribution_by_role": summary.get("role_distribution", {}),
            "distribution_by_diameter": summary.get("diameter_distribution", {}),
            "distribution_by_shape": summary.get("shape_distribution", {}),
            "distribution_by_fabrication_state": summary.get("fabrication_state_distribution", {}),
            "distribution_by_fabrication_mark": summary.get("fabrication_mark_distribution", {}),
            "weight_by_beam": summary.get("weight_by_beam", {}),
            "weight_by_diameter": summary.get("weight_by_diameter", {}),
            "weight_by_role": summary.get("weight_by_role", {}),
            "weight_by_shape": summary.get("weight_by_shape", {}),
        }

    @staticmethod
    def export_report(reporting: dict[str, Any]) -> dict[str, Any]:
        return reporting

    @staticmethod
    def export_engineering_weight_report(summary: dict[str, Any], reporting: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.11",
            "title": "Engineering Steel Weight Report",
            "summary": summary,
            "reporting": reporting,
        }
