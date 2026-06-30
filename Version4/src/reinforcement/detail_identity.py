"""Engineering Detail Identity — stable engineering identifier above views."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.reinforcement.reinforcement_geometry_entity import (
    ENGINEERING_STATUS_GEOMETRY_ONLY,
    STATUS_READY,
)

PREFIX_DETAIL = "DETAIL"

MATCHING_STATUS_NOT_MATCHED = "NOT_MATCHED"
MATCHING_STATUS_MATCHING = "MATCHING"
MATCHING_STATUS_MATCHED = "MATCHED"
MATCHING_STATUS_PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
MATCHING_STATUS_FAILED = "FAILED"

MATCHING_STATE_NOT_MATCHED = "NOT_MATCHED"
MATCHING_STATE_CANDIDATES_READY = "CANDIDATES_READY"
MATCHING_STATE_MATCH_COMPLETED = "MATCH_COMPLETED"

SOURCE_DETAIL_CONTEXT = "DETAIL_CONTEXT"


def format_detail_identity_id(index: int) -> str:
    return f"{PREFIX_DETAIL}::{index:03d}"


def detail_identity_id_from_context(detail_context_id: str, fallback_index: int) -> str:
    if "::" in detail_context_id:
        suffix = detail_context_id.split("::", 1)[1]
        return f"{PREFIX_DETAIL}::{suffix}"
    return format_detail_identity_id(fallback_index)


def split_beam_marks(beam_marks: List[str]) -> tuple[str, List[str]]:
    ordered = list(beam_marks)
    if not ordered:
        return "", []
    return ordered[0], ordered[1:]


@dataclass
class EngineeringDetailIdentity:
    """Permanent engineering identity derived from a detail context."""

    detail_identity_id: str
    detail_context_id: str
    detail_type: str
    primary_beam_mark: str
    secondary_beam_marks: List[str] = field(default_factory=list)
    beam_count: int = 0
    view_count: int = 0
    matching_status: str = MATCHING_STATUS_NOT_MATCHED
    engineering_owner: Optional[str] = None
    engineering_status: str = ENGINEERING_STATUS_GEOMETRY_ONLY
    confidence: float = 1.0
    source: str = SOURCE_DETAIL_CONTEXT
    candidate_count: int = 0
    candidate_ids: List[str] = field(default_factory=list)
    best_candidate_id: Optional[str] = None
    matching_state: str = MATCHING_STATE_NOT_MATCHED
    match_decision_id: Optional[str] = None
    decision_status: Optional[str] = None
    beam_match_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detail_identity_id": self.detail_identity_id,
            "detail_context_id": self.detail_context_id,
            "detail_type": self.detail_type,
            "primary_beam_mark": self.primary_beam_mark,
            "secondary_beam_marks": list(self.secondary_beam_marks),
            "beam_count": self.beam_count,
            "view_count": self.view_count,
            "matching_status": self.matching_status,
            "engineering_owner": self.engineering_owner,
            "engineering_status": self.engineering_status,
            "confidence": self.confidence,
            "source": self.source,
            "candidate_count": self.candidate_count,
            "candidate_ids": list(self.candidate_ids),
            "best_candidate_id": self.best_candidate_id,
            "matching_state": self.matching_state,
            "match_decision_id": self.match_decision_id,
            "decision_status": self.decision_status,
            "beam_match_id": self.beam_match_id,
            "metadata": dict(self.metadata),
        }
