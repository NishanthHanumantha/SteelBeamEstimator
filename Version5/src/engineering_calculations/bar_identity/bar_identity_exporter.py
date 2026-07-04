"""Bar identity export helpers — Phase I.8."""

from __future__ import annotations

from typing import Any, List


class BarIdentityExporter:
    """Serialize bar identity artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.8",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.8",
            "total_bar_identity_determinations": summary.get("determination_count", 0),
            "calculated": summary.get("results_calculated", 0),
            "deferred": summary.get("deferred_results", 0),
            "blocked": summary.get("blocked_results", 0),
            "failed": summary.get("failed_results", 0),
            "grouped_bars": summary.get("grouped_bars", 0),
            "unique_groups": summary.get("unique_groups", 0),
            "unique_engineering_identities": summary.get("unique_engineering_identities", 0),
            "duplicate_bars": summary.get("duplicate_bars", 0),
            "distribution_by_beam": summary.get("beam_distribution", {}),
            "distribution_by_role": summary.get("role_distribution", {}),
            "distribution_by_diameter": summary.get("diameter_distribution", {}),
            "distribution_by_shape_code": summary.get("shape_code_distribution", {}),
            "distribution_by_rule_source": summary.get("rule_source_distribution", {}),
        }
