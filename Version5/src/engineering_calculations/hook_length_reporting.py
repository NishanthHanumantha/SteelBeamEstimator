"""Hook length reporting — Phase I.4."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.hook_length_summary import HookLengthSummary


class HookLengthReporting:
    """Single source of truth for hook length validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        hook_records = model.get("hook_length_results", [])
        registry = model.get("hook_length_registry", {})
        model["hook_length_validation"] = validation
        model["hook_length_summary"] = HookLengthSummary.build(
            bars,
            hook_records,
            registry,
            validation,
        )
        model["hook_length_reporting"] = HookLengthReporting.build(
            model["hook_length_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4",
            "determination_count": summary.get("determination_count", 0),
            "results_calculated": summary.get("results_calculated", 0),
            "deferred_results": summary.get("deferred_results", 0),
            "blocked_results": summary.get("blocked_results", 0),
            "failed_results": summary.get("failed_results", 0),
            "hook_length_distribution": summary.get("hook_length_distribution", {}),
            "hook_angle_distribution": summary.get("hook_angle_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "multiplier_distribution": summary.get("multiplier_distribution", {}),
            "rule_source_distribution": summary.get("rule_source_distribution", {}),
            "average_hook_length_mm": summary.get("average_hook_length_mm", 0.0),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
