"""Unified drawing identity model for all drawing types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


DRAWING_TYPE_GENERAL_NOTES = "GENERAL_NOTES"
DRAWING_TYPE_FRAMING_PLAN = "FRAMING_PLAN"
DRAWING_TYPE_BEAM_REINFORCEMENT = "BEAM_REINFORCEMENT"

DISCIPLINE_STRUCTURAL = "STRUCTURAL"
STATUS_IDENTIFIED = "IDENTIFIED"
STATUS_UNKNOWN = "UNKNOWN"

DRAWING_ID_SUFFIX = {
    DRAWING_TYPE_FRAMING_PLAN: "FRAMING",
    DRAWING_TYPE_BEAM_REINFORCEMENT: "REINFORCEMENT",
    DRAWING_TYPE_GENERAL_NOTES: "GENERAL_NOTES",
}


def drawing_id_for(floor_slug: Optional[str], drawing_type: str) -> str:
    if drawing_type == DRAWING_TYPE_GENERAL_NOTES:
        return "DRAWING::GENERAL_NOTES"
    slug = floor_slug or "UNKNOWN"
    suffix = DRAWING_ID_SUFFIX.get(drawing_type, drawing_type)
    return f"DRAWING::{slug}::{suffix}"


def framing_workspace_id(floor_slug: str) -> str:
    return f"FRAMING_WORKSPACE::{floor_slug}"


@dataclass
class DrawingIdentity:
    """Authoritative identity for a loaded engineering drawing."""

    drawing_id: str
    drawing_type: str
    discipline: str
    floor_id: Optional[str]
    floor_name: Optional[str]
    floor_slug: Optional[str]
    project_id: str
    revision: str
    sheet_number: str
    drawing_title: str
    status: str
    confidence: float
    source_file: str
    detection_source: str = "UNKNOWN"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drawing_id": self.drawing_id,
            "drawing_type": self.drawing_type,
            "discipline": self.discipline,
            "floor_id": self.floor_id,
            "floor_name": self.floor_name,
            "floor_slug": self.floor_slug,
            "project_id": self.project_id,
            "revision": self.revision,
            "sheet_number": self.sheet_number,
            "drawing_title": self.drawing_title,
            "status": self.status,
            "confidence": self.confidence,
            "source_file": self.source_file,
            "detection_source": self.detection_source,
            "metadata": self.metadata,
        }
