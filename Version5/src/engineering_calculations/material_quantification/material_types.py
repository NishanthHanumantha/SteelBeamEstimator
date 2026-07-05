"""Material quantification types — Phase I.14."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_MATERIAL = "MATERIAL"
PREFIX_MATERIAL_REGISTRY = "MATERIAL_REGISTRY"
NAMESPACE_MATERIAL = "MATERIAL"

CREATED_PHASE = "I.14"
ENGINE_NAME = "MATERIAL_QUANTIFICATION_ENGINE"
SOURCE_ENGINE_VERSION = "I.14"
DETERMINATION_METHOD = "AGGREGATION"
DEFAULT_STEEL_GRADE = "Fe550D"
UNIT_KG = "kg"

MATERIAL_TYPE_REINFORCEMENT_STEEL = "REINFORCEMENT_STEEL"
FUTURE_MATERIAL_TYPES: FrozenSet[str] = frozenset({
    "BINDING_WIRE",
    "SPACER_BAR",
    "CHAIR_BAR",
    "COUPLER",
    "ANCHOR",
})


class MaterialState(str, Enum):
    """Material quantification lifecycle state."""

    READY = "READY"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"


VALID_MATERIAL_STATES: FrozenSet[str] = frozenset(item.value for item in MaterialState)

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "determination_count",
    "determination_ids",
    "results_by_state",
    "state_counts",
    "results_by_material_type",
    "results_by_steel_grade",
    "results_by_diameter",
    "results_by_material_state",
    "results_by_engineering_ready",
    "results_by_quality_ready",
    "results_by_beam",
    "results_by_beam_mark",
    "results_by_fabrication_mark",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


def format_material_id(sequence: int) -> str:
    return f"{PREFIX_MATERIAL}::{sequence:06d}"


def format_material_registry_id() -> str:
    return PREFIX_MATERIAL_REGISTRY


def material_group_sort_key(
    key: tuple[str | None, str | None, int | None],
) -> tuple[str, str, int]:
    """Deterministic ordering for material grouping keys."""
    material_type, steel_grade, diameter_mm = key
    return (
        str(material_type or ""),
        str(steel_grade or ""),
        diameter_mm if diameter_mm is not None else -1,
    )
