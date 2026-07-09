"""Development length reporting — Phase I.3."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.development_length_summary import DevelopmentLengthSummary


class DevelopmentLengthReporting:
    """Single source of truth for development length validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        dev_records = model.get("development_length_results", [])
        registry = model.get("development_length_registry", {})
        model["development_length_validation"] = validation
        model["development_length_summary"] = DevelopmentLengthSummary.build(
            bars,
            dev_records,
            registry,
            validation,
        )
        model["development_length_reporting"] = DevelopmentLengthReporting.build(
            model["development_length_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.3",
            "determination_count": summary.get("determination_count", 0),
            "results_calculated": summary.get("results_calculated", 0),
            "deferred_results": summary.get("deferred_results", 0),
            "development_length_distribution": summary.get("development_length_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "steel_grade_distribution": summary.get("steel_grade_distribution", {}),
            "concrete_grade_distribution": summary.get("concrete_grade_distribution", {}),
            "lookup_table_usage": summary.get("lookup_table_usage", {}),
            "average_development_length_mm": summary.get("average_development_length_mm", 0.0),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
