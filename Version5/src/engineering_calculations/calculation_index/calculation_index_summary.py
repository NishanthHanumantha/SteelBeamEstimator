"""Calculation index summary — Phase I.4.5."""

from __future__ import annotations

from collections import Counter
from typing import Any, List

from src.engineering_calculations.calculation_index.calculation_index_types import (
    CATEGORY_DEVELOPMENT_LENGTH,
    CATEGORY_HOOK_LENGTH,
    CREATED_PHASE,
    PHASE_LABEL,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState


class CalculationIndexSummary:
    """Build project-level calculation index summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        results: List[dict[str, Any]],
        indexes: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        category_counts = Counter()
        indexed_calculations = 0
        for index in indexes:
            references = index.get("references") or {}
            indexed_calculations += len(references)
            for category in references:
                category_counts[str(category)] += 1

        results_by_state = Counter(
            str(item.get("calculation_state", "")) for item in results
        )

        return {
            "phase": PHASE_LABEL,
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "total_calculation_results": len(results),
            "indexed_calculations": indexed_calculations,
            "category_counts": dict(sorted(category_counts.items())),
            "development_length_count": category_counts.get(CATEGORY_DEVELOPMENT_LENGTH, 0),
            "hook_length_count": category_counts.get(CATEGORY_HOOK_LENGTH, 0),
            "deferred_count": results_by_state.get(CalculationResultState.DEFERRED.value, 0),
            "blocked_count": results_by_state.get(CalculationResultState.BLOCKED.value, 0),
            "calculated_count": results_by_state.get(CalculationResultState.CALCULATED.value, 0),
            "average_calculations_per_bar": round(indexed_calculations / len(bars), 2) if bars else 0.0,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "index_count": registry.get("index_count", 0),
                "result_count": registry.get("result_count", 0),
                "category_counts": registry.get("category_counts", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
