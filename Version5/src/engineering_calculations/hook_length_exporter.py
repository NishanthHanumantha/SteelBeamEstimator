"""Hook length export helpers — Phase I.4."""

from __future__ import annotations

from typing import Any, List


class HookLengthExporter:
    """Serialize hook length artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4",
            "total_hook_determinations": summary.get("determination_count", 0),
            "calculated": summary.get("results_calculated", 0),
            "deferred": summary.get("deferred_results", 0),
            "blocked": summary.get("blocked_results", 0),
            "failed": summary.get("failed_results", 0),
            "average_hook_length_mm": summary.get("average_hook_length_mm", 0.0),
            "min_hook_length_mm": summary.get("min_hook_length_mm"),
            "max_hook_length_mm": summary.get("max_hook_length_mm"),
            "distribution_by_hook_angle": summary.get("hook_angle_distribution", {}),
            "distribution_by_diameter": summary.get("diameter_distribution", {}),
            "distribution_by_multiplier": summary.get("multiplier_distribution", {}),
            "distribution_by_rule_source": summary.get("rule_source_distribution", {}),
        }
