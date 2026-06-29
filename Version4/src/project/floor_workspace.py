"""Floor-level workspace container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FloorWorkspace:
    """Owns floor framing, reinforcement plans, and beam context references."""

    floor_id: str
    floor_name: str
    framing_plan: dict[str, Any]
    reinforcement_plan: dict[str, Any]
    beam_contexts: List[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "floor_id": self.floor_id,
            "floor_name": self.floor_name,
            "framing_plan": self.framing_plan,
            "reinforcement_plan": self.reinforcement_plan,
            "beam_contexts": self.beam_contexts,
            "metadata": self.metadata,
        }
