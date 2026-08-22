"""Binding status taxonomy. Fail-closed. No beam-ID logic."""
from __future__ import annotations

from typing import Iterable, Set

from .config import (
    BEAM_AMBIGUOUS,
    BEAM_COMPATIBLE,
    BEAM_INCOMPATIBLE,
    BEAM_PARTIAL,
    STATUS_AMBIGUOUS,
    STATUS_BOUND,
    STATUS_INVALID,
    STATUS_MISSING_GEOM,
    STATUS_MISSING_RULE,
    STATUS_MISSING_SUPPORT,
    STATUS_PARTIAL,
    STATUS_UNSUPPORTED,
)

HARD_FAIL = {STATUS_INVALID, STATUS_UNSUPPORTED, STATUS_MISSING_GEOM}
SOFT_OK = {STATUS_BOUND, STATUS_PARTIAL, STATUS_MISSING_SUPPORT, STATUS_MISSING_RULE}


def decide_group_status(
    *,
    invalid: bool = False,
    ambiguous: bool = False,
    unsupported: bool = False,
    missing_geometry: bool = False,
    missing_support: bool = False,
    missing_rule: bool = False,
    partial: bool = False,
) -> str:
    if invalid:
        return STATUS_INVALID
    if ambiguous:
        return STATUS_AMBIGUOUS
    if unsupported:
        return STATUS_UNSUPPORTED
    if missing_geometry:
        return STATUS_MISSING_GEOM
    if missing_support and missing_rule:
        return STATUS_PARTIAL
    if missing_support:
        return STATUS_MISSING_SUPPORT
    if missing_rule:
        return STATUS_MISSING_RULE
    if partial:
        return STATUS_PARTIAL
    return STATUS_BOUND


def decide_beam_status(group_statuses: Iterable[str]) -> str:
    statuses: Set[str] = set(group_statuses or [])
    if not statuses:
        return BEAM_INCOMPATIBLE
    if statuses == {STATUS_BOUND}:
        return BEAM_COMPATIBLE
    has_hard = bool(statuses & HARD_FAIL)
    has_amb = STATUS_AMBIGUOUS in statuses
    has_soft = bool(statuses & SOFT_OK)
    if has_amb and not has_hard:
        return BEAM_AMBIGUOUS
    if has_hard and not has_soft:
        return BEAM_INCOMPATIBLE
    if has_hard:
        return BEAM_INCOMPATIBLE
    if has_soft and statuses != {STATUS_BOUND}:
        return BEAM_PARTIAL
    return BEAM_PARTIAL


__all__ = ["decide_beam_status", "decide_group_status"]
