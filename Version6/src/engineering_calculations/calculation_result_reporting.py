"""Calculation result reporting — Phase I.2.2."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.calculation_result_summary import CalculationResultSummary


class CalculationResultReporting:
    """Single source of truth for calculation result validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        registry = model.get("calculation_result_registry", {})
        model["calculation_result_validation"] = validation
        model["calculation_result_summary"] = CalculationResultSummary.build(
            bars,
            results,
            registry,
            validation,
        )
        model["calculation_result_reporting"] = CalculationResultReporting.build(
            model["calculation_result_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.2.2",
            "result_count": summary.get("result_count", 0),
            "results_by_state": summary.get("results_by_state", {}),
            "state_summary": summary.get("state_summary", {}),
            "results_by_calculation_type": summary.get("results_by_calculation_type", {}),
            "coverage": summary.get("coverage", {}),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
