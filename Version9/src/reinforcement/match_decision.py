"""Match Decision — formal engineering judgement before committed beam matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

PREFIX_MATCH_DECISION = "MATCH_DECISION"

ENGINEERING_STATUS_PRE_MATCH = "PRE_MATCH"

EXECUTION_STATUS_NOT_EXECUTED = "NOT_EXECUTED"
EXECUTION_STATUS_EXECUTED = "EXECUTED"

DECISION_STATUS_PENDING_VALIDATION = "PENDING_VALIDATION"
DECISION_STATUS_VALIDATED = "VALIDATED"
DECISION_STATUS_REJECTED = "REJECTED"
DECISION_STATUS_MANUAL_REVIEW = "MANUAL_REVIEW"

REASON_DIRECT_LABEL_MATCH = "DIRECT_LABEL_MATCH"
REASON_MULTI_VIEW_MATCH = "MULTI_VIEW_MATCH"
REASON_CONTINUOUS_MULTI_SPAN = "CONTINUOUS_MULTI_SPAN"
REASON_DRAWING_SET_MATCH = "DRAWING_SET_MATCH"
REASON_LOW_CONFIDENCE = "LOW_CONFIDENCE"
REASON_NO_MATCH = "NO_MATCH"
REASON_MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

ALLOWED_DECISION_REASONS = frozenset(
    {
        REASON_DIRECT_LABEL_MATCH,
        REASON_MULTI_VIEW_MATCH,
        REASON_CONTINUOUS_MULTI_SPAN,
        REASON_DRAWING_SET_MATCH,
        REASON_LOW_CONFIDENCE,
        REASON_NO_MATCH,
        REASON_MANUAL_OVERRIDE,
    }
)

ALLOWED_DECISION_STATUSES = frozenset(
    {
        DECISION_STATUS_PENDING_VALIDATION,
        DECISION_STATUS_VALIDATED,
        DECISION_STATUS_REJECTED,
        DECISION_STATUS_MANUAL_REVIEW,
    }
)

MANUAL_REVIEW_CONFIDENCE_THRESHOLD = 0.95

CANDIDATE_REASON_TO_DECISION = {
    "DIRECT_BEAM_MARK": REASON_DIRECT_LABEL_MATCH,
    "MULTI_VIEW_SINGLE_BEAM": REASON_MULTI_VIEW_MATCH,
    "CONTINUOUS_MULTI_SPAN": REASON_CONTINUOUS_MULTI_SPAN,
    "DRAWING_SET_MATCH": REASON_DRAWING_SET_MATCH,
}


def format_match_decision_id(detail_identity_id: str) -> str:
    suffix = detail_identity_id.split("::", 1)[1] if "::" in detail_identity_id else detail_identity_id
    return f"{PREFIX_MATCH_DECISION}::{suffix}"


def requires_manual_review(confidence: float) -> bool:
    return float(confidence) < MANUAL_REVIEW_CONFIDENCE_THRESHOLD


@dataclass
class MatchDecision:
    """Engineering decision recommending a candidate without committing a beam match."""

    decision_id: str
    detail_identity_id: str
    drawing_set_id: str
    floor_id: str
    candidate_count: int
    candidate_ids: List[str] = field(default_factory=list)
    recommended_candidate_id: Optional[str] = None
    recommended_beam_context_id: Optional[str] = None
    decision_status: str = DECISION_STATUS_PENDING_VALIDATION
    decision_reason: str = REASON_NO_MATCH
    requires_manual_review: bool = False
    confidence: float = 0.0
    engineering_status: str = ENGINEERING_STATUS_PRE_MATCH
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "detail_identity_id": self.detail_identity_id,
            "drawing_set_id": self.drawing_set_id,
            "floor_id": self.floor_id,
            "candidate_count": self.candidate_count,
            "candidate_ids": list(self.candidate_ids),
            "recommended_candidate_id": self.recommended_candidate_id,
            "recommended_beam_context_id": self.recommended_beam_context_id,
            "decision_status": self.decision_status,
            "decision_reason": self.decision_reason,
            "requires_manual_review": self.requires_manual_review,
            "confidence": self.confidence,
            "engineering_status": self.engineering_status,
            "metadata": dict(self.metadata),
        }
