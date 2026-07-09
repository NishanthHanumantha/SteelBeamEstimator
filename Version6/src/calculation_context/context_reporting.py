"""Calculation context reporting — Phase I.1."""

from __future__ import annotations

from typing import Any, List

from src.calculation_context.context_summary import CalculationContextSummary


class CalculationContextReporting:
    """Single source of truth for calculation context validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        contexts = model.get("calculation_contexts", [])
        registry = model.get("calculation_context_registry", {})
        model["calculation_context_validation"] = validation
        model["calculation_context_summary"] = CalculationContextSummary.build(
            model.get("engineering_specifications", []),
            contexts,
            registry,
            validation,
        )
        model["calculation_context_reporting"] = CalculationContextReporting.build(
            contexts,
            registry,
            model["calculation_context_summary"],
        )

    @staticmethod
    def build(
        contexts: List[dict[str, Any]],
        registry: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.1",
            "context_count": len(contexts),
            "context_statistics": summary.get("context_status", {}),
            "coverage": {
                "material_coverage": summary.get("material_coverage", {}),
                "geometry_coverage": summary.get("geometry_coverage", {}),
                "rule_coverage": summary.get("rule_coverage", {}),
            },
            "completeness": {
                "average_context_completeness": summary.get(
                    "average_context_completeness", 0.0
                ),
                "contexts_missing": summary.get("contexts_missing", 0),
            },
            "validation_summary": summary.get("validation_summary", {}),
            "registry_summary": summary.get("registry_statistics", {}),
            "context_version": summary.get("context_version", "I.1"),
        }
