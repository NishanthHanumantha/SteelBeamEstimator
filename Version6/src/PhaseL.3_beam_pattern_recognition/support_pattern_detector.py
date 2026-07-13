"""
Support Pattern Detector.

Rules
-----
NO_SUPPORT_REINFORCEMENT    No bars associated with support zones.
ONE_SIDE_REINFORCEMENT      Bars present at left OR right support only.
BOTH_SIDE_REINFORCEMENT     Bars present at both left AND right supports.
INTERMEDIATE_SUPPORT_REINFORCEMENT  Beam has intermediate support overlap.
SUPPORT_CONGESTION          >3 bars concentrated at support zone.
LONG_SUPPORT_ZONE           support_zone_ratio >= 0.30.
SHORT_SUPPORT_ZONE          support_zone_ratio < 0.12.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pattern_models import SupportPattern


def detect(
    beam_id: str,
    bar_features: List[Dict[str, Any]],
    l2_model: Dict[str, Any],
) -> str:
    """Return a SupportPattern constant for the given beam."""
    support_feats = [f.get("support") or {} for f in bar_features]

    has_left = any(s.get("left_support_overlap") for s in support_feats)
    has_right = any(s.get("right_support_overlap") for s in support_feats)
    has_intermediate = any(s.get("intermediate_support_overlap") for s in support_feats)

    # From L.2 model support_zones
    support_zones = l2_model.get("support_zones") or []
    intermediate_zones = [
        sz for sz in support_zones
        if sz.get("support_type") == "INTERMEDIATE_SUPPORT"
    ]
    if intermediate_zones:
        has_intermediate = True

    avg_ratio = 0.0
    ratios = [s.get("support_zone_ratio") for s in support_feats if s.get("support_zone_ratio") is not None]
    if ratios:
        avg_ratio = sum(ratios) / len(ratios)

    # Congestion: >3 bars cover both supports
    both_support_bars = sum(
        1 for f in bar_features
        if (f.get("extent") or {}).get("both_supports")
    )

    if has_intermediate:
        return SupportPattern.INTERMEDIATE

    if both_support_bars > 3:
        return SupportPattern.CONGESTED

    if avg_ratio >= 0.30:
        return SupportPattern.LONG_ZONE

    if not has_left and not has_right:
        return SupportPattern.NONE

    if has_left and has_right:
        if avg_ratio < 0.12 and avg_ratio > 0:
            return SupportPattern.SHORT_ZONE
        return SupportPattern.BOTH_SIDES

    if has_left or has_right:
        return SupportPattern.ONE_SIDE

    return SupportPattern.UNKNOWN
