"""Calculation state enum — Phase I.2.1."""

from __future__ import annotations

from enum import Enum


class CalculationState(str, Enum):
    """Strongly typed calculation execution state for engineering engines."""

    UNKNOWN = "UNKNOWN"
    READY = "READY"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


VALID_EVALUATED_STATES = frozenset({
    CalculationState.READY,
    CalculationState.DEFERRED,
    CalculationState.BLOCKED,
})


def is_calculation_ready(state: CalculationState | str) -> bool:
    """Return True only when engineering calculations may execute."""
    if isinstance(state, CalculationState):
        return state == CalculationState.READY
    return str(state) == CalculationState.READY.value


def parse_calculation_state(value: str | None) -> CalculationState:
    """Parse a calculation state string into the enum."""
    if not value:
        return CalculationState.UNKNOWN
    try:
        return CalculationState(str(value))
    except ValueError:
        return CalculationState.UNKNOWN
