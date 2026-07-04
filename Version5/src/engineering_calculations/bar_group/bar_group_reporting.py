"""Bar group reporting — Phase I.9."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.bar_group.bar_group_summary import BarGroupSummary


class BarGroupReporting:
    """Single source of truth for bar group validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        identity_records = model.get("bar_identity_results", [])
        group_records = model.get("bar_group_results", [])
        registry = model.get("bar_group_registry", {})
        model["bar_group_validation"] = validation
        model["bar_group_summary"] = BarGroupSummary.build(
            bars,
            identity_records,
            group_records,
            registry,
            validation,
        )
        model["bar_group_reporting"] = BarGroupReporting.build(
            model["bar_group_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.9",
            "bar_count": summary.get("bar_count", 0),
            "calculated_identities": summary.get("calculated_identities", 0),
            "total_groups": summary.get("total_groups", 0),
            "duplicate_groups": summary.get("duplicate_groups", 0),
            "largest_group_size": summary.get("largest_group_size", 0),
            "average_group_size": summary.get("average_group_size", 0),
            "unique_engineering_signatures": summary.get("unique_engineering_signatures", 0),
            "results_calculated": summary.get("results_calculated", 0),
            "deferred_results": summary.get("deferred_results", 0),
            "blocked_results": summary.get("blocked_results", 0),
            "failed_results": summary.get("failed_results", 0),
            "role_distribution": summary.get("role_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "beam_distribution": summary.get("beam_distribution", {}),
            "shape_distribution": summary.get("shape_distribution", {}),
            "cut_length_distribution": summary.get("cut_length_distribution", {}),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
