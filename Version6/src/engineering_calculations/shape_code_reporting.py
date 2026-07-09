"""Shape code reporting — Phase I.7."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.shape_code_summary import ShapeCodeSummary


class ShapeCodeReporting:
    """Single source of truth for shape code validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        shape_records = model.get("shape_code_results", [])
        registry = model.get("shape_code_registry", {})
        model["shape_code_validation"] = validation
        model["shape_code_summary"] = ShapeCodeSummary.build(
            bars,
            shape_records,
            registry,
            validation,
        )
        model["shape_code_reporting"] = ShapeCodeReporting.build(
            model["shape_code_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.7",
            "determination_count": summary.get("determination_count", 0),
            "results_calculated": summary.get("results_calculated", 0),
            "deferred_results": summary.get("deferred_results", 0),
            "blocked_results": summary.get("blocked_results", 0),
            "failed_results": summary.get("failed_results", 0),
            "shape_code_distribution": summary.get("shape_code_distribution", {}),
            "shape_family_distribution": summary.get("shape_family_distribution", {}),
            "role_distribution": summary.get("role_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "beam_distribution": summary.get("beam_distribution", {}),
            "rule_source_distribution": summary.get("rule_source_distribution", {}),
            "average_cut_length_by_shape": summary.get("average_cut_length_by_shape", {}),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
