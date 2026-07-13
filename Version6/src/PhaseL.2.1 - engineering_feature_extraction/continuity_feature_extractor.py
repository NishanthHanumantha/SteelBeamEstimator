"""
Continuity Feature Extractor — how far the bar extends across spans.
Observations only. No semantic meaning assigned.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engineering_feature_model import (
    ContinuityFeatures,
    CONT_SINGLE, CONT_MULTI, CONT_UNKNOWN,
)

# Beams that belong to multi-span continuous drawings
MULTI_SPAN_GROUPS: Dict[str, List[str]] = {
    "B8": ["B8", "B9", "B10"],
    "B9": ["B8", "B9", "B10"],
    "B10": ["B8", "B9", "B10"],
}

CONTINUITY_THRESHOLD = 0.80  # bar reaching >= 80% of span → considered continuous


class ContinuityFeatureExtractor:
    """Extract continuity observations for a single bar."""

    def extract(
        self,
        bar: Dict[str, Any],
        beam_model: Dict[str, Any],
        config: Dict[str, Any],
    ) -> ContinuityFeatures:
        beam_id = bar.get("beam_id") or beam_model.get("beam_id") or ""
        coverage = bar.get("coverage_ratio") or 0.0
        extent = (bar.get("extent") or "").upper()
        bar_continuity = (bar.get("continuity") or "").upper()
        threshold = config.get("continuity_threshold", CONTINUITY_THRESHOLD)

        is_multi_span_beam = beam_id in MULTI_SPAN_GROUPS
        group = MULTI_SPAN_GROUPS.get(beam_id, [])

        # Is bar continuous (spans ≥ 80% of its beam)?
        is_continuous = (
            coverage >= threshold
            or "FULL" in extent
            or "MULTI_BEAM" in bar_continuity
            or "CONTINUOUS" in bar_continuity
        )

        is_multi_span = "MULTI_BEAM" in bar_continuity or (is_multi_span_beam and is_continuous)
        is_single_span = not is_multi_span

        crosses_support = (
            "FULL" in extent
            or "SUPPORT" in extent
            or "BOTH" in extent
            or (coverage is not None and coverage >= threshold)
        )

        crosses_multiple_beams = is_multi_span
        n_beams = len(group) if is_multi_span else 1
        beam_seq = group if is_multi_span else [beam_id]

        # Termination points
        terminations: List[str] = []
        if "LEFT_SUPPORT_ONLY" in extent or "FULL" in extent or "BOTH" in extent:
            terminations.append("LEFT_SUPPORT")
        if "RIGHT_SUPPORT_ONLY" in extent or "FULL" in extent or "BOTH" in extent:
            terminations.append("RIGHT_SUPPORT")
        if "MIDSPAN" in extent:
            terminations.append("MIDSPAN")

        cont_type = (
            CONT_MULTI if is_multi_span
            else CONT_SINGLE if is_single_span
            else CONT_UNKNOWN
        )

        return ContinuityFeatures(
            is_continuous=is_continuous,
            is_single_span=is_single_span,
            is_multi_span=is_multi_span,
            crosses_support=crosses_support,
            crosses_multiple_beams=crosses_multiple_beams,
            number_of_beams_crossed=n_beams,
            beam_sequence=beam_seq,
            termination_points=terminations,
            continuity_type=cont_type,
        )
