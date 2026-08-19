"""Map existing R.1 / R1.3 roles onto physical layer + reinforcement role."""
from __future__ import annotations

from typing import Any, Tuple

from PhaseP26_vision_candidate_recovery.deterministic_comparator import role_family

from .config import (
    FAMILY_LONGITUDINAL,
    FAMILY_OTHER,
    FAMILY_SIDE,
    FAMILY_SPACER,
    FAMILY_STIRRUP,
    LAYER_BOTTOM,
    LAYER_SIDE,
    LAYER_SPACER,
    LAYER_STIRRUP,
    LAYER_TOP,
    LAYER_UNKNOWN,
    ROLE_EXTRA,
    ROLE_MAIN,
    ROLE_SIDE_FACE,
    ROLE_SPACER,
    ROLE_STIRRUP,
    ROLE_UNKNOWN,
    ZONE_BOTH_SUPPORTS,
    ZONE_FULL_SPAN,
    ZONE_LEFT_SUPPORT,
    ZONE_RIGHT_SUPPORT,
    ZONE_SUPPORT,
    ZONE_UNKNOWN,
)

_FAM_TO_LAYER = {
    "TOP": LAYER_TOP,
    "BOTTOM": LAYER_BOTTOM,
    "SIDE": LAYER_SIDE,
    "STIRRUP": LAYER_STIRRUP,
    "SPACER": LAYER_SPACER,
}


def physical_layer_from_role(role: Any) -> str:
    fam = role_family(role)
    return _FAM_TO_LAYER.get(fam, LAYER_UNKNOWN)


def family_from_layer(layer: str) -> str:
    if layer in (LAYER_TOP, LAYER_BOTTOM):
        return FAMILY_LONGITUDINAL
    if layer == LAYER_STIRRUP:
        return FAMILY_STIRRUP
    if layer == LAYER_SIDE:
        return FAMILY_SIDE
    if layer == LAYER_SPACER:
        return FAMILY_SPACER
    return FAMILY_OTHER


def reinforcement_role_from_token(role: Any) -> str:
    text = str(role or "").strip().upper()
    if "STIRRUP" in text:
        return ROLE_STIRRUP
    if "SPACER" in text:
        return ROLE_SPACER
    if "SIDE" in text:
        return ROLE_SIDE_FACE
    if "EXTRA" in text:
        return ROLE_EXTRA
    if "MAIN" in text or text in ("TOP_BAR", "BOTTOM_BAR", "TOP", "BOTTOM"):
        return ROLE_MAIN
    return ROLE_UNKNOWN


def zone_from_piece(*, piece_type: Any, support_zone: Any, extent: Any, position_zone: Any) -> str:
    piece = str(piece_type or "").upper()
    if piece.endswith("_LEFT") or "LEFT_SUPPORT" in piece:
        return ZONE_LEFT_SUPPORT
    if piece.endswith("_RIGHT") or "RIGHT_SUPPORT" in piece:
        return ZONE_RIGHT_SUPPORT
    for token in (support_zone, extent, position_zone):
        val = str(token or "").upper()
        if val in (ZONE_FULL_SPAN, ZONE_BOTH_SUPPORTS, ZONE_LEFT_SUPPORT, ZONE_RIGHT_SUPPORT, ZONE_SUPPORT):
            return val
        if val == "BOTH_SUPPORTS":
            return ZONE_BOTH_SUPPORTS
        if val in ("LEFT_SUPPORT", "TOP_EXTRA_LEFT", "BOTTOM_EXTRA_LEFT"):
            return ZONE_LEFT_SUPPORT
        if val in ("RIGHT_SUPPORT", "TOP_EXTRA_RIGHT", "BOTTOM_EXTRA_RIGHT"):
            return ZONE_RIGHT_SUPPORT
        if val in ("FULL_SPAN", "SPAN"):
            return ZONE_FULL_SPAN
        if "SUPPORT" in val:
            return ZONE_SUPPORT
    if "EXTRA" in piece:
        return ZONE_SUPPORT
    if "MAIN" in piece:
        return ZONE_FULL_SPAN
    return ZONE_UNKNOWN


def merge_zones(zones: Tuple[str, ...]) -> str:
    uniq = tuple(dict.fromkeys(z for z in zones if z and z != ZONE_UNKNOWN))
    if not uniq:
        return ZONE_UNKNOWN
    if ZONE_LEFT_SUPPORT in uniq and ZONE_RIGHT_SUPPORT in uniq:
        return ZONE_BOTH_SUPPORTS
    if len(uniq) == 1:
        return uniq[0]
    if ZONE_BOTH_SUPPORTS in uniq:
        return ZONE_BOTH_SUPPORTS
    return ZONE_UNKNOWN


__all__ = [
    "family_from_layer",
    "merge_zones",
    "physical_layer_from_role",
    "reinforcement_role_from_token",
    "zone_from_piece",
]
