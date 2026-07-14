"""Lifecycle registry export for Engineering Reinforcement Contexts."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.engineering_reinforcement_state_machine import (
    STATE_OWNERSHIP_READY,
    format_erc_lifecycle_id,
)


class EngineeringReinforcementLifecycleRegistry:
    """Build project-level ERC lifecycle registry."""

    @staticmethod
    def build_registry(contexts: List[dict[str, Any]]) -> dict[str, Any]:
        entries = []
        for ctx in contexts:
            beam_mark = str(ctx.get("beam_mark", ""))
            lifecycle = dict(ctx.get("lifecycle", {}))
            entries.append(
                {
                    "reinforcement_context_id": ctx.get("reinforcement_context_id"),
                    "beam_mark": beam_mark,
                    "beam_match_id": ctx.get("beam_match_id"),
                    "lifecycle_id": format_erc_lifecycle_id(beam_mark),
                    "lifecycle": lifecycle,
                }
            )
        return {
            "namespace": "ERC_LIFECYCLE",
            "phase": "Phase G.4.1",
            "context_count": len(entries),
            "current_state": STATE_OWNERSHIP_READY,
            "ercs": entries,
        }

    @staticmethod
    def build_summary(contexts: List[dict[str, Any]]) -> dict[str, Any]:
        states = [c.get("lifecycle", {}).get("current_state") for c in contexts]
        uniform = len(set(states)) == 1 if states else False
        return {
            "phase": "Phase G.4.1",
            "context_count": len(contexts),
            "current_state": states[0] if uniform and states else STATE_OWNERSHIP_READY,
            "all_ownership_ready": all(s == STATE_OWNERSHIP_READY for s in states),
            "status": "READY",
        }
