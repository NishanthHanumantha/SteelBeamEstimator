"""
Engineering Pattern Builder — combines all detector outputs into a single
EngineeringPattern per beam.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from continuity_detector import detect as detect_continuity
from pattern_confidence import compute_confidence
from pattern_models import EngineeringPattern, MODEL_VERSION, PHASE, make_pattern_id
from reinforcement_pattern_detector import detect as detect_reinforcement
from span_pattern_detector import detect as detect_span
from structural_behavior_detector import detect as detect_behavior
from support_pattern_detector import detect as detect_support


def build_anchorage_pattern(l2_model: Dict[str, Any], bar_features: List[Dict[str, Any]]) -> str:
    """Infer anchorage pattern from hook symbols in annotation features."""
    hook_bars = [
        f for f in bar_features
        if (f.get("annotation") or {}).get("has_hook_symbol")
    ]
    if len(hook_bars) > 0:
        return "HOOK_ANCHORAGE"
    top_extra = l2_model.get("top_extra_bars") or []
    bot_extra = l2_model.get("bottom_extra_bars") or []
    if top_extra or bot_extra:
        return "STANDARD_WITH_EXTRAS"
    return "STANDARD"


def build_development_pattern(l2_model: Dict[str, Any], bar_features: List[Dict[str, Any]]) -> str:
    """Infer development length pattern from bar coverage ratios."""
    avg_coverage = None
    coverages = [
        (f.get("support") or {}).get("support_zone_ratio")
        for f in bar_features
        if (f.get("support") or {}).get("support_zone_ratio") is not None
    ]
    if coverages:
        avg_coverage = sum(coverages) / len(coverages)
    if avg_coverage is None:
        return "UNKNOWN"
    if avg_coverage >= 0.20:
        return "EXTENDED"
    return "STANDARD"


def build_lap_pattern(l2_model: Dict[str, Any], bar_features: List[Dict[str, Any]]) -> str:
    """Infer lap splice pattern from continuity data."""
    multi_span = any(
        (f.get("continuity") or {}).get("is_multi_span") for f in bar_features
    )
    if multi_span:
        return "LAP_AT_SUPPORT"
    return "NO_LAP"


def build_engineering_notes(
    beam_id: str,
    span_pat: str,
    continuity_pat: str,
    rein_result: Dict[str, str],
    behavior: str,
    geometry_entry: Dict[str, Any],
) -> List[str]:
    notes: List[str] = []

    geo_source = (geometry_entry or {}).get("source", "ORIGINAL")
    if geo_source == "RECOVERED":
        notes.append("Geometry recovered from L.2 model + V5 beam schedule (Phase L.2.2).")

    if "CONTINUOUS" in span_pat:
        notes.append("Continuous beam: pattern classification accounts for multi-span effects.")

    if rein_result.get("top_bottom_balance") == "TOP_HEAVY":
        notes.append("Top steel area dominates — consistent with hogging or cantilever behaviour.")
    elif rein_result.get("top_bottom_balance") == "BOTTOM_HEAVY":
        notes.append("Bottom steel area dominates — consistent with sagging (positive moment) region.")

    if rein_result.get("extra_bar_pattern") not in ("NO_EXTRA_BARS", ""):
        notes.append("Extra bars detected — verify curtailment length in future phases.")

    if behavior in ("SAGGING_AND_HOGGING",):
        notes.append("Combined moment region: requires both sagging and hogging curtailment checks.")

    return notes


class EngineeringPatternBuilder:
    """Builds one EngineeringPattern per beam from all detector results."""

    def build(
        self,
        beam_id: str,
        bar_features: List[Dict[str, Any]],
        l2_model: Dict[str, Any],
        geometry_entry: Dict[str, Any],
        l2_continuity_data: Dict[str, Any],
        run_timestamp: str,
    ) -> EngineeringPattern:
        # ── Detectors ─────────────────────────────────────────────────────
        span_pat = detect_span(beam_id, l2_model, bar_features)
        cont_pat = detect_continuity(beam_id, bar_features, l2_continuity_data)
        rein_result = detect_reinforcement(beam_id, l2_model, bar_features)
        supp_pat = detect_support(beam_id, bar_features, l2_model)
        behavior = detect_behavior(beam_id, l2_model, bar_features, cont_pat)

        # ── Anchorage / development / lap ─────────────────────────────────
        anchorage = build_anchorage_pattern(l2_model, bar_features)
        dev_len = build_development_pattern(l2_model, bar_features)
        lap = build_lap_pattern(l2_model, bar_features)

        # ── Confidence ────────────────────────────────────────────────────
        conf = compute_confidence(beam_id, bar_features, geometry_entry, l2_model)

        # ── Notes ─────────────────────────────────────────────────────────
        notes = build_engineering_notes(
            beam_id, span_pat, cont_pat, rein_result, behavior, geometry_entry
        )

        return EngineeringPattern(
            pattern_id=make_pattern_id(beam_id),
            beam_id=beam_id,
            beam_name=beam_id,
            pattern_version=MODEL_VERSION,
            span_pattern=span_pat,
            support_pattern=supp_pat,
            reinforcement_pattern=rein_result["reinforcement_pattern"],
            continuity_pattern=cont_pat,
            structural_behavior=behavior,
            support_reinforcement_pattern=rein_result["support_reinforcement_pattern"],
            midspan_reinforcement_pattern=rein_result["midspan_reinforcement_pattern"],
            top_bottom_balance=rein_result["top_bottom_balance"],
            extra_bar_pattern=rein_result["extra_bar_pattern"],
            anchorage_pattern=anchorage,
            development_length_pattern=dev_len,
            lap_pattern=lap,
            dominant_reinforcement=rein_result["dominant_reinforcement"],
            classification_confidence=conf["score"],
            confidence_level=conf["level"],
            engineering_notes=notes,
            traceability={
                "phase": PHASE,
                "model_version": MODEL_VERSION,
                "beam_id": beam_id,
                "geometry_id": (geometry_entry or {}).get("geometry_id", ""),
                "geometry_source": (geometry_entry or {}).get("source", "UNKNOWN"),
                "pattern_generated_at": run_timestamp,
                "input_source": "L2.1_EngineeringFeatureDatabase",
                "bar_features_count": len(bar_features),
                "l2_model_bars": sum(
                    len(l2_model.get(k) or [])
                    for k in ["top_main_bars", "bottom_main_bars", "stirrups",
                               "top_extra_bars", "bottom_extra_bars",
                               "side_face_reinforcement"]
                ),
            },
        )
