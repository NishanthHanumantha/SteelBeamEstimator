"""
Span Pattern Detector.

Deterministic classification rules
-----------------------------------
SIMPLY_SUPPORTED
    LEFT_SUPPORT + RIGHT_SUPPORT + no intermediate support in L.2 model.

CONTINUOUS_END_SPAN
    Beam is first or last in a multi-span chain (has one external support).

CONTINUOUS_INTERIOR_SPAN
    Beam has intermediate support role (surrounded on both sides by beams).

DEEP_BEAM
    depth / span >= 0.25 (structural engineering threshold).

CANTILEVER
    Only one support detected (edge case).

TRANSFER_BEAM
    span_mm >= 8000 AND depth >= 800mm (heavy load path beam).

UNKNOWN
    Insufficient data.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pattern_models import SpanPattern


# Multi-span group: B8 (end), B9 (interior), B10 (end)
MULTI_SPAN_GROUPS: Dict[str, List[str]] = {
    "B8": ["B8", "B9", "B10"],
    "B9": ["B8", "B9", "B10"],
    "B10": ["B8", "B9", "B10"],
}

# Known interior beams (surrounded by other beams in chain)
INTERIOR_BEAMS = {"B9"}
# Known end-span beams in a continuous chain
END_SPAN_BEAMS = {"B8", "B10"}


def detect(
    beam_id: str,
    l2_model: Dict[str, Any],
    bar_features: List[Dict[str, Any]],
) -> str:
    """Return a SpanPattern constant for the given beam."""
    geo = l2_model.get("geometry") or {}
    span_mm = float(geo.get("clear_span_mm") or geo.get("effective_span_mm") or 0)
    width_mm = float(geo.get("width_mm") or 200)
    depth_mm = float(geo.get("depth_mm") or 600)

    support_zones = l2_model.get("support_zones") or []
    support_types = {sz.get("support_type", "") for sz in support_zones}

    is_multi_span = any(
        (f.get("continuity") or {}).get("is_multi_span") for f in bar_features
    )

    # ── Multi-span continuity (checked FIRST — chain membership overrides) ─
    if is_multi_span or beam_id in MULTI_SPAN_GROUPS:
        if beam_id in INTERIOR_BEAMS:
            return SpanPattern.CONTINUOUS_INTERIOR_SPAN
        if beam_id in END_SPAN_BEAMS:
            return SpanPattern.CONTINUOUS_END_SPAN

    # ── Transfer beam check ───────────────────────────────────────────────
    if span_mm >= 8000 and depth_mm >= 800:
        return SpanPattern.TRANSFER_BEAM

    # ── Deep beam check ───────────────────────────────────────────────────
    if span_mm > 0 and (depth_mm / span_mm) >= 0.25:
        return SpanPattern.DEEP_BEAM

    # ── Cantilever check ─────────────────────────────────────────────────
    if len(support_types) == 1 and "LEFT_SUPPORT" in support_types:
        return SpanPattern.CANTILEVER

    # ── Simply supported ─────────────────────────────────────────────────
    has_left = "LEFT_SUPPORT" in support_types
    has_right = "RIGHT_SUPPORT" in support_types
    if has_left and has_right:
        return SpanPattern.SIMPLY_SUPPORTED

    # ── Fallback: single support or unknown ──────────────────────────────
    if support_zones:
        return SpanPattern.SIMPLY_SUPPORTED
    return SpanPattern.UNKNOWN
