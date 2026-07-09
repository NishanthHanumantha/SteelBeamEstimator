"""Cut length determination types — Phase I.6."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_CUT_LENGTH = "CUT_LENGTH"
PREFIX_CUT_LENGTH_REGISTRY = "CUT_LENGTH_REGISTRY"
NAMESPACE_CUT_LENGTH = "CUT_LENGTH"

CREATED_PHASE = "I.6"
ENGINE_NAME = "CUT_LENGTH_ENGINE"
SOURCE_ENGINE_VERSION = "I.6"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"
RESULT_STATUS_DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"

CALCULATION_TYPE = "CUT_LENGTH"
RULE_SOURCE_GENERAL_NOTES = "GENERAL_NOTES"
RULE_SOURCE_STRUCTURAL_CODE = "STRUCTURAL_CODE"
DETERMINATION_METHOD = "FORMULA_ENGINE"

SPAN_BASIS_CLEAR_SPAN = "CLEAR_SPAN"
SPAN_BASIS_SECTION_PERIMETER = "SECTION_PERIMETER"

TENSION_POSITION = "TENSION"
COMPRESSION_POSITION = "COMPRESSION"


class CutLengthState(str, Enum):
    """Determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


VALID_CUT_LENGTH_STATES: FrozenSet[str] = frozenset(item.value for item in CutLengthState)

MAIN_BAR_ROLES: FrozenSet[str] = frozenset({
    "TOP_MAIN",
    "BOTTOM_MAIN",
    "EXTRA_TOP",
    "EXTRA_BOTTOM",
    "SIDE_BAR",
    "STARTER",
})

TRANSVERSE_ROLES: FrozenSet[str] = frozenset({
    "STIRRUP",
    "LINK_BAR",
    "SPACER",
})

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
    "results_by_bar_type",
    "results_by_rule_source",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})
