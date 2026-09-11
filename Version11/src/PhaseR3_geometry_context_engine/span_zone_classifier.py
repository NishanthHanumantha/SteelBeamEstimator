"""
span_zone_classifier.py — Classify annotation into span zone.
MODEL_VERSION: 8.0.0

Span zones (geometry-only labels):

  LEFT_SUPPORT_ZONE   — within physical support width at left end
  LEFT_TRANSITION_ZONE— between left support and midspan
  MIDSPAN_ZONE        — central region of beam
  RIGHT_TRANSITION_ZONE— between midspan and right support
  RIGHT_SUPPORT_ZONE  — within physical support width at right end

Zone boundaries are computed dynamically from support widths and beam length.
No hardcoded percentages; all from geometry_registry support data.

Midspan boundary: default 20% from each support zone boundary.
"""
from __future__ import annotations

from typing import List, Optional

from .geometry_models import (
    SupportLocation,
    SPAN_ZONE_LEFT_SUPPORT,
    SPAN_ZONE_LEFT_TRANS,
    SPAN_ZONE_MIDSPAN,
    SPAN_ZONE_RIGHT_TRANS,
    SPAN_ZONE_RIGHT_SUPPORT,
    SPAN_ZONE_UNKNOWN,
)

_TRANSITION_FRACTION = 0.20   # 20% of span on each side of midspan is transition


class SpanZoneClassifier:
    """
    Classify normalized position into a named span zone.
    Boundaries derived from actual support geometry.
    """

    def classify(
        self,
        normalized_pos:  float,
        supports:        List[SupportLocation],
        beam_length_mm:  float,
    ) -> tuple:
        """Returns (span_zone: str, notes: list[str])."""
        notes = []

        left  = next((s for s in supports if "LEFT"  in s.support_type), None)
        right = next((s for s in supports if "RIGHT" in s.support_type), None)

        left_zone_end   = left.zone_end_fraction   if left  else 0.0
        right_zone_start= right.zone_start_fraction if right else 1.0

        usable_span = right_zone_start - left_zone_end
        trans_span  = usable_span * _TRANSITION_FRACTION
        midspan_start = left_zone_end  + trans_span
        midspan_end   = right_zone_start - trans_span

        if normalized_pos <= left_zone_end:
            zone = SPAN_ZONE_LEFT_SUPPORT
            notes.append(
                f"pos={normalized_pos:.3f} <= left_zone_end={left_zone_end:.3f}: LEFT_SUPPORT_ZONE"
            )
        elif normalized_pos < midspan_start:
            zone = SPAN_ZONE_LEFT_TRANS
            notes.append(
                f"pos={normalized_pos:.3f} in [{left_zone_end:.3f}, {midspan_start:.3f}): LEFT_TRANSITION"
            )
        elif normalized_pos <= midspan_end:
            zone = SPAN_ZONE_MIDSPAN
            notes.append(
                f"pos={normalized_pos:.3f} in [{midspan_start:.3f}, {midspan_end:.3f}]: MIDSPAN"
            )
        elif normalized_pos < right_zone_start:
            zone = SPAN_ZONE_RIGHT_TRANS
            notes.append(
                f"pos={normalized_pos:.3f} in ({midspan_end:.3f}, {right_zone_start:.3f}): RIGHT_TRANSITION"
            )
        else:
            zone = SPAN_ZONE_RIGHT_SUPPORT
            notes.append(
                f"pos={normalized_pos:.3f} >= right_zone_start={right_zone_start:.3f}: RIGHT_SUPPORT_ZONE"
            )

        return zone, notes
