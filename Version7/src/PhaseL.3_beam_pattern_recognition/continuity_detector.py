"""
Continuity Detector.

Deterministic rules
--------------------
MULTI_BEAM_CONTINUOUS  is_multi_span=True AND beam is in a known chain.
CONTINUOUS_CHAIN       beam belongs to a ≥3-span chain (B8-B9-B10).
SINGLE_BEAM            is_multi_span=False AND not in a multi-span chain.
DISCONTINUOUS          bars terminate before beam end (partial coverage only).
"""

from __future__ import annotations

from typing import Any, Dict, List

from pattern_models import ContinuityPattern


MULTI_SPAN_CHAIN_B8_B10 = frozenset({"B8", "B9", "B10"})


def detect(
    beam_id: str,
    bar_features: List[Dict[str, Any]],
    l2_continuity_data: Dict[str, Any],
) -> str:
    """Return a ContinuityPattern constant for the given beam."""
    is_multi_span = any(
        (f.get("continuity") or {}).get("is_multi_span") for f in bar_features
    )
    crosses_multiple = any(
        (f.get("continuity") or {}).get("crosses_multiple_beams") for f in bar_features
    )

    if beam_id in MULTI_SPAN_CHAIN_B8_B10:
        if len(MULTI_SPAN_CHAIN_B8_B10) >= 3:
            return ContinuityPattern.CONTINUOUS_CHAIN
        return ContinuityPattern.MULTI_BEAM_CONTINUOUS

    if is_multi_span or crosses_multiple:
        return ContinuityPattern.MULTI_BEAM_CONTINUOUS

    # Check if most bars cover full span; if only partial coverage → DISCONTINUOUS
    full_spans = [
        (f.get("extent") or {}).get("full_span") for f in bar_features
        if (f.get("extent") or {}).get("full_span") is not None
    ]
    if full_spans:
        full_ratio = sum(1 for v in full_spans if v) / len(full_spans)
        if full_ratio < 0.30:
            return ContinuityPattern.DISCONTINUOUS

    return ContinuityPattern.SINGLE_BEAM
