"""Calculation index export helpers — Phase I.4.5."""

from __future__ import annotations

from typing import Any, List


class CalculationIndexExporter:
    """Serialize calculation index artifacts for pipeline export."""

    @staticmethod
    def export_indexes(indexes: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4.5",
            "index_count": len(indexes),
            "indexes": indexes,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4.5",
            "bar_count": summary.get("bar_count", 0),
            "total_calculation_results": summary.get("total_calculation_results", 0),
            "indexed_calculations": summary.get("indexed_calculations", 0),
            "category_counts": summary.get("category_counts", {}),
            "development_length_count": summary.get("development_length_count", 0),
            "hook_length_count": summary.get("hook_length_count", 0),
            "deferred_count": summary.get("deferred_count", 0),
            "blocked_count": summary.get("blocked_count", 0),
            "calculated_count": summary.get("calculated_count", 0),
            "average_calculations_per_bar": summary.get("average_calculations_per_bar", 0.0),
            "validation_status": summary.get("validation_summary", {}).get("status", "SKIP"),
        }
