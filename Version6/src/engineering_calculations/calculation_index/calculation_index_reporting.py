"""Calculation index reporting — Phase I.4.5."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.calculation_index.calculation_index_summary import (
    CalculationIndexSummary,
)


class CalculationIndexReporting:
    """Single source of truth for calculation index validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        indexes = model.get("calculation_indexes", [])
        registry = model.get("calculation_index_registry", {})
        model["calculation_index_validation"] = validation
        model["calculation_index_summary"] = CalculationIndexSummary.build(
            bars,
            results,
            indexes,
            registry,
            validation,
        )
        model["calculation_index_reporting"] = CalculationIndexReporting.build(
            model["calculation_index_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4.5",
            "bar_count": summary.get("bar_count", 0),
            "indexed_calculations": summary.get("indexed_calculations", 0),
            "category_counts": summary.get("category_counts", {}),
            "development_length_count": summary.get("development_length_count", 0),
            "hook_length_count": summary.get("hook_length_count", 0),
            "average_calculations_per_bar": summary.get("average_calculations_per_bar", 0.0),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
