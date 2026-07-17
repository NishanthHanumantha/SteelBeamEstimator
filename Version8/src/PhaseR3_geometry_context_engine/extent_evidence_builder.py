"""
extent_evidence_builder.py — Build observable extent evidence label.
MODEL_VERSION: 8.0.0

Extent evidence is based ONLY on WHERE the annotation appears on the beam.
It is an observable location label — NOT an engineering interpretation.

Labels:
  LEFT_SUPPORT_ONLY  — annotation is in the left support zone
  RIGHT_SUPPORT_ONLY — annotation is in the right support zone
  MIDSPAN_ONLY       — annotation is in the midspan zone
  LEFT_TRANSITION    — annotation is in the left transition zone
  RIGHT_TRANSITION   — annotation is in the right transition zone
  FULL_SPAN          — annotation appears to span the full beam
                       (only assigned when multiple annotations exist at both ends)
  UNKNOWN            — position unknown

IMPORTANT:
  These labels describe annotation POSITION, not bar EXTENT.
  A "LEFT_SUPPORT_ONLY" annotation means the annotation TEXT is at the left
  support zone — it does NOT mean the bar stops there.
  Bar extent determination belongs to Phase R.4.
"""
from __future__ import annotations

from typing import List

from .geometry_models import (
    EXTENT_FULL_SPAN,
    EXTENT_LEFT_SUPPORT_ONLY,
    EXTENT_RIGHT_SUPPORT_ONLY,
    EXTENT_MIDSPAN_ONLY,
    EXTENT_LEFT_TRANSITION,
    EXTENT_RIGHT_TRANSITION,
    EXTENT_UNKNOWN,
    SPAN_ZONE_LEFT_SUPPORT,
    SPAN_ZONE_RIGHT_SUPPORT,
    SPAN_ZONE_MIDSPAN,
    SPAN_ZONE_LEFT_TRANS,
    SPAN_ZONE_RIGHT_TRANS,
    GEO_CONF_HIGH,
    GEO_CONF_MEDIUM,
    GEO_CONF_LOW,
)


class ExtentEvidenceBuilder:
    """
    Build extent evidence label from span zone and position data.

    Single annotation:
      Label is based on which span zone the annotation falls in.

    Multiple annotations (same beam, same clean_text):
      If annotations span from left support to right support, label = FULL_SPAN.
    """

    def build_for_annotation(
        self,
        span_zone:       str,
        normalized_pos:  float,
        inside_left:     bool,
        inside_right:    bool,
    ) -> tuple:
        """
        Returns (extent_label, confidence, reason).
        """
        if inside_left and inside_right:
            return (
                EXTENT_FULL_SPAN,
                GEO_CONF_MEDIUM,
                "Annotation position spans both support zones",
            )
        if inside_left or span_zone == SPAN_ZONE_LEFT_SUPPORT:
            return (
                EXTENT_LEFT_SUPPORT_ONLY,
                GEO_CONF_HIGH,
                f"Annotation at left support zone (pos={normalized_pos:.3f})",
            )
        if inside_right or span_zone == SPAN_ZONE_RIGHT_SUPPORT:
            return (
                EXTENT_RIGHT_SUPPORT_ONLY,
                GEO_CONF_HIGH,
                f"Annotation at right support zone (pos={normalized_pos:.3f})",
            )
        if span_zone == SPAN_ZONE_MIDSPAN:
            return (
                EXTENT_MIDSPAN_ONLY,
                GEO_CONF_HIGH,
                f"Annotation at midspan (pos={normalized_pos:.3f})",
            )
        if span_zone == SPAN_ZONE_LEFT_TRANS:
            return (
                EXTENT_LEFT_TRANSITION,
                GEO_CONF_MEDIUM,
                f"Annotation at left transition zone (pos={normalized_pos:.3f})",
            )
        if span_zone == SPAN_ZONE_RIGHT_TRANS:
            return (
                EXTENT_RIGHT_TRANSITION,
                GEO_CONF_MEDIUM,
                f"Annotation at right transition zone (pos={normalized_pos:.3f})",
            )
        return (
            EXTENT_UNKNOWN,
            GEO_CONF_LOW,
            f"Extent unknown (span_zone={span_zone}, pos={normalized_pos:.3f})",
        )

    def refine_with_beam_group(
        self,
        annotation_id: str,
        extent_label:  str,
        confidence:    str,
        reason:        str,
        beam_normalized_positions: List[float],
    ) -> tuple:
        """
        Refine extent evidence if multiple annotations for same beam
        span from left support to right support → FULL_SPAN evidence.

        beam_normalized_positions: all normalized positions of annotations
        with the same clean_text within the same beam.
        """
        if len(beam_normalized_positions) < 2:
            return extent_label, confidence, reason

        min_pos = min(beam_normalized_positions)
        max_pos = max(beam_normalized_positions)

        if min_pos <= 0.15 and max_pos >= 0.85:
            return (
                EXTENT_FULL_SPAN,
                GEO_CONF_MEDIUM,
                f"Multiple annotations span from pos={min_pos:.3f} to pos={max_pos:.3f} "
                "— FULL_SPAN evidence from group",
            )

        return extent_label, confidence, reason
