"""Engineering quantity export helpers — Phase I.13."""

from __future__ import annotations

from typing import Any, List


class QuantityExporter:
    """Serialize quantity artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.13",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.13",
            "total_beams": summary.get("total_beams", 0),
            "total_summaries": summary.get("total_summaries", 0),
            "total_quantities": summary.get("total_quantities", 0),
            "ready_quantities": summary.get("ready_quantities", 0),
            "deferred_quantities": summary.get("deferred_quantities", 0),
            "blocked_quantities": summary.get("blocked_quantities", 0),
            "empty_quantities": summary.get("empty_quantities", 0),
            "unknown_quantities": summary.get("unknown_quantities", 0),
            "total_steel_weight_kg": summary.get("total_steel_weight_kg", 0.0),
            "total_cut_length_mm": summary.get("total_cut_length_mm", 0),
            "total_bars": summary.get("total_bars", 0),
            "average_steel_weight_kg": summary.get("average_steel_weight_kg", 0.0),
            "average_cut_length_mm": summary.get("average_cut_length_mm", 0.0),
            "average_bars": summary.get("average_bars", 0.0),
            "beam_quantity_report": summary.get("beam_quantity_report", []),
        }

    @staticmethod
    def export_report(reporting: dict[str, Any]) -> dict[str, Any]:
        return reporting

    @staticmethod
    def export_engineering_quantity_report(
        summary: dict[str, Any],
        reporting: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.13",
            "title": "Engineering Quantity Report",
            "summary": summary,
            "reporting": reporting,
        }
