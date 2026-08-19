"""Layer identity from existing P2.6.x fields. DXF layer is never the sole authority."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP26_vision_candidate_recovery.deterministic_comparator import role_family

from .config import (
    LAYER_BOTTOM,
    LAYER_SIDE,
    LAYER_SPACER,
    LAYER_STIRRUP,
    LAYER_SUPPORT_BOTTOM,
    LAYER_SUPPORT_TOP,
    LAYER_TOP,
    LAYER_UNKNOWN,
)

_FAM_TO_LAYER = {
    "TOP": LAYER_TOP,
    "BOTTOM": LAYER_BOTTOM,
    "SIDE": LAYER_SIDE,
    "STIRRUP": LAYER_STIRRUP,
    "SPACER": LAYER_SPACER,
}


def layer_from_role(role: Any) -> str:
    fam = role_family(role)
    return _FAM_TO_LAYER.get(fam, LAYER_UNKNOWN)


def layer_from_zone(*, tip_in_top: Optional[bool], tip_in_bottom: Optional[bool], position_zone: Any) -> str:
    if tip_in_bottom is True and tip_in_top is not True:
        return LAYER_BOTTOM
    if tip_in_top is True and tip_in_bottom is not True:
        return LAYER_TOP
    zone = str(position_zone or "").upper()
    if zone in ("BOTTOM_ZONE", LAYER_SUPPORT_BOTTOM):
        return LAYER_SUPPORT_BOTTOM
    if zone in ("TOP_ZONE", LAYER_SUPPORT_TOP):
        return LAYER_SUPPORT_TOP
    return LAYER_UNKNOWN


def resolve_candidate_layer(
    *,
    annotation: Optional[Dict[str, Any]] = None,
    p266_target_layer: Any = None,
    tip_votes: Optional[list] = None,
    frozen_role: Any = None,
) -> Dict[str, Any]:
    """Combine role, leader tip, spatial zone, and prior semantic layer. No DXF-only assumption."""
    ann = annotation or {}
    role_layer = layer_from_role(frozen_role if frozen_role is not None else ann.get("role"))
    tip_layer = layer_from_zone(
        tip_in_top=ann.get("tip_in_top_zone"),
        tip_in_bottom=ann.get("tip_in_bottom_zone"),
        position_zone=ann.get("position_zone"),
    )
    vote_layer = LAYER_UNKNOWN
    votes = [str(v).upper() for v in (tip_votes or []) if v]
    if votes:
        if votes.count("BOTTOM") > votes.count("TOP"):
            vote_layer = LAYER_BOTTOM
        elif votes.count("TOP") > votes.count("BOTTOM"):
            vote_layer = LAYER_TOP
    prior = str(p266_target_layer or "").upper()
    if prior not in (
        LAYER_TOP,
        LAYER_BOTTOM,
        LAYER_SIDE,
        LAYER_STIRRUP,
        LAYER_SPACER,
        LAYER_SUPPORT_TOP,
        LAYER_SUPPORT_BOTTOM,
        LAYER_UNKNOWN,
    ):
        prior = LAYER_UNKNOWN

    resolved = LAYER_UNKNOWN
    source = "unknown"
    if role_layer in (LAYER_TOP, LAYER_BOTTOM, LAYER_SIDE, LAYER_STIRRUP, LAYER_SPACER):
        resolved, source = role_layer, "deterministic_role_layer"
    elif tip_layer in (LAYER_TOP, LAYER_BOTTOM):
        resolved, source = tip_layer, "leader_association"
    elif vote_layer in (LAYER_TOP, LAYER_BOTTOM):
        resolved, source = vote_layer, "spatial_topological"
    elif prior in (LAYER_TOP, LAYER_BOTTOM, LAYER_SIDE):
        resolved, source = prior, "normalized_drawing_semantics"
    elif tip_layer in (LAYER_SUPPORT_TOP, LAYER_SUPPORT_BOTTOM):
        resolved, source = tip_layer, "spatial_topological"
    return {
        "resolved_layer": resolved,
        "role_layer": role_layer,
        "leader_layer": tip_layer,
        "vote_layer": vote_layer,
        "prior_semantic_layer": prior,
        "layer_source": source,
        "layer_evidence_incomplete": resolved == LAYER_UNKNOWN,
    }


__all__ = ["layer_from_role", "layer_from_zone", "resolve_candidate_layer"]
