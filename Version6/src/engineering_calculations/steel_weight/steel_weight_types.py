"""Steel weight calculation types — Phase I.11."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_WEIGHT = "WEIGHT"
PREFIX_WEIGHT_REGISTRY = "WEIGHT_REGISTRY"
NAMESPACE_WEIGHT = "WEIGHT"

CREATED_PHASE = "I.11"
ENGINE_NAME = "STEEL_WEIGHT_ENGINE"
SOURCE_ENGINE_VERSION = "I.11"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"
RESULT_STATUS_DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"

CALCULATION_TYPE = "STEEL_WEIGHT"
DETERMINATION_METHOD = "CALCULATOR"
STEEL_DENSITY_KG_M3 = 7850
FORMULA_VERSION = "1.0"
FORMULA_NAME = "engineering_weight_d2_over_162"
CONVERSION_FACTOR = 162
ENGINEERING_PRECISION = 6
EXPORT_PRECISION = 3
UNIT_KG = "kg"


class SteelWeightState(str, Enum):
    """Steel weight determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


VALID_STEEL_WEIGHT_STATES: FrozenSet[str] = frozenset(item.value for item in SteelWeightState)

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
    "results_by_fabrication_state",
    "results_by_fabrication_mark",
    "results_by_engineering_group",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


def format_weight_record_id(sequence: int) -> str:
    return f"{PREFIX_WEIGHT}::{sequence:06d}"


def format_weight_registry_id() -> str:
    return PREFIX_WEIGHT_REGISTRY
