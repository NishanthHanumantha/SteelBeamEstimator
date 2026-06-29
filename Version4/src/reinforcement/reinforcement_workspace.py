"""Reinforcement workspace container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.reinforcement.reinforcement_document import ReinforcementDocument, STATUS_LOADED


@dataclass
class ReinforcementWorkspace:
    """Floor-scoped reinforcement drawing workspace (loading only in G.1)."""

    workspace_id: str
    document: ReinforcementDocument
    beam_regions: List[dict[str, Any]] = field(default_factory=list)
    annotation_regions: List[dict[str, Any]] = field(default_factory=list)
    text_entities: List[dict[str, Any]] = field(default_factory=list)
    blocks: List[dict[str, Any]] = field(default_factory=list)
    status: str = STATUS_LOADED
    floor_id: str = ""
    floor_slug: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "status": self.status,
            "floor_id": self.floor_id,
            "floor_slug": self.floor_slug,
            "document": self.document.to_dict(),
            "beam_regions": list(self.beam_regions),
            "annotation_regions": list(self.annotation_regions),
            "text_entities": list(self.text_entities),
            "blocks": list(self.blocks),
        }
