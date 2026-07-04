"""Cut length export helpers — Phase I.6."""

from __future__ import annotations

from typing import Any, List


class CutLengthExporter:
    """Serialize cut length artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.6",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.6",
            "total_cut_determinations": summary.get("determination_count", 0),
            "calculated": summary.get("results_calculated", 0),
            "deferred": summary.get("deferred_results", 0),
            "blocked": summary.get("blocked_results", 0),
            "failed": summary.get("failed_results", 0),
            "average_cut_length_mm": summary.get("average_cut_length_mm", 0.0),
            "min_cut_length_mm": summary.get("min_cut_length_mm"),
            "max_cut_length_mm": summary.get("max_cut_length_mm"),
            "distribution_by_role": summary.get("role_distribution", {}),
            "distribution_by_diameter": summary.get("diameter_distribution", {}),
            "distribution_by_beam": summary.get("beam_distribution", {}),
            "distribution_by_bar_type": summary.get("bar_type_distribution", {}),
            "distribution_by_rule_source": summary.get("rule_source_distribution", {}),
        }
