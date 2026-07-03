"""Resolve left and right bearing lengths from support faces."""

from __future__ import annotations

from typing import List

from src.framing.beam_length_model import SOURCE_GEOMETRY, EngineeringLength, STATUS_KNOWN, STATUS_UNKNOWN
from src.framing.support_face_resolver import ResolvedSupportFace


class BearingLengthResolver:
    """Calculate bearing lengths at each beam end."""

    def resolve(
        self,
        centerline_length: float,
        left_face: ResolvedSupportFace,
        right_face: ResolvedSupportFace,
    ) -> tuple[EngineeringLength, EngineeringLength]:
        left_derived = list(left_face.derived_from)
        right_derived = list(right_face.derived_from)

        if left_face.resolved and left_face.axis_position_mm >= 0:
            left = EngineeringLength(
                value=max(0.0, left_face.axis_position_mm),
                unit="mm",
                source=SOURCE_GEOMETRY,
                confidence=left_face.confidence,
                derived_from=left_derived,
                status=STATUS_KNOWN,
            )
        else:
            left = EngineeringLength.unknown(SOURCE_GEOMETRY)

        if right_face.resolved and centerline_length > 0:
            right_value = max(0.0, centerline_length - right_face.axis_position_mm)
            right = EngineeringLength(
                value=right_value,
                unit="mm",
                source=SOURCE_GEOMETRY,
                confidence=right_face.confidence,
                derived_from=right_derived,
                status=STATUS_KNOWN,
            )
        else:
            right = EngineeringLength.unknown(SOURCE_GEOMETRY)

        return left, right
