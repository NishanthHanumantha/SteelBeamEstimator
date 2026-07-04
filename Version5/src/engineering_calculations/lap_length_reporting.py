"""Lap length reporting — Phase I.5."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.lap_length_summary import LapLengthSummary


class LapLengthReporting:
    """Single source of truth for lap length validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        lap_records = model.get("lap_length_results", [])
        registry = model.get("lap_length_registry", {})
        model["lap_length_validation"] = validation
        model["lap_length_summary"] = LapLengthSummary.build(
            bars,
            lap_records,
            registry,
            validation,
        )
        model["lap_length_reporting"] = LapLengthReporting.build(
            model["lap_length_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.5",
            "determination_count": summary.get("determination_count", 0),
            "results_calculated": summary.get("results_calculated", 0),
            "deferred_results": summary.get("deferred_results", 0),
            "blocked_results": summary.get("blocked_results", 0),
            "failed_results": summary.get("failed_results", 0),
            "lap_length_distribution": summary.get("lap_length_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "lap_factor_distribution": summary.get("lap_factor_distribution", {}),
            "steel_grade_distribution": summary.get("steel_grade_distribution", {}),
            "concrete_grade_distribution": summary.get("concrete_grade_distribution", {}),
            "rule_source_distribution": summary.get("rule_source_distribution", {}),
            "average_lap_length_mm": summary.get("average_lap_length_mm", 0.0),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
