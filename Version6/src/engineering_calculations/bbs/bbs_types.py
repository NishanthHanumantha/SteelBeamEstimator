"""Bar bending schedule foundation types — Phase I.10."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_BBS = "BBS"
PREFIX_BBS_REGISTRY = "BBS_REGISTRY"
NAMESPACE_BBS = "BBS"

CREATED_PHASE = "I.10"
ENGINE_NAME = "BBS_ENGINE"
SOURCE_ENGINE_VERSION = "I.10"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED_DEFERRED"
RESULT_STATUS_LOOKUP_FAILED = "LOOKUP_FAILED"
RESULT_STATUS_DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"

CALCULATION_TYPE = "BBS"
RULE_SOURCE_GENERAL_NOTES = "GENERAL_NOTES"
DETERMINATION_METHOD = "CLASSIFIER"
SCHEDULE_ORDER_ENGINEERING_SIGNATURE = "ENGINEERING_SIGNATURE_THEN_GROUP"

FABRICATION_MARK_PREFIX = "BM"


class BbsState(str, Enum):
    """BBS determination lifecycle state."""

    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class FabricationState(str, Enum):
    """Fabrication readiness state."""

    FABRICATION_READY = "FABRICATION_READY"
    FABRICATION_DEFERRED = "FABRICATION_DEFERRED"
    FABRICATION_BLOCKED = "FABRICATION_BLOCKED"


VALID_BBS_STATES: FrozenSet[str] = frozenset(item.value for item in BbsState)
VALID_FABRICATION_STATES: FrozenSet[str] = frozenset(item.value for item in FabricationState)

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
    "results_by_fabrication_state",
    "results_by_fabrication_mark",
    "results_by_rule_source",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


def format_bbs_record_id(sequence: int) -> str:
    return f"{PREFIX_BBS}::{sequence:06d}"


def format_bbs_registry_id() -> str:
    return PREFIX_BBS_REGISTRY


def format_fabrication_mark(sequence: int) -> str:
    return f"{FABRICATION_MARK_PREFIX}{sequence:03d}"


def format_schedule_description(
    member_count: int,
    diameter_mm: int,
    role: str,
    shape_code: str,
) -> str:
    role_upper = str(role or "").upper()
    shape_upper = str(shape_code or "").upper()
    diameter = int(diameter_mm or 0)
    count = max(int(member_count or 0), 1)

    if role_upper == "STIRRUP" or shape_upper == "SC_STIRRUP":
        return f"Y{diameter} Stirrup"
    if role_upper == "SIDE_BAR" or shape_upper == "SC_SIDE":
        return f"Side Bar Y{diameter}"
    if count > 1:
        return f"{count}T{diameter} Straight Bar"
    return f"1T{diameter} Straight Bar"
