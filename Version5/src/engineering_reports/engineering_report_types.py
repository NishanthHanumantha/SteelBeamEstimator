"""Engineering report model types — Phase I.16."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_ENGINEERING_REPORT = "REPORT"
PREFIX_ENGINEERING_REPORT_REGISTRY = "ENGINEERING_REPORT_REGISTRY"
NAMESPACE_ENGINEERING_REPORT = "ENGINEERING_REPORT"

CREATED_PHASE = "I.16"
ENGINE_NAME = "ENGINEERING_REPORT_ENGINE"
DETERMINATION_METHOD = "REPORT_MODEL"
REPORT_TYPE_BEAM_REINFORCEMENT_SCHEDULE = "BEAM_REINFORCEMENT_SCHEDULE"
MODEL_VERSION = "5.20.0"

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
    "results_by_engineering_ready",
    "results_by_quality_ready",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


class ReportState(str, Enum):
    """Engineering report lifecycle state."""

    READY = "READY"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"


VALID_REPORT_STATES: FrozenSet[str] = frozenset(item.value for item in ReportState)


def format_engineering_report_id(sequence: int) -> str:
    return f"{PREFIX_ENGINEERING_REPORT}::{sequence:06d}"


def format_engineering_report_registry_id() -> str:
    return PREFIX_ENGINEERING_REPORT_REGISTRY
