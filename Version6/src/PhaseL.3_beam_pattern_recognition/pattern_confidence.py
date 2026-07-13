"""
Pattern Confidence — compute a 0–1 confidence score per beam pattern.

Score components
----------------
feature_completeness   0–0.35   from feature_completeness_score of bars
geometry_completeness  0–0.25   from geometry registry (ORIGINAL > RECOVERED)
bar_classification     0–0.20   based on bar count + classification source
support_confidence     0–0.10   from support feature coverage
continuity_confidence  0–0.10   from continuity feature completeness

Level thresholds
----------------
HIGH   >= 0.80
MEDIUM >= 0.55
LOW    < 0.55
"""

from __future__ import annotations

from typing import Any, Dict, List

from pattern_models import ConfidenceLevel


def compute_confidence(
    beam_id: str,
    bar_features: List[Dict[str, Any]],
    geometry_entry: Dict[str, Any],
    l2_model: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute classification confidence for a beam.

    Parameters
    ----------
    beam_id:        Target beam identifier.
    bar_features:   List of feature records for this beam (from L.2.1 DB).
    geometry_entry: Geometry registry entry for this beam.
    l2_model:       L.2 BeamReinforcementModel for this beam.

    Returns
    -------
    Dict with score (float 0–1) and level (str HIGH/MEDIUM/LOW).
    """
    score = 0.0

    # ── 1. Feature completeness (max 0.35) ──────────────────────────────
    if bar_features:
        avg_completeness = sum(
            f.get("feature_completeness_score", 0.5) for f in bar_features
        ) / len(bar_features)
        score += avg_completeness * 0.35
    # If no original bars (recovered beams), apply a base 0.15
    is_recovered = (geometry_entry or {}).get("source") == "RECOVERED"
    if not bar_features or is_recovered:
        score += 0.15

    # ── 2. Geometry completeness (max 0.25) ──────────────────────────────
    if geometry_entry:
        geo_source = geometry_entry.get("source", "UNKNOWN")
        geo_confidence = float(geometry_entry.get("confidence", 0))
        if geo_source == "ORIGINAL":
            score += min(geo_confidence * 0.25, 0.25)
        else:
            score += min(geo_confidence * 0.15, 0.15)
    # No geometry → 0 contribution

    # ── 3. Bar classification confidence (max 0.20) ──────────────────────
    total_bars = 0
    ref_anchored = 0
    for role_key in ["top_main_bars", "bottom_main_bars", "stirrups",
                     "top_extra_bars", "bottom_extra_bars", "side_face_reinforcement"]:
        bars = (l2_model or {}).get(role_key) or []
        total_bars += len(bars)
        ref_anchored += sum(1 for b in bars if b.get("is_reference_anchored"))

    if total_bars > 0:
        ref_ratio = ref_anchored / total_bars
        score += ref_ratio * 0.15
        score += min(total_bars / 10.0, 1.0) * 0.05
    elif is_recovered:
        score += 0.05  # Recovered beam with placeholder bars

    # ── 4. Support confidence (max 0.10) ─────────────────────────────────
    support_feats = [f.get("support") or {} for f in bar_features]
    if support_feats:
        has_support_info = any(
            s.get("left_support_overlap") is not None for s in support_feats
        )
        if has_support_info:
            score += 0.10
    else:
        score += 0.04  # partial credit

    # ── 5. Continuity confidence (max 0.10) ───────────────────────────────
    cont_feats = [f.get("continuity") or {} for f in bar_features]
    if cont_feats:
        has_continuity = any(
            c.get("is_continuous") is not None for c in cont_feats
        )
        if has_continuity:
            score += 0.10
    else:
        score += 0.04

    score = round(min(score, 1.0), 4)

    if score >= 0.80:
        level = ConfidenceLevel.HIGH
    elif score >= 0.55:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    return {"score": score, "level": level}
