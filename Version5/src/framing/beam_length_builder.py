"""Build the Engineering Length Model for all beams."""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from src.framing.beam_length_model import (
    GOVERNING_CENTERLINE,
    GOVERNING_CLEAR_SPAN,
    GOVERNING_EFFECTIVE_SPAN,
    SOURCE_CENTERLINE,
    SOURCE_ENGINEERING_MODEL,
    SOURCE_FRAMING_PLAN,
    STATUS_ESTIMATED,
    STATUS_KNOWN,
    BeamLengthModel,
    EngineeringLength,
    GoverningSpan,
)
from src.framing.bearing_length_resolver import BearingLengthResolver
from src.framing.clear_span_resolver import ClearSpanResolver
from src.framing.effective_span_resolver import EffectiveSpanResolver
from src.framing.support_face_resolver import SupportFaceResolver


class BeamLengthBuilder:
    """Assemble complete engineering length models from geometry and supports."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._enabled = bool(config.get("engineering_length", {}).get("enable", True))
        self._face_resolver = SupportFaceResolver(config)
        self._bearing_resolver = BearingLengthResolver()
        self._clear_span_resolver = ClearSpanResolver()
        self._effective_resolver = EffectiveSpanResolver(config)
        self._stats: Dict[str, int] = {
            "centerline_lengths": 0,
            "support_face_lengths": 0,
            "clear_spans": 0,
            "effective_spans": 0,
            "design_spans": 0,
        }

    def build_model(
        self,
        model: dict[str, Any],
        structural_context: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Engineering length model disabled in config")
            return model

        length_exports: List[dict[str, Any]] = []

        for beam in model.get("beams", []):
            length_model = self._build_beam_length(beam, model, structural_context)
            beam["length_model"] = length_model.to_dict()
            length_exports.append(
                {
                    "beam_id": beam["beam_id"],
                    "beam_mark": beam["beam_mark"],
                    "length_model": length_model.to_dict(),
                }
            )
            self._update_stats(length_model)

        model["length_model_export"] = length_exports
        model["engineering_length_summary"] = dict(self._stats)
        model["phase"] = "Phase F.4"
        model["model_version"] = "1.3"

        logger.info(
            "Engineering length — CL={}, faces={}, clear={}, effective={}, design={}",
            self._stats["centerline_lengths"],
            self._stats["support_face_lengths"],
            self._stats["clear_spans"],
            self._stats["effective_spans"],
            self._stats["design_spans"],
        )
        return model

    def _build_beam_length(
        self,
        beam: dict[str, Any],
        model: dict[str, Any],
        structural_context: dict[str, Any],
    ) -> BeamLengthModel:
        geometry = beam.get("geometry", {})
        centerline = geometry.get("centerline") or {}
        cl_value = float(centerline.get("length_mm") or geometry.get("length_mm") or 0.0)

        centerline_length = EngineeringLength(
            value=cl_value if cl_value > 0 else None,
            unit="mm",
            source=SOURCE_CENTERLINE,
            confidence=float(geometry.get("confidence", 1.0)),
            derived_from=["F1_CENTERLINE"],
            status=STATUS_KNOWN if cl_value > 0 else "UNKNOWN",
        )

        left_face, right_face = self._face_resolver.resolve(beam, model, structural_context)
        derived = list(dict.fromkeys(left_face.derived_from + right_face.derived_from))

        support_face_length = EngineeringLength(
            value=max(0.0, right_face.axis_position_mm - left_face.axis_position_mm),
            unit="mm",
            source="SUPPORT_FACE",
            confidence=min(left_face.confidence, right_face.confidence),
            derived_from=derived,
            status=STATUS_KNOWN,
        )

        bearing_left, bearing_right = self._bearing_resolver.resolve(
            cl_value, left_face, right_face
        )
        clear_span = self._clear_span_resolver.resolve(left_face, right_face, cl_value)
        effective_span = self._effective_resolver.resolve(
            cl_value, clear_span, left_face, right_face, derived
        )

        design_value = effective_span.value if effective_span.value is not None else cl_value
        design_span = EngineeringLength(
            value=design_value,
            unit="mm",
            source=SOURCE_ENGINEERING_MODEL,
            confidence=effective_span.confidence * 0.9,
            derived_from=["EFFECTIVE_SPAN"],
            status=STATUS_ESTIMATED,
        )

        governing = self._select_governing_span(
            centerline_length, clear_span, effective_span, derived
        )

        overall_confidence = min(
            centerline_length.confidence,
            support_face_length.confidence if support_face_length.value else 0.0,
            clear_span.confidence if clear_span.value else centerline_length.confidence,
            effective_span.confidence,
            governing.confidence,
        )

        return BeamLengthModel(
            centerline_length=centerline_length,
            support_face_length=support_face_length,
            bearing_length_left=bearing_left,
            bearing_length_right=bearing_right,
            clear_span=clear_span,
            effective_span=effective_span,
            design_span=design_span,
            governing_span=governing,
            source=SOURCE_FRAMING_PLAN,
            confidence=overall_confidence,
        )

    def _select_governing_span(
        self,
        centerline: EngineeringLength,
        clear_span: EngineeringLength,
        effective_span: EngineeringLength,
        derived_from: List[str],
    ) -> GoverningSpan:
        if clear_span.status == STATUS_KNOWN and clear_span.value is not None:
            return GoverningSpan(
                value=float(clear_span.value),
                unit="mm",
                selected_from=GOVERNING_CLEAR_SPAN,
                confidence=clear_span.confidence,
                derived_from=derived_from,
            )
        if effective_span.status == STATUS_KNOWN and effective_span.value is not None:
            return GoverningSpan(
                value=float(effective_span.value),
                unit="mm",
                selected_from=GOVERNING_EFFECTIVE_SPAN,
                confidence=effective_span.confidence,
                derived_from=derived_from or ["EFFECTIVE_SPAN"],
            )
        return GoverningSpan(
            value=centerline.value,
            unit="mm",
            selected_from=GOVERNING_CENTERLINE,
            confidence=centerline.confidence,
            derived_from=["CENTERLINE"],
        )

    def _update_stats(self, length_model: BeamLengthModel) -> None:
        if length_model.centerline_length.value is not None:
            self._stats["centerline_lengths"] += 1
        if length_model.support_face_length.value is not None:
            self._stats["support_face_lengths"] += 1
        if length_model.clear_span.value is not None:
            self._stats["clear_spans"] += 1
        if length_model.effective_span.value is not None:
            self._stats["effective_spans"] += 1
        if length_model.design_span.value is not None:
            self._stats["design_spans"] += 1

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)
