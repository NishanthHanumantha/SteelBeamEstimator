"""Beam reinforcement summary types — Phase I.12."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_BEAM_SUMMARY = "BEAM_SUMMARY"
PREFIX_BEAM_SUMMARY_REGISTRY = "BEAM_SUMMARY_REGISTRY"
NAMESPACE_BEAM_SUMMARY = "BEAM_SUMMARY"

CREATED_PHASE = "I.12"
COMPLETION_REFINEMENT_PHASE = "I.12.1"
ENGINE_NAME = "BEAM_SUMMARY_ENGINE"
SOURCE_ENGINE_VERSION = "I.12"
RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_PRESERVED = "PRESERVED"
RESULT_STATUS_EMPTY = "EMPTY"

DETERMINATION_METHOD = "AGGREGATION"

FABRICATION_READY = "FABRICATION_READY"
FABRICATION_DEFERRED = "FABRICATION_DEFERRED"
FABRICATION_BLOCKED = "FABRICATION_BLOCKED"
FABRICATION_EMPTY = "FABRICATION_EMPTY"

ENGINEERING_COMPLETE = "COMPLETE"
ENGINEERING_PARTIAL = "PARTIAL"
ENGINEERING_BLOCKED = "BLOCKED"
ENGINEERING_EMPTY = "EMPTY"

READINESS_EMPTY = "EMPTY"
READINESS_READY = "READY"
READINESS_PARTIAL = "PARTIAL"
READINESS_BLOCKED = "BLOCKED"
READINESS_UNKNOWN = "UNKNOWN"


class BeamSummaryState(str, Enum):
    """Beam summary lifecycle state."""

    CALCULATED = "CALCULATED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    EMPTY = "EMPTY"


VALID_BEAM_SUMMARY_STATES: FrozenSet[str] = frozenset(item.value for item in BeamSummaryState)

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "determination_count",
    "determination_ids",
    "results_by_state",
    "state_counts",
    "results_by_beam",
    "results_by_beam_mark",
    "results_by_fabrication_mark",
    "results_by_shape_code",
    "results_by_diameter",
    "results_by_role",
    "results_by_engineering_group",
    "results_by_bbs",
    "results_by_identity",
    "results_by_fabrication_state",
    "results_by_engineering_state",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


def format_beam_summary_id(sequence: int) -> str:
    return f"{PREFIX_BEAM_SUMMARY}::{sequence:06d}"


def format_beam_summary_registry_id() -> str:
    return PREFIX_BEAM_SUMMARY_REGISTRY
