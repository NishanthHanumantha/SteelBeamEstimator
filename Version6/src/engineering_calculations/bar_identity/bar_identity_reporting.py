"""Bar identity reporting — Phase I.8."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.bar_identity.bar_identity_summary import BarIdentitySummary


class BarIdentityReporting:
    """Single source of truth for bar identity validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        identity_records = model.get("bar_identity_results", [])
        registry = model.get("bar_identity_registry", {})
        model["bar_identity_validation"] = validation
        model["bar_identity_summary"] = BarIdentitySummary.build(
            bars,
            identity_records,
            registry,
            validation,
        )
        model["bar_identity_reporting"] = BarIdentityReporting.build(
            model["bar_identity_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.8",
            "determination_count": summary.get("determination_count", 0),
            "results_calculated": summary.get("results_calculated", 0),
            "deferred_results": summary.get("deferred_results", 0),
            "blocked_results": summary.get("blocked_results", 0),
            "failed_results": summary.get("failed_results", 0),
            "grouped_bars": summary.get("grouped_bars", 0),
            "unique_groups": summary.get("unique_groups", 0),
            "unique_engineering_identities": summary.get("unique_engineering_identities", 0),
            "duplicate_bars": summary.get("duplicate_bars", 0),
            "role_distribution": summary.get("role_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "beam_distribution": summary.get("beam_distribution", {}),
            "shape_code_distribution": summary.get("shape_code_distribution", {}),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
