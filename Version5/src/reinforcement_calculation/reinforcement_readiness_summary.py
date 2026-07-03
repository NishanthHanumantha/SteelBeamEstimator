"""Calculation readiness summary — Phase I.2.1."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from src.reinforcement_calculation.calculation_state import CalculationState
from src.reinforcement_calculation.reinforcement_types import READINESS_PHASE


class ReinforcementReadinessSummary:
    """Build project-level calculation readiness summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        state_counts = Counter(
            (bar.get("calculation_readiness") or {}).get("calculation_state", "UNKNOWN")
            for bar in bars
        )
        defer_reasons = Counter(
            (bar.get("calculation_readiness") or {}).get("defer_reason", "")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        ready_count = state_counts.get(CalculationState.READY.value, 0)
        total = len(bars) if bars else 0

        return {
            "phase": "Phase I.2.1",
            "readiness_phase": READINESS_PHASE,
            "ready_count": ready_count,
            "deferred_count": state_counts.get(CalculationState.DEFERRED.value, 0),
            "blocked_count": state_counts.get(CalculationState.BLOCKED.value, 0),
            "completed_count": state_counts.get(CalculationState.COMPLETED.value, 0),
            "bar_count": len(bars),
            "group_count": len(groups),
            "defer_reasons": dict(defer_reasons),
            "readiness_coverage": {
                "ready_count": ready_count,
                "total_bars": total,
                "coverage_rate": round(ready_count / total, 4) if total else 0.0,
            },
            "registry_statistics": registry.get("readiness_counts", {}),
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
