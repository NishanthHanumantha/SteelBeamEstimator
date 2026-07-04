"""Calculation dependency reporting — Phase I.4.6."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.calculation_dependency.dependency_summary import (
    CalculationDependencySummary,
)


class CalculationDependencyReporting:
    """Single source of truth for dependency graph validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        graph = model.get("calculation_dependency_graph", {})
        registry = model.get("calculation_dependency_registry", {})
        model["calculation_dependency_validation"] = validation
        model["calculation_dependency_summary"] = CalculationDependencySummary.build(
            graph,
            registry,
            validation,
        )
        model["calculation_dependency_reporting"] = CalculationDependencyReporting.build(
            model["calculation_dependency_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4.6",
            "node_count": summary.get("node_count", 0),
            "ordered_categories": summary.get("ordered_categories", []),
            "metadata_only": summary.get("metadata_only", True),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
