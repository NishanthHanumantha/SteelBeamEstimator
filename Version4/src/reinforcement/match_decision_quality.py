"""Match decision quality metadata — confidence levels and algorithm versioning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

ALGORITHM_VERSION = "1.0"
IMPLEMENTATION_PHASE = "G.2.7"
ALGORITHM_FAMILY_LABEL_MATCHING = "LABEL_MATCHING"

SHARED_ALGORITHM_ID = "MATCH_ALGORITHM::DIRECT_LABEL_MATCH::1.0"
SHARED_ALGORITHM_NAME = "DIRECT_LABEL_MATCH"

PREFIX_DECISION_QUALITY = "DECISION_QUALITY"


class DecisionConfidenceLevel(str, Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class DecisionQualityStatus(str, Enum):
    ENGINEERING_READY = "ENGINEERING_READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNKNOWN = "UNKNOWN"


def format_decision_quality_id(decision_id: str) -> str:
    suffix = decision_id.split("::", 1)[1] if "::" in decision_id else decision_id
    return f"{PREFIX_DECISION_QUALITY}::{suffix}"


def confidence_level_from_value(confidence: Optional[float]) -> str:
    if confidence is None:
        return DecisionConfidenceLevel.UNKNOWN.value
    value = float(confidence)
    if value >= 0.98:
        return DecisionConfidenceLevel.VERY_HIGH.value
    if value >= 0.95:
        return DecisionConfidenceLevel.HIGH.value
    if value >= 0.85:
        return DecisionConfidenceLevel.MEDIUM.value
    return DecisionConfidenceLevel.LOW.value


def quality_status_from_level(level: str) -> str:
    if level in (DecisionConfidenceLevel.VERY_HIGH.value, DecisionConfidenceLevel.HIGH.value):
        return DecisionQualityStatus.ENGINEERING_READY.value
    if level == DecisionConfidenceLevel.MEDIUM.value:
        return DecisionQualityStatus.NEEDS_REVIEW.value
    if level == DecisionConfidenceLevel.LOW.value:
        return DecisionQualityStatus.LOW_CONFIDENCE.value
    return DecisionQualityStatus.UNKNOWN.value


def build_quality_summary(decisions: list[dict[str, Any]]) -> dict[str, int]:
    summary = {level.value: 0 for level in DecisionConfidenceLevel}
    for decision in decisions:
        level = str(decision.get("confidence_level", DecisionConfidenceLevel.UNKNOWN.value))
        if level in summary:
            summary[level] += 1
        else:
            summary[DecisionConfidenceLevel.UNKNOWN.value] += 1
    return summary


@dataclass
class DecisionAlgorithmInfo:
    """Versioned algorithm metadata for auditability."""

    algorithm_name: str
    algorithm_version: str = ALGORITHM_VERSION
    algorithm_family: str = ALGORITHM_FAMILY_LABEL_MATCHING
    implementation_phase: str = IMPLEMENTATION_PHASE
    decision_timestamp: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm_name": self.algorithm_name,
            "algorithm_version": self.algorithm_version,
            "algorithm_family": self.algorithm_family,
            "implementation_phase": self.implementation_phase,
            "decision_timestamp": self.decision_timestamp,
        }


def shared_algorithm_node() -> dict[str, Any]:
    return {
        "id": SHARED_ALGORITHM_ID,
        "name": SHARED_ALGORITHM_NAME,
        "version": ALGORITHM_VERSION,
        "family": ALGORITHM_FAMILY_LABEL_MATCHING,
    }
