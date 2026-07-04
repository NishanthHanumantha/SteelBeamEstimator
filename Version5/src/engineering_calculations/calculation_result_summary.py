"""Calculation result summary — Phase I.2.2."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_calculations.calculation_result_types import (
    CREATED_PHASE,
    CalculationResultState,
)


class CalculationResultSummary:
    """Build project-level calculation result framework summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        results: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        by_state: Dict[str, int] = dict(registry.get("results_by_state", {}))
        by_type: Dict[str, int] = dict(registry.get("results_by_calculation_type", {}))
        ready_count = by_state.get(CalculationResultState.READY.value, 0)
        total = len(results)

        return {
            "phase": "Phase I.2.2",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "result_count": len(results),
            "results_by_state": by_state,
            "results_by_calculation_type": by_type,
            "state_summary": {
                "ready": ready_count,
                "deferred": by_state.get(CalculationResultState.DEFERRED.value, 0),
                "blocked": by_state.get(CalculationResultState.BLOCKED.value, 0),
                "failed": by_state.get(CalculationResultState.FAILED.value, 0),
                "calculated": by_state.get(CalculationResultState.CALCULATED.value, 0),
            },
            "coverage": {
                "result_count": len(results),
                "bar_count": len(bars),
                "results_per_bar": round(len(results) / len(bars), 2) if bars else 0.0,
                "ready_coverage_rate": round(ready_count / total, 4) if total else 0.0,
            },
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "result_count": registry.get("result_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_calculation_type": by_type,
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
            "calculation_inputs_summary": {
                "results_with_inputs": len(results),
                "empty_inputs": sum(
                    1 for item in results if not (item.get("calculation_inputs") or {})
                ),
                "populated_inputs": sum(
                    1 for item in results if item.get("calculation_inputs")
                ),
            },
        }
