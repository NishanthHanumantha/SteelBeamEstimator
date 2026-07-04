"""Shape code determination types — Phase I.7."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_SHAPE_CODE = "SHAPE_CODE"
PREFIX_SHAPE_CODE_REGISTRY = "SHAPE_CODE_REGISTRY"
NAMESPACE_SHAPE_CODE = "SHAPE_CODE"

CREATED_PHASE = "I.7"
ENGINE_NAME = "SHAPE_CODE_ENGINE"
SOURCE_ENGINE_VERSION = "I.7"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"
RESULT_STATUS_DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"

CALCULATION_TYPE = "SHAPE_CODE"
RULE_SOURCE_GENERAL_NOTES = "GENERAL_NOTES"
DETERMINATION_METHOD = "CLASSIFIER"

INTERNAL_CODE_STRAIGHT = "SC_STRAIGHT"
INTERNAL_CODE_L = "SC_L"
INTERNAL_CODE_U = "SC_U"
INTERNAL_CODE_LINK = "SC_LINK"
INTERNAL_CODE_STIRRUP = "SC_STIRRUP"
INTERNAL_CODE_OPEN_STIRRUP = "SC_OPEN_STIRRUP"
INTERNAL_CODE_CRANK = "SC_CRANK"
INTERNAL_CODE_SIDE = "SC_SIDE"

FAMILY_STRAIGHT = "STRAIGHT"
FAMILY_L_BAR = "L_BAR"
FAMILY_U_BAR = "U_BAR"
FAMILY_LINK = "LINK"
FAMILY_CLOSED_STIRRUP = "CLOSED_STIRRUP"
FAMILY_OPEN_STIRRUP = "OPEN_STIRRUP"
FAMILY_CRANKED_BAR = "CRANKED_BAR"
FAMILY_SIDE_BAR = "SIDE_BAR"

TRANSVERSE_ROLES: FrozenSet[str] = frozenset({
    "STIRRUP",
    "LINK_BAR",
    "SPACER",
})

MAIN_BAR_ROLES: FrozenSet[str] = frozenset({
    "TOP_MAIN",
    "BOTTOM_MAIN",
    "EXTRA_TOP",
    "EXTRA_BOTTOM",
    "STARTER",
})

SIDE_BAR_ROLES: FrozenSet[str] = frozenset({
    "SIDE_BAR",
})


class ShapeCodeState(str, Enum):
    """Determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


VALID_SHAPE_CODE_STATES: FrozenSet[str] = frozenset(item.value for item in ShapeCodeState)

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "determination_count",
    "determination_ids",
    "results_by_state",
    "state_counts",
    "results_by_beam",
    "results_by_diameter",
    "results_by_role",
    "results_by_shape_code",
    "results_by_shape_family",
    "results_by_rule_source",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})
