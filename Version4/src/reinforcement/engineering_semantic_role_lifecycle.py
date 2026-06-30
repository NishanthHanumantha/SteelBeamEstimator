"""Lifecycle state machine for Engineering Semantic Roles."""

from __future__ import annotations

from typing import Any, FrozenSet, List

STATE_DISCOVERED = "DISCOVERED"
STATE_CLASSIFIED = "CLASSIFIED"
STATE_VALIDATED = "VALIDATED"
STATE_CONSUMED = "CONSUMED"
STATE_FAILED = "FAILED"

VALID_SEMANTIC_ROLE_LIFECYCLE: FrozenSet[str] = frozenset({
    STATE_DISCOVERED,
    STATE_CLASSIFIED,
    STATE_VALIDATED,
    STATE_CONSUMED,
    STATE_FAILED,
})

TRANSITIONS: dict[str, list[str]] = {
    STATE_DISCOVERED: [STATE_CLASSIFIED, STATE_FAILED],
    STATE_CLASSIFIED: [STATE_VALIDATED, STATE_CONSUMED, STATE_FAILED],
    STATE_VALIDATED: [STATE_CONSUMED],
    STATE_CONSUMED: [],
    STATE_FAILED: [],
}


class EngineeringSemanticRoleLifecycle:
    """Lifecycle metadata for semantic roles."""

    @staticmethod
    def current_phase_state() -> str:
        return STATE_CLASSIFIED

    @staticmethod
    def is_valid(state: str) -> bool:
        return state in VALID_SEMANTIC_ROLE_LIFECYCLE

    @staticmethod
    def next_allowed(state: str) -> List[str]:
        return list(TRANSITIONS.get(state, []))

    @staticmethod
    def build_entry(
        reinforcement_context_id: str,
        beam_mark: str,
        role_count: int = 0,
    ) -> dict[str, Any]:
        return {
            "reinforcement_context_id": reinforcement_context_id,
            "beam_mark": beam_mark,
            "role_count": role_count,
            "current_state": EngineeringSemanticRoleLifecycle.current_phase_state(),
            "status": "ROLE_CLASSIFIED",
        }
