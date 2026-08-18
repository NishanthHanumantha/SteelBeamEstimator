"""
Deterministic spatial/context evidence aggregation.

Never lets a single feature produce SKIP. Prefers AMBIGUOUS / INSUFFICIENT
over unsafe certainty. Does not use GT, estimator, sampling labels, or Vision.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .config import (
    CLEARANCE_RATIO,
    REPEAT_SEPARATION_RATIO,
    STATUS_AMBIGUOUS,
    STATUS_CALL,
    STATUS_INSUFFICIENT,
    STATUS_SKIP,
)


def classify_spatial_context(
    *,
    spatial: Dict[str, Any],
    production_features: Optional[Dict[str, Any]] = None,
    longitudinal_coverage: Optional[str] = None,
    clearance_ratio: float = CLEARANCE_RATIO,
    repeat_ratio: float = REPEAT_SEPARATION_RATIO,
) -> Dict[str, Any]:
    del clearance_ratio, repeat_ratio
    feat = production_features or {}
    codes: List[str] = []
    call_votes = 0
    skip_votes = 0

    xy_ok = bool(spatial.get("annotation_xy_available"))
    leader_ok = bool(spatial.get("leader_geometry_available"))
    env_ok = bool(spatial.get("envelope_available"))
    if not xy_ok:
        codes.append("NO_ANNOTATION_XY")
    if not leader_ok:
        codes.append("NO_LEADER_GEOMETRY")
    if not spatial.get("physical_bar_geometry_available"):
        codes.append("NO_PHYSICAL_BAR_GEOMETRY")
    if not xy_ok and not leader_ok:
        codes.append("NO_RELIABLE_SPATIAL_EVIDENCE")
        return {
            "context_status": STATUS_INSUFFICIENT,
            "evidence_codes": list(dict.fromkeys(codes)),
            "call_votes": 0,
            "skip_votes": 0,
            "context_score": 0,
            "note": "No annotation XY and no leader geometry.",
        }

    populated = str(spatial.get("populated_layer") or feat.get("populated_layer") or "")
    unique_specs = int(feat.get("unique_accepted_spec_count") or 0)
    inst = int(feat.get("accepted_instance_count") or 0)

    if spatial.get("repeated_separate_location"):
        codes.append("REPEATED_SEPARATE_LOCATION")
        codes.append("ANNOTATION_CLUSTER_SEPARATION")
        codes.append("SPATIAL_SEPARATION_STRONG")
        call_votes += 2
    elif spatial.get("repeated_same_location"):
        codes.append("REPEATED_SAME_LOCATION")
        skip_votes += 1

    if int(spatial.get("annotation_cluster_count") or 0) >= 2:
        if "ANNOTATION_CLUSTER_SEPARATION" not in codes:
            codes.append("ANNOTATION_CLUSTER_SEPARATION")
        call_votes += 1
    if int(spatial.get("physical_bar_cluster_count") or 0) >= 2:
        codes.append("SEPARATE_CLUSTER")
        call_votes += 1
    elif int(spatial.get("physical_bar_cluster_count") or 0) == 1 and spatial.get(
        "physical_bar_geometry_available"
    ):
        codes.append("SAME_CLUSTER")

    votes: Sequence[str] = spatial.get("tip_layer_votes") or []
    strong_top = sum(1 for v in votes if v == "TOP")
    strong_bot = sum(1 for v in votes if v == "BOTTOM")
    boundary = sum(1 for v in votes if v == "BOUNDARY")
    if strong_top:
        codes.append("TOP_PROXIMITY")
    if strong_bot:
        codes.append("BOTTOM_PROXIMITY")
    if boundary:
        codes.append("ZONE_BOUNDARY")

    if populated == "TOP" and strong_bot and not strong_top:
        codes.append("CROSS_LAYER_SEPARATION")
        codes.append("LEADER_SEPARATION")
        call_votes += 2
    elif populated == "BOTTOM" and strong_top and not strong_bot:
        codes.append("CROSS_LAYER_SEPARATION")
        codes.append("LEADER_SEPARATION")
        call_votes += 2
    elif populated == "TOP" and strong_top and not strong_bot and not boundary:
        codes.append("SPATIAL_MATCH_STRONG")
        skip_votes += 2
    elif populated == "BOTTOM" and strong_bot and not strong_top and not boundary:
        codes.append("SPATIAL_MATCH_STRONG")
        skip_votes += 2
    elif boundary and not strong_bot and not strong_top:
        skip_votes += 0
        call_votes += 0

    if unique_specs > 1:
        call_votes += 1
    if inst > 1 and spatial.get("repeated_separate_location"):
        call_votes += 1

    score = call_votes - skip_votes
    if call_votes >= 2 and skip_votes >= 2:
        status = STATUS_AMBIGUOUS
    elif call_votes >= 2 and call_votes > skip_votes:
        status = STATUS_CALL
    elif (
        skip_votes >= 2
        and skip_votes > call_votes
        and unique_specs <= 1
        and not spatial.get("repeated_separate_location")
        and "CROSS_LAYER_SEPARATION" not in codes
    ):
        status = STATUS_SKIP
    elif not env_ok or (not votes and not spatial.get("repeated_separate_location")):
        status = STATUS_INSUFFICIENT
        if "NO_RELIABLE_SPATIAL_EVIDENCE" not in codes:
            codes.append("NO_RELIABLE_SPATIAL_EVIDENCE")
    else:
        status = STATUS_AMBIGUOUS

    if longitudinal_coverage == "FULLY_COVERED" and status == STATUS_SKIP:
        status = STATUS_AMBIGUOUS

    return {
        "context_status": status,
        "evidence_codes": list(dict.fromkeys(codes)),
        "call_votes": call_votes,
        "skip_votes": skip_votes,
        "context_score": score,
        "populated_layer": populated or None,
        "unique_accepted_spec_count": unique_specs,
        "note": (
            "Categorical aggregation. A single proximity feature cannot SKIP. "
            "CALL is preferred when evidence conflicts."
        ),
    }


__all__ = ["classify_spatial_context"]
