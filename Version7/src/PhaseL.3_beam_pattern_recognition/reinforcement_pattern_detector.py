"""
Reinforcement Pattern Detector.

Deterministic rules based on steel area comparison.
Steel area proxy = pi/4 * dia² * quantity (proportional comparison only).

Rules
-----
Compare top_area vs bottom_area (MAIN bars only):

  ratio = top_area / max(bottom_area, 1)

  ratio > 1.50  → TOP_REINFORCEMENT_DOMINANT  (+ TOP_HEAVY balance)
  ratio > 1.15  → TOP_HEAVY balance
  ratio < 0.67  → BOTTOM_REINFORCEMENT_DOMINANT  (+ BOTTOM_HEAVY balance)
  ratio < 0.87  → BOTTOM_HEAVY balance
  else          → BALANCED_REINFORCEMENT

Extra bars: check for extra top/bottom bars.
Support heavy: if bars concentrated at support zones.
Midspan heavy: if bars span full extent.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from pattern_models import ReinforcementPattern


def _steel_area(bars: List[Dict[str, Any]]) -> float:
    """Compute proportional steel area: sum(dia² * qty) for all bars."""
    area = 0.0
    for bar in bars:
        dia = float(bar.get("diameter_mm") or 0)
        qty = float(bar.get("quantity") or 1)
        area += (dia ** 2) * qty
    return area


def detect(
    beam_id: str,
    l2_model: Dict[str, Any],
    bar_features: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Return dict with keys:
      reinforcement_pattern, top_bottom_balance, extra_bar_pattern,
      support_reinforcement_pattern, midspan_reinforcement_pattern,
      dominant_reinforcement.
    """
    top_main = l2_model.get("top_main_bars") or []
    bot_main = l2_model.get("bottom_main_bars") or []
    top_extra = l2_model.get("top_extra_bars") or []
    bot_extra = l2_model.get("bottom_extra_bars") or []
    stirrups = l2_model.get("stirrups") or []
    sfr = l2_model.get("side_face_reinforcement") or []

    top_area = _steel_area(top_main)
    bot_area = _steel_area(bot_main)
    top_extra_area = _steel_area(top_extra)
    bot_extra_area = _steel_area(bot_extra)

    # ── Reinforcement pattern from ratio ──────────────────────────────────
    ratio = top_area / max(bot_area, 1.0)

    if top_area == 0 and bot_area == 0:
        rein_pattern = ReinforcementPattern.MINIMAL
        balance = "BALANCED"
    elif ratio > 1.50:
        rein_pattern = ReinforcementPattern.TOP_DOMINANT
        balance = "TOP_HEAVY"
    elif ratio > 1.15:
        rein_pattern = ReinforcementPattern.TOP_HEAVY
        balance = "TOP_HEAVY"
    elif ratio < 0.67:
        rein_pattern = ReinforcementPattern.BOTTOM_DOMINANT
        balance = "BOTTOM_HEAVY"
    elif ratio < 0.87:
        rein_pattern = ReinforcementPattern.BOTTOM_HEAVY
        balance = "BOTTOM_HEAVY"
    else:
        rein_pattern = ReinforcementPattern.BALANCED
        balance = "BALANCED"

    # ── Extra bars ────────────────────────────────────────────────────────
    if top_extra and bot_extra:
        extra = "EXTRA_TOP_AND_BOTTOM"
    elif top_extra:
        extra = "EXTRA_TOP"
    elif bot_extra:
        extra = "EXTRA_BOTTOM"
    else:
        extra = "NO_EXTRA_BARS"

    # ── Support zone concentration (from features) ─────────────────────────
    support_bars = [
        f for f in bar_features
        if (f.get("extent") or {}).get("left_support_only")
        or (f.get("extent") or {}).get("right_support_only")
        or (f.get("extent") or {}).get("both_supports")
    ]
    full_span_bars = [
        f for f in bar_features
        if (f.get("extent") or {}).get("full_span")
    ]
    total_bars = len(bar_features)

    if total_bars > 0:
        support_ratio = len(support_bars) / total_bars
        fullspan_ratio = len(full_span_bars) / total_bars
    else:
        support_ratio = 0.0
        fullspan_ratio = 0.0

    from pattern_models import Intensity
    if support_ratio >= 0.40:
        supp_pat = Intensity.HEAVY
    elif support_ratio >= 0.20:
        supp_pat = Intensity.MODERATE
    elif support_ratio > 0:
        supp_pat = Intensity.LIGHT
    else:
        supp_pat = Intensity.NONE

    if fullspan_ratio >= 0.60:
        mid_pat = Intensity.HEAVY
    elif fullspan_ratio >= 0.30:
        mid_pat = Intensity.MODERATE
    elif fullspan_ratio > 0:
        mid_pat = Intensity.LIGHT
    else:
        mid_pat = Intensity.NONE

    # ── Dominant reinforcement ────────────────────────────────────────────
    if top_area > bot_area:
        dominant = "TOP_MAIN_BARS"
    elif bot_area > top_area:
        dominant = "BOTTOM_MAIN_BARS"
    elif stirrups:
        dominant = "STIRRUPS"
    else:
        dominant = "BALANCED_TOP_BOTTOM"

    return {
        "reinforcement_pattern": rein_pattern,
        "top_bottom_balance": balance,
        "extra_bar_pattern": extra,
        "support_reinforcement_pattern": supp_pat,
        "midspan_reinforcement_pattern": mid_pat,
        "dominant_reinforcement": dominant,
    }
