"""Computation state machine for Phase G engineering workflows."""

from __future__ import annotations

from typing import Any, FrozenSet

STATE_NOT_STARTED = "NOT_STARTED"
STATE_READY = "READY"
STATE_RUNNING = "RUNNING"
STATE_COMPUTED = "COMPUTED"
STATE_VALIDATED = "VALIDATED"
STATE_FAILED = "FAILED"

VALID_COMPUTATION_STATES: FrozenSet[str] = frozenset(
    {
        STATE_NOT_STARTED,
        STATE_READY,
        STATE_RUNNING,
        STATE_COMPUTED,
        STATE_VALIDATED,
        STATE_FAILED,
    }
)

# Allowed transitions for Phase G orchestration
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATE_NOT_STARTED: frozenset({STATE_READY, STATE_RUNNING}),
    STATE_READY: frozenset({STATE_RUNNING, STATE_NOT_STARTED}),
    STATE_RUNNING: frozenset({STATE_COMPUTED, STATE_FAILED, STATE_READY}),
    STATE_COMPUTED: frozenset({STATE_VALIDATED, STATE_FAILED, STATE_RUNNING}),
    STATE_VALIDATED: frozenset({STATE_COMPUTED, STATE_FAILED}),
    STATE_FAILED: frozenset({STATE_READY, STATE_NOT_STARTED, STATE_RUNNING}),
}


class EngineeringStateMachine:
    """Track and validate computation lifecycle states."""

    def __init__(self, initial: str = STATE_NOT_STARTED) -> None:
        self._state = self._normalize(initial)

    @property
    def state(self) -> str:
        return self._state

    def can_transition(self, target: str) -> bool:
        target = self._normalize(target)
        return target in ALLOWED_TRANSITIONS.get(self._state, frozenset())

    def transition(self, target: str) -> str:
        target = self._normalize(target)
        if not self.can_transition(target):
            raise ValueError(f"Invalid transition {self._state} -> {target}")
        self._state = target
        return self._state

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "allowed_next": sorted(ALLOWED_TRANSITIONS.get(self._state, frozenset())),
        }

    @staticmethod
    def placeholder() -> dict[str, str]:
        return {"status": STATE_NOT_STARTED}

    @staticmethod
    def _normalize(state: str) -> str:
        normalized = str(state).upper()
        if normalized == "NOT_COMPUTED":
            return STATE_NOT_STARTED
        if normalized not in VALID_COMPUTATION_STATES:
            return STATE_NOT_STARTED
        return normalized
