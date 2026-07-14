"""
Structural Behaviour Detector.

Infers expected structural behaviour from reinforcement distribution.
Uses deterministic rules ONLY — no structural analysis performed.

Rules
-----
SAGGING_BEAM
    Bottom main area significantly > top main area (ratio < 0.70).
    Characteristic of positive moment region (midspan dominant).

HOGGING_BEAM
    Top main area significantly > bottom main area (ratio > 1.40).
    Characteristic of negative moment region (support dominant).

SAGGING_AND_HOGGING
    Top main + bottom main both present AND the beam is multi-span
    OR extra bars exist at support zones.
    Typical of continuous beams.

SUPPORT_MOMENT_DOMINANT
    Support-only bars > midspan bars (large proportion at supports).

MIDSPAN_MOMENT_DOMINANT
    Full-span / midspan bars dominate.

SYMMETRIC
    Left and right support details are mirror images.

ASYMMETRIC
    Left support ≠ right support reinforcement detail.

UNKNOWN
    Insufficient data.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from pattern_models import StructuralBehavior, ContinuityPattern


def _steel_area(bars: List[Dict[str, Any]]) -> float:
    area = 0.0
    for bar in bars:
        dia = float(bar.get("diameter_mm") or 0)
        qty = float(bar.get("quantity") or 1)
        area += dia * dia * qty
    return area


def detect(
    beam_id: str,
    l2_model: Dict[str, Any],
    bar_features: List[Dict[str, Any]],
    continuity_pattern: str,
) -> str:
    """Return a StructuralBehavior constant."""
    top_main = l2_model.get("top_main_bars") or []
    bot_main = l2_model.get("bottom_main_bars") or []
    top_extra = l2_model.get("top_extra_bars") or []
    bot_extra = l2_model.get("bottom_extra_bars") or []

    top_area = _steel_area(top_main)
    bot_area = _steel_area(bot_main)

    is_multi_span = continuity_pattern in (
        ContinuityPattern.MULTI_BEAM_CONTINUOUS,
        ContinuityPattern.CONTINUOUS_CHAIN,
    )

    has_extra_at_support = bool(top_extra) or bool(bot_extra)

    # Support-only bars
    support_only_count = sum(
        1 for f in bar_features
        if (f.get("extent") or {}).get("left_support_only")
        or (f.get("extent") or {}).get("right_support_only")
        or (f.get("extent") or {}).get("both_supports")
    )
    full_span_count = sum(
        1 for f in bar_features
        if (f.get("extent") or {}).get("full_span")
    )
    total = len(bar_features)

    # Multi-span or extra bars at supports → sagging+hogging
    if is_multi_span or (has_extra_at_support and top_area > 0 and bot_area > 0):
        return StructuralBehavior.SAGGING_AND_HOGGING

    if top_area == 0 and bot_area == 0:
        return StructuralBehavior.UNKNOWN

    ratio = top_area / max(bot_area, 1.0)

    if ratio > 1.40:
        # Top heavy → hogging (support moment)
        if total > 0 and support_only_count / total > 0.30:
            return StructuralBehavior.SUPPORT_MOMENT_DOMINANT
        return StructuralBehavior.HOGGING_BEAM

    if ratio < 0.70:
        # Bottom heavy → sagging (midspan moment)
        if total > 0 and full_span_count / total > 0.50:
            return StructuralBehavior.MIDSPAN_MOMENT_DOMINANT
        return StructuralBehavior.SAGGING_BEAM

    # Roughly balanced → check symmetry
    # Symmetry: left support bars ≈ right support bars
    left_bars = sum(
        1 for f in bar_features
        if (f.get("extent") or {}).get("left_support_only")
    )
    right_bars = sum(
        1 for f in bar_features
        if (f.get("extent") or {}).get("right_support_only")
    )

    if abs(left_bars - right_bars) <= 1:
        return StructuralBehavior.SYMMETRIC
    return StructuralBehavior.ASYMMETRIC
