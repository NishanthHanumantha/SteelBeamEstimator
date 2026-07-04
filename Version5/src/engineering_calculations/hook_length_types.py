"""Hook length determination types — Phase I.4."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_HOOK_LENGTH = "HOOK_LENGTH"
PREFIX_HOOK_LENGTH_REGISTRY = "HOOK_LENGTH_REGISTRY"
NAMESPACE_HOOK_LENGTH = "HOOK_LENGTH"

CREATED_PHASE = "I.4"
ENGINE_NAME = "HOOK_LENGTH_ENGINE"
SOURCE_ENGINE_VERSION = "I.4"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"

CALCULATION_TYPE = "HOOK"
RULE_SOURCE_GENERAL_NOTES = "GENERAL_NOTES"
DETERMINATION_METHOD = "RULE_LOOKUP"


class HookLengthState(str, Enum):
    """Determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


VALID_HOOK_LENGTH_STATES: FrozenSet[str] = frozenset(item.value for item in HookLengthState)

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "determination_count",
    "determination_ids",
    "results_by_state",
    "state_counts",
    "results_by_beam",
    "results_by_hook_angle",
    "results_by_hook_type",
    "results_by_rule_source",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})
