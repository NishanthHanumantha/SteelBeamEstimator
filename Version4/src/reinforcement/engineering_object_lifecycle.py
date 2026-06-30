"""Engineering Object lifecycle state machine — architecture for G.5+."""

from __future__ import annotations

from typing import Any, FrozenSet, List, Optional

STATE_NOT_CREATED = "NOT_CREATED"
STATE_PLACEHOLDER_CREATED = "PLACEHOLDER_CREATED"
STATE_CREATED = "CREATED"
STATE_READY_FOR_PARSING = "READY_FOR_PARSING"
STATE_PARSED = "PARSED"
STATE_VALIDATED = "VALIDATED"
STATE_COMPUTED = "COMPUTED"
STATE_BOQ_READY = "BOQ_READY"
STATE_COMPLETED = "COMPLETED"
STATE_FAILED = "FAILED"

VALID_OBJECT_LIFECYCLE_STATES: FrozenSet[str] = frozenset({
    STATE_NOT_CREATED,
    STATE_PLACEHOLDER_CREATED,
    STATE_CREATED,
    STATE_READY_FOR_PARSING,
    STATE_PARSED,
    STATE_VALIDATED,
    STATE_COMPUTED,
    STATE_BOQ_READY,
    STATE_COMPLETED,
    STATE_FAILED,
})

TRANSITIONS: dict[str, list[str]] = {
    STATE_NOT_CREATED: [STATE_PLACEHOLDER_CREATED],
    STATE_PLACEHOLDER_CREATED: [STATE_READY_FOR_PARSING, STATE_CREATED],
    STATE_CREATED: [STATE_PARSED, STATE_FAILED],
    STATE_READY_FOR_PARSING: [STATE_PARSED, STATE_FAILED, STATE_CREATED],
    STATE_PARSED: [STATE_VALIDATED, STATE_FAILED],
    STATE_VALIDATED: [STATE_COMPUTED, STATE_FAILED],
    STATE_COMPUTED: [STATE_BOQ_READY, STATE_FAILED],
    STATE_BOQ_READY: [STATE_COMPLETED],
    STATE_COMPLETED: [],
    STATE_FAILED: [],
}

PREFIX_OBJECT_LIFECYCLE = "ENG_OBJ_LIFECYCLE"


class EngineeringObjectLifecycle:
    """Lifecycle metadata for engineering objects."""

    @staticmethod
    def is_valid_state(state: str) -> bool:
        return state in VALID_OBJECT_LIFECYCLE_STATES

    @staticmethod
    def next_allowed(state: str) -> List[str]:
        return list(TRANSITIONS.get(state, []))

    @staticmethod
    def initial_framework_state() -> str:
        """Framework-ready state when no objects exist yet."""
        return STATE_READY_FOR_PARSING

    @staticmethod
    def build_registry_entry(
        reinforcement_context_id: str,
        beam_mark: str,
        object_count: int = 0,
    ) -> dict[str, Any]:
        return {
            "reinforcement_context_id": reinforcement_context_id,
            "beam_mark": beam_mark,
            "lifecycle_id": f"{PREFIX_OBJECT_LIFECYCLE}::{beam_mark.upper()}",
            "object_count": object_count,
            "current_state": EngineeringObjectLifecycle.initial_framework_state(),
            "status": "READY_FOR_G5",
        }

    @staticmethod
    def instantiated_state() -> str:
        return STATE_CREATED

    @staticmethod
    def build_project_registry(contexts: list, phase: str = "Phase G.4.2") -> dict[str, Any]:
        entries = [
            EngineeringObjectLifecycle.build_registry_entry(
                c.get("reinforcement_context_id", ""),
                str(c.get("beam_mark", "")),
                len(c.get("engineering_objects", {}).get("objects", [])),
            )
            for c in contexts
        ]
        return {
            "namespace": "ENG_OBJ_LIFECYCLE",
            "phase": phase,
            "context_count": len(entries),
            "current_state": (
                EngineeringObjectLifecycle.instantiated_state()
                if any(e.get("object_count", 0) > 0 for e in entries)
                else EngineeringObjectLifecycle.initial_framework_state()
            ),
            "ercs": entries,
        }
