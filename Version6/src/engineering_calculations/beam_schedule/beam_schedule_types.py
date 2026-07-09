"""Beam reinforcement schedule types — Phase I.15."""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, Tuple

PREFIX_BEAM_SCHEDULE = "BEAM_SCHEDULE"
PREFIX_BEAM_SCHEDULE_REGISTRY = "BEAM_SCHEDULE_REGISTRY"
PREFIX_SCHEDULE_ROW = "ROW"
NAMESPACE_BEAM_SCHEDULE = "BEAM_SCHEDULE"

CREATED_PHASE = "I.15"
ENGINE_NAME = "BEAM_SCHEDULE_ENGINE"
DETERMINATION_METHOD = "AGGREGATION"

ROLE_TOP_MAIN = "TOP_MAIN"
ROLE_TOP_EXTRA = "TOP_EXTRA"
ROLE_BOTTOM_MAIN = "BOTTOM_MAIN"
ROLE_BOTTOM_EXTRA = "BOTTOM_EXTRA"
ROLE_SIDE_BAR = "SIDE_BAR"
ROLE_STIRRUP = "STIRRUP"
ROLE_SPACER_BAR = "SPACER_BAR"
ROLE_SFR = "SFR"
ROLE_OTHER = "OTHER"

ROLE_ORDER: Tuple[str, ...] = (
    ROLE_TOP_MAIN,
    ROLE_TOP_EXTRA,
    ROLE_BOTTOM_MAIN,
    ROLE_BOTTOM_EXTRA,
    ROLE_SIDE_BAR,
    ROLE_STIRRUP,
    ROLE_SPACER_BAR,
    ROLE_SFR,
    ROLE_OTHER,
)

ROLE_DESCRIPTIONS: Dict[str, str] = {
    ROLE_TOP_MAIN: "Top Bars",
    ROLE_TOP_EXTRA: "Top Bars - Extra",
    ROLE_BOTTOM_MAIN: "Bottom Bars",
    ROLE_BOTTOM_EXTRA: "Bottom Bars - Extra",
    ROLE_SIDE_BAR: "Side Bars",
    ROLE_STIRRUP: "Stirrups",
    ROLE_SPACER_BAR: "Spacer Bars",
    ROLE_SFR: "SFR",
    ROLE_OTHER: "Other",
}

ROLE_ORDER_INDEX: Dict[str, int] = {
    role: index for index, role in enumerate(ROLE_ORDER)
}

ROLE_DISPLAY_ORDER: Dict[str, int] = {
    ROLE_TOP_MAIN: 10,
    ROLE_TOP_EXTRA: 20,
    ROLE_BOTTOM_MAIN: 30,
    ROLE_BOTTOM_EXTRA: 40,
    ROLE_SIDE_BAR: 50,
    ROLE_STIRRUP: 60,
    ROLE_SPACER_BAR: 70,
    ROLE_SFR: 80,
    ROLE_OTHER: 999,
}

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
    "results_by_role",
    "results_by_diameter",
    "results_by_fabrication_mark",
    "results_by_engineering_ready",
    "results_by_quality_ready",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
})


class ScheduleState(str, Enum):
    """Beam schedule lifecycle state."""

    READY = "READY"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"


VALID_SCHEDULE_STATES: FrozenSet[str] = frozenset(item.value for item in ScheduleState)


def format_beam_schedule_id(sequence: int) -> str:
    return f"{PREFIX_BEAM_SCHEDULE}::{sequence:06d}"


def format_beam_schedule_registry_id() -> str:
    return PREFIX_BEAM_SCHEDULE_REGISTRY


def format_schedule_row_id(sequence: int) -> str:
    return f"{PREFIX_SCHEDULE_ROW}::{sequence:06d}"


def role_description(role: str | None) -> str:
    if not role:
        return ROLE_DESCRIPTIONS[ROLE_OTHER]
    normalized = str(role).upper()
    if normalized in ROLE_DESCRIPTIONS:
        return ROLE_DESCRIPTIONS[normalized]
    return ROLE_DESCRIPTIONS[ROLE_OTHER]


def role_display_order(role: str | None) -> int:
    if not role:
        return ROLE_DISPLAY_ORDER[ROLE_OTHER]
    normalized = str(role).upper()
    if normalized == "UNKNOWN":
        return 999
    return ROLE_DISPLAY_ORDER.get(normalized, 999)


def row_sort_key(row: dict) -> tuple[int, int, str]:
    display_order = row.get("display_order")
    if display_order is None:
        display_order = role_display_order(row.get("role"))
    diameter = row.get("diameter_mm")
    fabrication_mark = str(row.get("fabrication_mark") or "")
    return (
        int(display_order),
        int(diameter) if diameter is not None else -1,
        fabrication_mark,
    )
