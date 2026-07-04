"""Bar group export helpers — Phase I.9."""

from __future__ import annotations

from typing import Any, List


class BarGroupExporter:
    """Serialize bar group artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.9",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.9",
            "total_bars": summary.get("bar_count", 0),
            "calculated_identities": summary.get("calculated_identities", 0),
            "total_groups": summary.get("total_groups", 0),
            "duplicate_groups": summary.get("duplicate_groups", 0),
            "largest_group_size": summary.get("largest_group_size", 0),
            "average_group_size": summary.get("average_group_size", 0),
            "unique_engineering_signatures": summary.get("unique_engineering_signatures", 0),
            "calculated": summary.get("results_calculated", 0),
            "deferred": summary.get("deferred_results", 0),
            "blocked": summary.get("blocked_results", 0),
            "failed": summary.get("failed_results", 0),
            "distribution_by_beam": summary.get("beam_distribution", {}),
            "distribution_by_role": summary.get("role_distribution", {}),
            "distribution_by_diameter": summary.get("diameter_distribution", {}),
            "distribution_by_shape": summary.get("shape_distribution", {}),
            "distribution_by_cut_length": summary.get("cut_length_distribution", {}),
            "distribution_by_rule_source": summary.get("rule_source_distribution", {}),
        }
