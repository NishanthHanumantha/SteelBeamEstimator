"""Engineering Detail Context — engineering grouping above views, below ownership."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.reinforcement.reinforcement_geometry_entity import (
    ENGINEERING_STATUS_GEOMETRY_ONLY,
    STATUS_READY,
)

PREFIX_DETAIL_CTX = "DETAIL_CTX"

DETAIL_TYPE_SINGLE_BEAM = "SINGLE_BEAM"
DETAIL_TYPE_MULTI_VIEW_SINGLE_BEAM = "MULTI_VIEW_SINGLE_BEAM"
DETAIL_TYPE_CONTINUOUS_MULTI_SPAN = "CONTINUOUS_MULTI_SPAN"
DETAIL_TYPE_UNKNOWN = "UNKNOWN"

SOURCE_REGION_CLASSIFICATION = "REGION_CLASSIFICATION"


def format_detail_context_id(index: int) -> str:
    return f"{PREFIX_DETAIL_CTX}::{index:03d}"


def detail_context_id_from_region(region_id: str, fallback_index: int) -> str:
    if "::" in region_id:
        suffix = region_id.split("::", 1)[1]
        return f"{PREFIX_DETAIL_CTX}::{suffix}"
    return format_detail_context_id(fallback_index)


@dataclass
class EngineeringDetailContext:
    """One engineering detailing concept derived from a classified region."""

    detail_context_id: str
    detail_type: str
    region_id: str
    view_ids: List[str] = field(default_factory=list)
    beam_marks: List[str] = field(default_factory=list)
    beam_count: int = 0
    view_count: int = 0
    status: str = STATUS_READY
    engineering_status: str = ENGINEERING_STATUS_GEOMETRY_ONLY
    geometry_status: str = STATUS_READY
    engineering_object_id: Optional[str] = None
    detail_identity_id: Optional[str] = None
    confidence: float = 1.0
    source: str = SOURCE_REGION_CLASSIFICATION
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detail_context_id": self.detail_context_id,
            "detail_type": self.detail_type,
            "region_id": self.region_id,
            "view_ids": list(self.view_ids),
            "beam_marks": list(self.beam_marks),
            "beam_count": self.beam_count,
            "view_count": self.view_count,
            "status": self.status,
            "engineering_status": self.engineering_status,
            "geometry_status": self.geometry_status,
            "engineering_object_id": self.engineering_object_id,
            "detail_identity_id": self.detail_identity_id,
            "confidence": self.confidence,
            "source": self.source,
            "metadata": dict(self.metadata),
        }
