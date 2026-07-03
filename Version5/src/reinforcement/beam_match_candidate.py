"""Beam match candidate — ranked possible beam association before final matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

PREFIX_CANDIDATE = "CANDIDATE"

CANDIDATE_STATUS_GENERATED = "GENERATED"
CANDIDATE_STATUS_RANKED = "RANKED"
CANDIDATE_STATUS_SELECTED = "SELECTED"
CANDIDATE_STATUS_REJECTED = "REJECTED"

REASON_DIRECT_BEAM_MARK = "DIRECT_BEAM_MARK"
REASON_CONTINUOUS_MULTI_SPAN = "CONTINUOUS_MULTI_SPAN"
REASON_MULTI_VIEW_SINGLE_BEAM = "MULTI_VIEW_SINGLE_BEAM"
REASON_DRAWING_SET_MATCH = "DRAWING_SET_MATCH"
REASON_NO_MATCH = "NO_MATCH"

ALGORITHM_DIRECT_LABEL_MATCH = "DIRECT_LABEL_MATCH"
ALGORITHM_CONTINUOUS_SPAN_MATCH = "CONTINUOUS_SPAN_MATCH"
ALGORITHM_MULTI_VIEW_MATCH = "MULTI_VIEW_MATCH"

MATCHING_STATE_NOT_MATCHED = "NOT_MATCHED"
MATCHING_STATE_CANDIDATES_READY = "CANDIDATES_READY"

SCORE_DIRECT_BEAM_MARK = 1.00
SCORE_MULTI_VIEW = 0.99
SCORE_CONTINUOUS_MULTI_SPAN = 0.98


def format_candidate_id(detail_identity_id: str, beam_mark: str) -> str:
    suffix = detail_identity_id.split("::", 1)[1] if "::" in detail_identity_id else detail_identity_id
    return f"{PREFIX_CANDIDATE}::{suffix}::{beam_mark.upper()}"


@dataclass
class BeamMatchCandidate:
    """A possible beam association for a detail identity (not a final match)."""

    candidate_id: str
    detail_identity_id: str
    beam_context_id: str
    beam_mark: str
    drawing_set_id: str
    floor_id: str
    project_id: str
    confidence: float
    score: float
    matching_algorithm: str
    matching_reason: str
    status: str = CANDIDATE_STATUS_GENERATED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "detail_identity_id": self.detail_identity_id,
            "beam_context_id": self.beam_context_id,
            "beam_mark": self.beam_mark,
            "drawing_set_id": self.drawing_set_id,
            "floor_id": self.floor_id,
            "project_id": self.project_id,
            "confidence": self.confidence,
            "score": self.score,
            "matching_algorithm": self.matching_algorithm,
            "matching_reason": self.matching_reason,
            "status": self.status,
            "metadata": dict(self.metadata),
        }
