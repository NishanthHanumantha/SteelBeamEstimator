"""Documented deterministic engineering intent rules."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional


class EngineeringIntentType(str, Enum):
    SUPPLEMENTARY_DEVELOPMENT_LENGTH = "SUPPLEMENTARY_DEVELOPMENT_LENGTH"
    SUPPLEMENTARY_ANCHORAGE = "SUPPLEMENTARY_ANCHORAGE"
    SUPPLEMENTARY_CONTINUATION = "SUPPLEMENTARY_CONTINUATION"
    SUPPLEMENTARY_CURTAILMENT = "SUPPLEMENTARY_CURTAILMENT"
    SUPPLEMENTARY_SUPPORT_BAR = "SUPPLEMENTARY_SUPPORT_BAR"
    SUPPLEMENTARY_HOOK = "SUPPLEMENTARY_HOOK"
    SUPPLEMENTARY_REINFORCEMENT = "SUPPLEMENTARY_REINFORCEMENT"
    SUPPLEMENTARY_TERMINATION = "SUPPLEMENTARY_TERMINATION"
    UNKNOWN = "UNKNOWN"


TENSION_ROLES = frozenset({"TOP_MAIN", "BOTTOM_MAIN", "EXTRA_TOP", "EXTRA_BOTTOM"})
MAIN_BAR_TYPES = frozenset({"MAIN_BAR"})


INTENT_RULES: List[dict[str, Any]] = [
    {
        "rule_id": "K.1.RULE.DEV_LENGTH.001",
        "intent_type": EngineeringIntentType.SUPPLEMENTARY_DEVELOPMENT_LENGTH.value,
        "description": (
            "Existing tension main bar at beam support requires development length continuation "
            "per General Notes development length table."
        ),
        "preconditions": [
            "engineering_object_exists",
            "specification_exists",
            "beam_exists",
            "geometry_exists",
            "support_exists",
            "development_length_available",
            "calculation_context_complete",
            "general_note_development_length_rule",
        ],
        "general_note_refs": [
            "RULE::PROJECT#structural_detailing_rules.anchorage_rules",
            "KNOWLEDGE::GENERAL_NOTES#development_tables",
        ],
        "engineering_standard": "IS 456 Development Length",
    },
    {
        "rule_id": "K.1.RULE.ANCHORAGE.001",
        "intent_type": EngineeringIntentType.SUPPLEMENTARY_ANCHORAGE.value,
        "description": (
            "Existing tension main bar at support requires anchorage continuation "
            "per General Notes anchorage rules."
        ),
        "preconditions": [
            "engineering_object_exists",
            "specification_exists",
            "beam_exists",
            "geometry_exists",
            "support_exists",
            "anchorage_rule_exists",
            "development_length_available",
            "calculation_context_complete",
            "general_note_anchorage_rule",
        ],
        "general_note_refs": ["RULE::PROJECT#structural_detailing_rules.anchorage_rules"],
        "engineering_standard": "IS 456 Anchorage",
    },
    {
        "rule_id": "K.1.RULE.HOOK.001",
        "intent_type": EngineeringIntentType.SUPPLEMENTARY_HOOK.value,
        "description": (
            "Existing tension main bar at support requires standard hook continuation "
            "where General Notes mandate hooks for tension reinforcement."
        ),
        "preconditions": [
            "engineering_object_exists",
            "specification_exists",
            "beam_exists",
            "geometry_exists",
            "support_exists",
            "hook_rule_exists",
            "calculation_context_complete",
            "general_note_hook_rule",
        ],
        "general_note_refs": ["RULE::PROJECT#structural_detailing_rules.hook_rules"],
        "engineering_standard": "IS 456 Standard Hooks",
    },
    {
        "rule_id": "K.1.RULE.CONTINUITY.001",
        "intent_type": EngineeringIntentType.SUPPLEMENTARY_CONTINUATION.value,
        "description": (
            "Continuous beam with shared support requires reinforcement continuation "
            "per structural continuity and General Notes."
        ),
        "preconditions": [
            "engineering_object_exists",
            "specification_exists",
            "beam_exists",
            "geometry_exists",
            "support_exists",
            "continuity_relationship_exists",
            "calculation_context_complete",
            "general_note_continuation_rule",
        ],
        "general_note_refs": ["KNOWLEDGE::GENERAL_NOTES"],
        "engineering_standard": "Structural Continuity",
    },
    {
        "rule_id": "K.1.RULE.CURTAILMENT.001",
        "intent_type": EngineeringIntentType.SUPPLEMENTARY_CURTAILMENT.value,
        "description": (
            "Main bar in span zone requires curtailment/splice continuation "
            "where lap splice rules apply per General Notes."
        ),
        "preconditions": [
            "engineering_object_exists",
            "specification_exists",
            "beam_exists",
            "geometry_exists",
            "lap_rule_exists",
            "calculation_context_complete",
            "general_note_lap_rule",
        ],
        "general_note_refs": ["RULE::PROJECT#structural_detailing_rules.lap_rules"],
        "engineering_standard": "IS 456 Lap Splice",
    },
    {
        "rule_id": "K.1.RULE.SUPPORT_BAR.001",
        "intent_type": EngineeringIntentType.SUPPLEMENTARY_SUPPORT_BAR.value,
        "description": (
            "Support zone requires supplementary support reinforcement "
            "implied by beam support geometry and detailing rules."
        ),
        "preconditions": [
            "engineering_object_exists",
            "specification_exists",
            "beam_exists",
            "geometry_exists",
            "support_exists",
            "calculation_context_complete",
        ],
        "general_note_refs": ["KNOWLEDGE::GENERAL_NOTES"],
        "engineering_standard": "Support Detailing",
    },
    {
        "rule_id": "K.1.RULE.TERMINATION.001",
        "intent_type": EngineeringIntentType.SUPPLEMENTARY_TERMINATION.value,
        "description": (
            "Bar termination at support requires explicit termination reinforcement "
            "per anchorage and development length rules."
        ),
        "preconditions": [
            "engineering_object_exists",
            "specification_exists",
            "beam_exists",
            "geometry_exists",
            "support_exists",
            "development_length_available",
            "calculation_context_complete",
        ],
        "general_note_refs": ["RULE::PROJECT#structural_detailing_rules.anchorage_rules"],
        "engineering_standard": "Bar Termination",
    },
]


def rule_by_id(rule_id: str) -> Optional[dict[str, Any]]:
    for rule in INTENT_RULES:
        if rule.get("rule_id") == rule_id:
            return rule
    return None


def rules_for_intent(intent_type: str) -> List[dict[str, Any]]:
    return [rule for rule in INTENT_RULES if rule.get("intent_type") == intent_type]


def extract_general_note_rules(engineering_rules: dict[str, Any]) -> dict[str, List[dict[str, Any]]]:
    detailing = (engineering_rules.get("structural_detailing_rules") or {})
    return {
        "anchorage_rules": detailing.get("anchorage_rules") or [],
        "hook_rules": detailing.get("hook_rules") or [],
        "lap_rules": detailing.get("lap_rules") or [],
        "bend_rules": detailing.get("bend_rules") or [],
        "development_tables": engineering_rules.get("development_tables") or [],
    }


def lookup_development_length(
    table: dict[str, Any],
    steel_grade: str,
    concrete_grade: str,
    diameter_mm: float,
) -> Optional[dict[str, Any]]:
    diameter_key = str(int(diameter_mm)) if float(diameter_mm).is_integer() else str(diameter_mm)
    grade_candidates = []
    for candidate in (steel_grade, steel_grade.replace("D", ""), "Fe550", "Fe500", "Fe415"):
        if candidate and candidate not in grade_candidates:
            grade_candidates.append(candidate)

    for steel_key in grade_candidates:
        steel_table = table.get(steel_key)
        if not isinstance(steel_table, dict):
            continue
        concrete_table = steel_table.get(concrete_grade)
        if not isinstance(concrete_table, dict):
            continue
        entry = concrete_table.get(diameter_key)
        if isinstance(entry, dict) and entry.get("value") is not None:
            return entry

    for physical_key, steel_table in table.items():
        if not isinstance(steel_table, dict):
            continue
        concrete_table = steel_table.get(concrete_grade)
        if not isinstance(concrete_table, dict):
            continue
        entry = concrete_table.get(diameter_key)
        if isinstance(entry, dict) and entry.get("value") is not None:
            result = dict(entry)
            result["physical_table_key"] = physical_key
            return result
    return None
