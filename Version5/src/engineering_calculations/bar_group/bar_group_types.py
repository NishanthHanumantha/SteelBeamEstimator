"""Engineering bar group types — Phase I.9."""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, FrozenSet, Mapping

PREFIX_BAR_GROUP = "BAR_GROUP"
PREFIX_BAR_GROUP_REGISTRY = "BAR_GROUP_REGISTRY"
PREFIX_ENGINEERING_GROUP = "GROUP"
PREFIX_ENGINEERING_SIGNATURE = "SIG"
NAMESPACE_BAR_GROUP = "BAR_GROUP"

CREATED_PHASE = "I.9"
ENGINE_NAME = "BAR_GROUP_ENGINE"
SOURCE_ENGINE_VERSION = "I.9"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"
RESULT_STATUS_DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"

CALCULATION_TYPE = "BAR_GROUP"
RULE_SOURCE_GENERAL_NOTES = "GENERAL_NOTES"
DETERMINATION_METHOD = "CLASSIFIER"
GROUPING_STRATEGY_ENGINEERING_SIGNATURE = "ENGINEERING_SIGNATURE"

SIGNATURE_ATTRIBUTE_KEYS: tuple[str, ...] = (
    "reinforcement_role",
    "bar_diameter_mm",
    "shape_code",
    "cut_length_mm",
    "hook_length_mm",
    "development_length_mm",
    "lap_length_mm",
    "geometry_signature",
    "support_configuration",
)


class BarGroupState(str, Enum):
    """Determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


VALID_BAR_GROUP_STATES: FrozenSet[str] = frozenset(item.value for item in BarGroupState)

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
    "results_by_signature",
    "results_by_rule_source",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


def format_bar_group_record_id(sequence: int) -> str:
    return f"{PREFIX_BAR_GROUP}::{sequence:06d}"


def format_bar_group_registry_id() -> str:
    return PREFIX_BAR_GROUP_REGISTRY


def format_engineering_group_id(sequence: int) -> str:
    return f"{PREFIX_ENGINEERING_GROUP}::{sequence:06d}"


def format_engineering_signature(digest: str) -> str:
    return f"{PREFIX_ENGINEERING_SIGNATURE}::{digest}"


def compute_engineering_signature(
    reinforcement_role: str,
    diameter_mm: int,
    shape_code: str,
    cut_length_mm: int,
    hook_length_mm: int,
    development_length_mm: int,
    lap_length_mm: int,
    geometry_signature: str,
    support_configuration: str,
) -> str:
    """Deterministic immutable engineering fingerprint."""
    parts = [
        str(reinforcement_role),
        str(int(diameter_mm)),
        str(shape_code),
        str(int(cut_length_mm)),
        str(int(hook_length_mm)),
        str(int(development_length_mm)),
        str(int(lap_length_mm)),
        str(geometry_signature),
        str(support_configuration),
    ]
    payload = "|".join(parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8].upper()
    return format_engineering_signature(digest)


def compute_engineering_signature_from_inputs(inputs: Mapping[str, Any]) -> str:
    return compute_engineering_signature(
        reinforcement_role=str(inputs.get("reinforcement_role", "")),
        diameter_mm=int(inputs.get("bar_diameter_mm") or inputs.get("diameter_mm") or 0),
        shape_code=str(inputs.get("shape_code", "")),
        cut_length_mm=int(inputs.get("cut_length_mm") or 0),
        hook_length_mm=int(inputs.get("hook_length_mm") or 0),
        development_length_mm=int(inputs.get("development_length_mm") or 0),
        lap_length_mm=int(inputs.get("lap_length_mm") or 0),
        geometry_signature=str(inputs.get("geometry_signature", "")),
        support_configuration=str(inputs.get("support_configuration", "")),
    )
