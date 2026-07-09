"""BBS export helpers — Phase I.10."""

from __future__ import annotations

from typing import Any, List


class BbsExporter:
    """Serialize BBS artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.10",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.10",
            "total_bars": summary.get("bar_count", 0),
            "calculated_groups": summary.get("calculated_groups", 0),
            "bbs_records": summary.get("bbs_records", 0),
            "deferred": summary.get("deferred_results", 0),
            "blocked": summary.get("blocked_results", 0),
            "failed": summary.get("failed_results", 0),
            "duplicate_groups": summary.get("duplicate_groups", 0),
            "largest_schedule": summary.get("largest_schedule", 0),
            "average_members_per_schedule": summary.get("average_members_per_schedule", 0),
            "unique_fabrication_marks": summary.get("unique_fabrication_marks", 0),
            "unique_engineering_signatures": summary.get("unique_engineering_signatures", 0),
            "distribution_by_beam": summary.get("beam_distribution", {}),
            "distribution_by_role": summary.get("role_distribution", {}),
            "distribution_by_diameter": summary.get("diameter_distribution", {}),
            "distribution_by_shape": summary.get("shape_distribution", {}),
            "distribution_by_fabrication_state": summary.get("fabrication_state_distribution", {}),
            "distribution_by_rule_source": summary.get("rule_source_distribution", {}),
        }

    @staticmethod
    def export_report(reporting: dict[str, Any]) -> dict[str, Any]:
        return reporting
