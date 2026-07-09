"""Drawing set — engineering-level grouping of related drawings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


STATUS_COMPLETE = "COMPLETE"
STATUS_PARTIAL = "PARTIAL"


def drawing_set_id(floor_slug: str) -> str:
    return f"DRAWING_SET::{floor_slug}"


@dataclass
class DrawingSet:
    """Groups framing, reinforcement, and references for one engineering level."""

    drawing_set_id: str
    floor_id: str
    floor_name: str
    project_id: str
    status: str
    drawings: Dict[str, Optional[str]]
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    # G.1.3 fields (optional until lifecycle enrichment)
    drawing_set_version: Optional[Dict[str, Any]] = None
    beam_index: Optional[Dict[str, str]] = None
    beam_index_meta: Optional[Dict[str, Any]] = None
    loading_state: Optional[str] = None
    matching_state: Optional[str] = None
    parsing_state: Optional[str] = None
    engineering_state: Optional[str] = None
    quantity_state: Optional[str] = None
    boq_state: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "drawing_set_id": self.drawing_set_id,
            "floor_id": self.floor_id,
            "floor_name": self.floor_name,
            "project_id": self.project_id,
            "status": self.status,
            "drawings": dict(self.drawings),
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
        if self.drawing_set_version is not None:
            payload["drawing_set_version"] = self.drawing_set_version
        if self.beam_index is not None:
            payload["beam_index"] = dict(self.beam_index)
        if self.beam_index_meta is not None:
            payload["beam_index_meta"] = self.beam_index_meta
        for field_name in (
            "loading_state",
            "matching_state",
            "parsing_state",
            "engineering_state",
            "quantity_state",
            "boq_state",
        ):
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = value
        return payload
