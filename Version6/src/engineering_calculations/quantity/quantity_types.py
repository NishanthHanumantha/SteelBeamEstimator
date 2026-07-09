"""Engineering quantity types — Phase I.13."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_QUANTITY = "QUANTITY"
PREFIX_QUANTITY_REGISTRY = "QUANTITY_REGISTRY"
NAMESPACE_QUANTITY = "QUANTITY"

CREATED_PHASE = "I.13"
ENGINE_NAME = "QUANTITY_ENGINE"
SOURCE_ENGINE_VERSION = "I.13"
DETERMINATION_METHOD = "AGGREGATION"


class QuantityState(str, Enum):
    """Engineering quantity lifecycle state."""

    READY = "READY"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"


VALID_QUANTITY_STATES: FrozenSet[str] = frozenset(item.value for item in QuantityState)

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "determination_count",
    "determination_ids",
    "results_by_state",
    "state_counts",
    "results_by_beam_summary",
    "results_by_beam",
    "results_by_beam_mark",
    "results_by_fabrication_mark",
    "results_by_quantity_state",
    "results_by_engineering_ready",
    "results_by_quality_ready",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


def format_quantity_id(sequence: int) -> str:
    return f"{PREFIX_QUANTITY}::{sequence:06d}"


def format_quantity_registry_id() -> str:
    return PREFIX_QUANTITY_REGISTRY
