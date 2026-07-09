"""Bar identity determination types — Phase I.8."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_BAR_IDENTITY = "BAR_IDENTITY"
PREFIX_BAR_IDENTITY_REGISTRY = "BAR_IDENTITY_REGISTRY"
PREFIX_ENGINEERING_BAR = "BAR"
PREFIX_ENGINEERING_GROUP = "GROUP"
NAMESPACE_BAR_IDENTITY = "BAR_IDENTITY"

CREATED_PHASE = "I.8"
ENGINE_NAME = "BAR_IDENTITY_ENGINE"
SOURCE_ENGINE_VERSION = "I.8"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"
RESULT_STATUS_DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"

CALCULATION_TYPE = "BAR_IDENTITY"
RULE_SOURCE_GENERAL_NOTES = "GENERAL_NOTES"
DETERMINATION_METHOD = "CLASSIFIER"
GROUPING_STRATEGY_ENGINEERING_EQUIVALENCE = "ENGINEERING_EQUIVALENCE"

BAR_MARK_PREFIX = "BM"


class BarIdentityState(str, Enum):
    """Determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


VALID_BAR_IDENTITY_STATES: FrozenSet[str] = frozenset(item.value for item in BarIdentityState)

EQUIVALENCE_ATTRIBUTE_KEYS: FrozenSet[str] = frozenset({
    "beam_id",
    "reinforcement_role",
    "bar_type",
    "bar_diameter_mm",
    "shape_code",
    "cut_length_mm",
    "hook_length_mm",
    "development_length_mm",
    "lap_length_mm",
    "geometry_signature",
    "support_configuration",
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
    "results_by_role",
    "results_by_diameter",
    "results_by_shape_code",
    "results_by_group",
    "results_by_rule_source",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


def format_engineering_bar_id(sequence: int) -> str:
    return f"{PREFIX_ENGINEERING_BAR}::{sequence:06d}"


def format_engineering_group_id(sequence: int) -> str:
    return f"{PREFIX_ENGINEERING_GROUP}::{sequence:06d}"


def format_bar_mark(sequence: int) -> str:
    return f"{BAR_MARK_PREFIX}{sequence:03d}"


def format_bar_identity_record_id(sequence: int) -> str:
    return f"{PREFIX_BAR_IDENTITY}::{sequence:06d}"


def format_bar_identity_registry_id() -> str:
    return PREFIX_BAR_IDENTITY_REGISTRY
