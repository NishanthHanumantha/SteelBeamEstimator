"""Floor-level workspace container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FloorWorkspace:
    """Owns floor framing, reinforcement workspace, and beam context references."""

    floor_id: str
    floor_name: str
    framing_plan: dict[str, Any]
    beam_contexts: List[dict[str, Any]]
    reinforcement_workspace: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "floor_id": self.floor_id,
            "floor_name": self.floor_name,
            "framing_plan": self.framing_plan,
            "beam_contexts": self.beam_contexts,
            "metadata": self.metadata,
        }
        if self.reinforcement_workspace is not None:
            payload["reinforcement_workspace"] = self.reinforcement_workspace
        return payload
