"""Beam Match — authoritative committed reinforcement-to-beam relationship."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.reinforcement.match_decision_quality import DecisionQualityStatus

PREFIX_BEAM_MATCH = "BEAM_MATCH"

MATCH_STATUS_MATCHED = "MATCHED"
MATCH_SOURCE_ENGINEERING_DECISION = "ENGINEERING_DECISION"
ENGINEERING_STATUS_MATCHED = "MATCHED"

EXECUTION_STATUS_NOT_EXECUTED = "NOT_EXECUTED"
EXECUTION_STATUS_EXECUTED = "EXECUTED"

MATCHING_PROGRESS_COMPLETE = "MATCH_COMPLETE"
REINFORCEMENT_MATCHING_STATUS_MATCHED = "MATCHED"


def format_beam_match_id(detail_identity_id: str) -> str:
    suffix = detail_identity_id.split("::", 1)[1] if "::" in detail_identity_id else detail_identity_id
    return f"{PREFIX_BEAM_MATCH}::{suffix}"


def beam_matching_applied(model: dict[str, Any]) -> bool:
    """True when Phase G.3 beam matching has been committed on the model."""
    if model.get("beam_matches"):
        return True
    return bool(model.get("workspace_manager", {}).get("beam_matching_complete"))


def decision_eligible_for_match(decision: dict[str, Any]) -> bool:
    """Return True when a decision may be committed to a BeamMatch."""
    from src.reinforcement.match_decision import DECISION_STATUS_PENDING_VALIDATION

    if decision.get("decision_status") != DECISION_STATUS_PENDING_VALIDATION:
        return False
    if not decision.get("recommended_candidate_id"):
        return False
    quality = decision.get("decision_quality", {})
    return quality.get("quality_status") == DecisionQualityStatus.ENGINEERING_READY.value


def build_matching_summary(beam_matches: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "match_count": len(beam_matches),
        "matched_beam_count": len(beam_matches),
        "matching_progress": MATCHING_PROGRESS_COMPLETE if beam_matches else "NOT_STARTED",
        "match_status": MATCH_STATUS_MATCHED if beam_matches else "NOT_MATCHED",
    }


@dataclass
class BeamMatch:
    """Committed engineering relationship between a detail identity and a beam context."""

    beam_match_id: str
    detail_identity_id: str
    detail_context_id: str
    match_decision_id: str
    beam_context_id: str
    beam_mark: str
    drawing_set_id: str
    project_id: str
    floor_id: str
    match_status: str = MATCH_STATUS_MATCHED
    match_source: str = MATCH_SOURCE_ENGINEERING_DECISION
    confidence: float = 0.0
    confidence_level: str = ""
    algorithm_version: str = ""
    engineering_status: str = ENGINEERING_STATUS_MATCHED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "beam_match_id": self.beam_match_id,
            "detail_identity_id": self.detail_identity_id,
            "detail_context_id": self.detail_context_id,
            "match_decision_id": self.match_decision_id,
            "beam_context_id": self.beam_context_id,
            "beam_mark": self.beam_mark,
            "drawing_set_id": self.drawing_set_id,
            "project_id": self.project_id,
            "floor_id": self.floor_id,
            "match_status": self.match_status,
            "match_source": self.match_source,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "algorithm_version": self.algorithm_version,
            "engineering_status": self.engineering_status,
            "metadata": dict(self.metadata),
        }
