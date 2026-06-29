"""Resolve clear span — face-to-face distance between supports."""

from __future__ import annotations

from typing import List

from src.framing.beam_length_model import (
    SOURCE_SUPPORT_FACE,
    EngineeringLength,
    STATUS_KNOWN,
    STATUS_UNKNOWN,
)
from src.framing.support_face_resolver import ResolvedSupportFace


class ClearSpanResolver:
    """Calculate face-to-face clear span along the beam axis."""

    def resolve(
        self,
        left_face: ResolvedSupportFace,
        right_face: ResolvedSupportFace,
        centerline_length: float,
    ) -> EngineeringLength:
        derived: List[str] = []
        if left_face.derived_from:
            derived.extend(left_face.derived_from)
        if right_face.derived_from:
            derived.extend(right_face.derived_from)

        if left_face.axis_position_mm is None or right_face.axis_position_mm is None:
            return EngineeringLength.unknown(SOURCE_SUPPORT_FACE)

        clear = right_face.axis_position_mm - left_face.axis_position_mm
        if clear < 0:
            return EngineeringLength.unknown(SOURCE_SUPPORT_FACE)

        both_structural = left_face.resolved and right_face.resolved
        confidence = min(left_face.confidence, right_face.confidence)
        if not both_structural:
            confidence *= 0.88

        return EngineeringLength(
            value=min(clear, centerline_length),
            unit="mm",
            source=SOURCE_SUPPORT_FACE,
            confidence=confidence,
            derived_from=derived,
            status=STATUS_KNOWN,
        )
