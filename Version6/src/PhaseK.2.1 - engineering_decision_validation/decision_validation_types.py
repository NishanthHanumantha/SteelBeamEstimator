"""Phase K.2.1 — Engineering Decision Validation types."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ValidationStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    WARNING = "WARNING"
    INVALID = "INVALID"


SCORE_WEIGHTS = {
    "IDENTITY": 20,
    "TRACEABILITY": 20,
    "EXECUTION": 20,
    "ENGINEERING": 20,
    "PRODUCTION_SAFETY": 20,
}

VALID_DECISION_CATEGORIES = frozenset(
    {
        "SUPPLEMENTARY_DEVELOPMENT_LENGTH",
        "SUPPLEMENTARY_ANCHORAGE",
        "SUPPLEMENTARY_HOOK",
        "SUPPLEMENTARY_CONTINUATION",
        "SUPPLEMENTARY_SUPPORT_BAR",
        "SUPPLEMENTARY_TERMINATION",
        "SUPPLEMENTARY_CURTAILMENT",
        "SUPPLEMENTARY_REINFORCEMENT",
        "SUPPORT_REINFORCEMENT",
        "CONTINUOUS_SUPPORT_REINFORCEMENT",
        "UNKNOWN",
    }
)

VALID_LIFECYCLES = frozenset({"RESOLVED"})
VALID_ELIGIBILITY = frozenset({"ELIGIBLE", "HOLD"})

PRODUCTION_TARGETS = (
    "calculation",
    "cut_length",
    "steel",
    "bbs",
    "beam_schedule",
    "excel",
)

RULE_CATALOG = (
    {"group": "IDENTITY", "rule": "Decision ID exists"},
    {"group": "IDENTITY", "rule": "Decision Key exists"},
    {"group": "IDENTITY", "rule": "Engineering Object exists"},
    {"group": "IDENTITY", "rule": "Intent exists"},
    {"group": "IDENTITY", "rule": "Beam exists"},
    {"group": "IDENTITY", "rule": "Calculation Context exists"},
    {"group": "IDENTITY", "rule": "Specification exists"},
    {"group": "TRACEABILITY", "rule": "Engineering Object reference valid"},
    {"group": "TRACEABILITY", "rule": "Intent reference valid"},
    {"group": "TRACEABILITY", "rule": "Decision reference valid"},
    {"group": "TRACEABILITY", "rule": "Recovery reference valid"},
    {"group": "TRACEABILITY", "rule": "Beam reference valid"},
    {"group": "TRACEABILITY", "rule": "Calculation Context valid"},
    {"group": "TRACEABILITY", "rule": "Graph references valid"},
    {"group": "EXECUTION", "rule": "Decision executable"},
    {"group": "EXECUTION", "rule": "Execution registry exists"},
    {"group": "EXECUTION", "rule": "Execution target exists"},
    {"group": "EXECUTION", "rule": "Calculation target exists"},
    {"group": "EXECUTION", "rule": "Steel target exists"},
    {"group": "EXECUTION", "rule": "BBS target exists"},
    {"group": "EXECUTION", "rule": "Excel target exists"},
    {"group": "EXECUTION", "rule": "Lifecycle READY"},
    {"group": "EXECUTION", "rule": "Execution configuration compatible"},
    {"group": "ENGINEERING", "rule": "Primary intent exists"},
    {"group": "ENGINEERING", "rule": "Primary intent active"},
    {"group": "ENGINEERING", "rule": "Supporting intents valid"},
    {"group": "ENGINEERING", "rule": "Suppressed intents not active"},
    {"group": "ENGINEERING", "rule": "Decision category valid"},
    {"group": "ENGINEERING", "rule": "Engineering rule exists"},
    {"group": "ENGINEERING", "rule": "Specification compatible"},
    {"group": "ENGINEERING", "rule": "Calculation context compatible"},
    {"group": "PRODUCTION_SAFETY", "rule": "Exactly one execution path"},
    {"group": "PRODUCTION_SAFETY", "rule": "No duplicate execution targets"},
    {"group": "PRODUCTION_SAFETY", "rule": "No duplicate calculation targets"},
    {"group": "PRODUCTION_SAFETY", "rule": "No circular references"},
    {"group": "PRODUCTION_SAFETY", "rule": "No recursive execution"},
    {"group": "PRODUCTION_SAFETY", "rule": "No orphan execution"},
    {"group": "PRODUCTION_SAFETY", "rule": "Execution registry unique"},
    {"group": "VERSION", "rule": "Decision MODEL_VERSION valid"},
    {"group": "VERSION", "rule": "Execution MODEL_VERSION compatible"},
    {"group": "VERSION", "rule": "Validation MODEL_VERSION compatible"},
    {"group": "VERSION", "rule": "Configuration version compatible"},
)


def empty_validation(
    *,
    validation_id: str,
    decision_id: str,
    decision_key: str,
) -> dict[str, Any]:
    return {
        "validation_id": validation_id,
        "decision_id": decision_id,
        "decision_key": decision_key,
        "validation_status": ValidationStatus.UNKNOWN.value,
        "validation_score": 0,
        "execution_allowed": False,
        "validation_errors": [],
        "validation_warnings": [],
        "validated_rules": [],
        "validation_timestamp": "",
        "validation_version": "6.2.0",
        "traceability": {},
        "lifecycle": "VALIDATED",
        "score_breakdown": {},
    }
