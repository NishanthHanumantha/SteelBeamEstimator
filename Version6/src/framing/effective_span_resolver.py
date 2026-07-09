"""Resolve effective span for structural calculations."""

from __future__ import annotations

from typing import Any, List

from src.framing.beam_length_model import (
    SOURCE_CENTERLINE,
    SOURCE_SUPPORT_FACE,
    EngineeringLength,
    STATUS_KNOWN,
)
from src.framing.support_face_resolver import ResolvedSupportFace


class EffectiveSpanResolver:
    """Calculate effective span — refined from centerline when support faces permit."""

    def __init__(self, config: dict[str, Any]) -> None:
        el = config.get("engineering_length", {})
        self._min_face_confidence = float(el.get("effective_span_min_face_confidence", 0.85))

    def resolve(
        self,
        centerline_length: float,
        clear_span: EngineeringLength,
        left_face: ResolvedSupportFace,
        right_face: ResolvedSupportFace,
        derived_from: List[str],
    ) -> EngineeringLength:
        faces_reliable = (
            left_face.resolved
            and right_face.resolved
            and left_face.confidence >= self._min_face_confidence
            and right_face.confidence >= self._min_face_confidence
            and clear_span.status == "KNOWN"
            and clear_span.value is not None
        )

        if faces_reliable:
            return EngineeringLength(
                value=float(clear_span.value),
                unit="mm",
                source=SOURCE_SUPPORT_FACE,
                confidence=min(clear_span.confidence, left_face.confidence, right_face.confidence),
                derived_from=derived_from,
                status=STATUS_KNOWN,
            )

        return EngineeringLength(
            value=centerline_length,
            unit="mm",
            source=SOURCE_CENTERLINE,
            confidence=0.9,
            derived_from=["CENTERLINE"],
            status=STATUS_KNOWN,
        )
