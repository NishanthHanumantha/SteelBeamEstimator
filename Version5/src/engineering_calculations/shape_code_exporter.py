"""Shape code export helpers — Phase I.7."""

from __future__ import annotations

from typing import Any, List


class ShapeCodeExporter:
    """Serialize shape code artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.7",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.7",
            "total_shape_determinations": summary.get("determination_count", 0),
            "calculated": summary.get("results_calculated", 0),
            "deferred": summary.get("deferred_results", 0),
            "blocked": summary.get("blocked_results", 0),
            "failed": summary.get("failed_results", 0),
            "distribution_by_shape_code": summary.get("shape_code_distribution", {}),
            "distribution_by_shape_family": summary.get("shape_family_distribution", {}),
            "distribution_by_role": summary.get("role_distribution", {}),
            "distribution_by_diameter": summary.get("diameter_distribution", {}),
            "distribution_by_beam": summary.get("beam_distribution", {}),
            "distribution_by_rule_source": summary.get("rule_source_distribution", {}),
            "average_cut_length_by_shape": summary.get("average_cut_length_by_shape", {}),
        }
