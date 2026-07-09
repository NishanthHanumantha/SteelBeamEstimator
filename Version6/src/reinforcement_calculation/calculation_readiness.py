"""Calculation readiness model — Phase I.2.1."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.reinforcement_calculation.calculation_state import (
    CalculationState,
    is_calculation_ready,
)


def build_calculation_readiness(
    calculation_state: CalculationState,
    defer_reason: str = "",
    upstream_status_summary: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build an immutable calculation readiness record."""
    ready = is_calculation_ready(calculation_state)
    return {
        "calculation_state": calculation_state.value,
        "calculation_ready": ready,
        "defer_reason": "" if ready else str(defer_reason or "Calculation deferred."),
        "upstream_status_summary": dict(upstream_status_summary or {}),
    }


def calculation_readiness_from_object(obj: dict[str, Any]) -> dict[str, Any]:
    """Return the readiness object attached to a reinforcement record."""
    readiness = obj.get("calculation_readiness")
    if isinstance(readiness, dict):
        return readiness
    return build_calculation_readiness(CalculationState.UNKNOWN)


def require_calculation_ready(readiness: dict[str, Any]) -> CalculationState:
    """Standard deferred behavior helper for downstream calculation engines."""
    if readiness.get("calculation_ready"):
        return CalculationState.READY
    state = readiness.get("calculation_state", CalculationState.DEFERRED.value)
    return CalculationState.DEFERRED if state != CalculationState.BLOCKED.value else CalculationState.BLOCKED
