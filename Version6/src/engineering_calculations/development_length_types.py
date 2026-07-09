"""Development length determination types — Phase I.3."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_DEV_LENGTH = "DEV_LENGTH"
PREFIX_DEV_LENGTH_REGISTRY = "DEV_LENGTH_REGISTRY"
NAMESPACE_DEV_LENGTH = "DEV_LENGTH"

CREATED_PHASE = "I.3"
ENGINE_NAME = "DEVELOPMENT_LENGTH_ENGINE"
SOURCE_ENGINE_VERSION = "I.3"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"

CALCULATION_TYPE = "DEVELOPMENT_LENGTH"


class DevelopmentLengthState(str, Enum):
    """Determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


VALID_DEV_LENGTH_STATES: FrozenSet[str] = frozenset(item.value for item in DevelopmentLengthState)

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "determination_count",
    "determination_ids",
    "results_by_state",
    "state_counts",
    "results_by_beam",
    "results_by_steel_grade",
    "results_by_concrete_grade",
    "results_by_table",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})
