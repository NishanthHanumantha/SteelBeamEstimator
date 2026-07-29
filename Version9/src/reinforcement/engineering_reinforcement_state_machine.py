"""ERC lifecycle state machine — architectural scaffolding for G.5–G.7."""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional

STATE_OWNERSHIP_READY = "OWNERSHIP_READY"
STATE_PARSING_READY = "PARSING_READY"
STATE_PARSING_IN_PROGRESS = "PARSING_IN_PROGRESS"
STATE_PARSED = "PARSED"
STATE_QUANTITY_READY = "QUANTITY_READY"
STATE_QUANTITY_COMPUTED = "QUANTITY_COMPUTED"
STATE_BOQ_READY = "BOQ_READY"
STATE_COMPLETED = "COMPLETED"
STATE_FAILED = "FAILED"

LIFECYCLE_STATUS_READY = "READY"

VALID_STATES: FrozenSet[str] = frozenset({
    STATE_OWNERSHIP_READY,
    STATE_PARSING_READY,
    STATE_PARSING_IN_PROGRESS,
    STATE_PARSED,
    STATE_QUANTITY_READY,
    STATE_QUANTITY_COMPUTED,
    STATE_BOQ_READY,
    STATE_COMPLETED,
    STATE_FAILED,
})

TRANSITIONS: dict[str, list[str]] = {
    STATE_OWNERSHIP_READY: [STATE_PARSING_READY],
    STATE_PARSING_READY: [STATE_PARSING_IN_PROGRESS],
    STATE_PARSING_IN_PROGRESS: [STATE_PARSED, STATE_FAILED],
    STATE_PARSED: [STATE_QUANTITY_READY],
    STATE_QUANTITY_READY: [STATE_QUANTITY_COMPUTED],
    STATE_QUANTITY_COMPUTED: [STATE_BOQ_READY],
    STATE_BOQ_READY: [STATE_COMPLETED],
    STATE_COMPLETED: [],
    STATE_FAILED: [],
}

PREFIX_ERC_LIFECYCLE = "ERC_LIFECYCLE"


def format_erc_lifecycle_id(beam_mark: str) -> str:
    return f"{PREFIX_ERC_LIFECYCLE}::{beam_mark.upper()}"


class EngineeringReinforcementLifecycle:
    """Lifecycle metadata for one Engineering Reinforcement Context."""

    @staticmethod
    def initial(
        current_state: str = STATE_OWNERSHIP_READY,
        previous_state: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "current_state": current_state,
            "previous_state": previous_state,
            "next_allowed": list(TRANSITIONS.get(current_state, [])),
            "status": LIFECYCLE_STATUS_READY,
        }

    @staticmethod
    def is_valid_state(state: str) -> bool:
        return state in VALID_STATES

    @staticmethod
    def next_allowed(state: str) -> List[str]:
        return list(TRANSITIONS.get(state, []))
