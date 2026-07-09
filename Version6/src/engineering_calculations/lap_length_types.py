"""Lap length determination types — Phase I.5."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_LAP_LENGTH = "LAP_LENGTH"
PREFIX_LAP_LENGTH_REGISTRY = "LAP_LENGTH_REGISTRY"
NAMESPACE_LAP_LENGTH = "LAP_LENGTH"

CREATED_PHASE = "I.5"
ENGINE_NAME = "LAP_LENGTH_ENGINE"
SOURCE_ENGINE_VERSION = "I.5"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"
RESULT_STATUS_DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"

CALCULATION_TYPE = "LAP_LENGTH"
RULE_SOURCE_GENERAL_NOTES = "GENERAL_NOTES"
RULE_SOURCE_STRUCTURAL_CODE = "STRUCTURAL_CODE"
DETERMINATION_METHOD = "RULE_LOOKUP"

TENSION_POSITION = "TENSION"
COMPRESSION_POSITION = "COMPRESSION"


class LapLengthState(str, Enum):
    """Determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


VALID_LAP_LENGTH_STATES: FrozenSet[str] = frozenset(item.value for item in LapLengthState)

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
    "results_by_steel_grade",
    "results_by_concrete_grade",
    "results_by_lap_factor",
    "results_by_rule_source",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})
