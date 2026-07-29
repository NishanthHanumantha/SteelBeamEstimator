"""
ReinforcementDetailBuilder — Intent → ReinforcementDetail.
MODEL_VERSION: 8.4.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .continuity_interpreter import ContinuityInterpreter
from .curtailment_engine import CurtailmentEngine
from .detail_confidence_engine import DetailConfidenceEngine
from .detail_consistency_validator import DetailConsistencyValidator
from .development_length_engine import DevelopmentLengthEngine
from .reinforcement_detail_model import ReinforcementDetail
from .side_face_reinforcement_detector import SideFaceReinforcementDetector
from .stirrup_zone_interpreter import StirrupZoneInterpreter
from .support_zone_interpreter import SupportZoneInterpreter

MODEL_VERSION = "8.4.0"


class ReinforcementDetailBuilder:
    """Build ReinforcementDetail objects from EngineeringIntent list."""

    def __init__(self, engineering_context: Optional[Dict[str, Any]] = None):
        self._ctx = engineering_context or {}
        self._stirrup = StirrupZoneInterpreter()
        self._support = SupportZoneInterpreter()
        self._continuity = ContinuityInterpreter()
        self._curtailment = CurtailmentEngine()
        self._dev = DevelopmentLengthEngine(self._ctx)
        self._side = SideFaceReinforcementDetector()
        self._consistency = DetailConsistencyValidator()
        self._confidence = DetailConfidenceEngine()

    def build_for_beams(
        self,
        intents_by_beam: Dict[str, List[Any]],
        geometry_by_beam: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Tuple[List[ReinforcementDetail], Dict[str, Any]]:
        geometry_by_beam = geometry_by_beam or {}
        details: List[ReinforcementDetail] = []
        stirrup_segments_export: List[Dict[str, Any]] = []
        seq = 0

        for beam_id in sorted(intents_by_beam.keys()):
            intents = intents_by_beam[beam_id]
            geo = geometry_by_beam.get(beam_id) or {}
            span = float(geo.get("clear_span_mm") or 0)
            depth = float(geo.get("depth_mm") or 750)
            width = float(geo.get("width_mm") or 300)

            stirrups = [i for i in intents if str(getattr(i, "role", "")) == "STIRRUP"]
            stir_map = self._stirrup.interpret_beam(
                beam_id, stirrups, span, depth, width
            )

            for it in intents:
                seq += 1
                detail = self._build_one(
                    seq, it, span, depth, stir_map.get(it.intent_id) or {}
                )
                details.append(detail)
                for seg in detail.stirrup_segments:
                    stirrup_segments_export.append({
                        "detail_id": detail.detail_id,
                        "intent_id": detail.intent_id,
                        "beam_id": beam_id,
                        **seg,
                    })

        consistency = self._consistency.validate(details)
        for d in details:
            # re-score after flags
            self._confidence.apply(
                d,
                {
                    "intent": d.intent_confidence,
                    "support": 0.7,
                    "continuity": 0.7,
                    "curtailment": 0.7,
                    "development": 0.85 if d.development_length_mm else 0.3,
                    "stirrup": 0.85 if d.stirrup_zone_count else 0.7,
                    "side_face": 0.8,
                },
            )

        payload = {
            "model_version": MODEL_VERSION,
            "detail_count": len(details),
            "beam_count": len(intents_by_beam),
            "consistency": consistency,
            "confidence": self._confidence.distribution(details),
            "stirrup_segments": stirrup_segments_export,
        }
        return details, payload

    def _build_one(
        self,
        seq: int,
        intent: Any,
        span: float,
        depth: float,
        stir_info: Dict[str, Any],
    ) -> ReinforcementDetail:
        support = self._support.interpret(intent, span)
        continuity = self._continuity.interpret(intent, support)
        curtailment = self._curtailment.interpret(intent, support)
        ld = self._dev.compute(intent)
        side = self._side.detect(intent, depth)

        evidence: List[str] = []
        evidence.extend(support.get("evidence") or [])
        evidence.extend(continuity.get("evidence") or [])
        evidence.extend(curtailment.get("evidence") or [])
        evidence.extend(ld.get("evidence") or [])
        evidence.extend(side.get("evidence") or [])
        evidence.extend(stir_info.get("evidence") or [])

        notes: List[str] = []
        if ld.get("flagged"):
            notes.append("development_length_unavailable")
        if continuity.get("continuity") == "UNKNOWN":
            notes.append("continuity_unresolved")

        segs = list(stir_info.get("segments") or [])
        # Prefer beam-level full segmentation on one representative? Store assigned segs.
        if stir_info.get("all_beam_segments") and str(getattr(intent, "role", "")) == "STIRRUP":
            # Keep all beam segments on each stirrup detail for zone export clarity
            # but spacing_mm remains this intent's spacing
            pass

        detail = ReinforcementDetail(
            detail_id=f"DET::{intent.beam_id}::{seq:04d}",
            beam_id=str(intent.beam_id),
            intent_id=str(intent.intent_id),
            role=str(intent.role),
            diameter_mm=float(intent.diameter_mm),
            quantity=int(intent.quantity),
            layer=str(getattr(intent, "layer", "") or ""),
            bar_label=str(getattr(intent, "bar_label", "") or ""),
            zone=str(getattr(intent, "zone", "") or ""),
            extent=str(getattr(intent, "extent", "") or "UNKNOWN"),
            continuity=str(continuity.get("continuity") or "UNKNOWN"),
            support_type=str(getattr(intent, "support_type", "") or "UNKNOWN"),
            development_length_mm=ld.get("development_length_mm"),
            lap_length_mm=ld.get("lap_length_mm"),
            hook_type=str(ld.get("hook_type") or "UNKNOWN"),
            anchor_type=str(ld.get("anchor_type") or "UNKNOWN"),
            left_support_zone=bool(support.get("left_support_zone")),
            mid_zone=bool(support.get("mid_zone")),
            right_support_zone=bool(support.get("right_support_zone")),
            start_offset_mm=curtailment.get("start_offset_mm"),
            end_offset_mm=curtailment.get("end_offset_mm"),
            spacing_mm=stir_info.get("spacing_mm", getattr(intent, "spacing_mm", None)),
            spacing_pattern=str(stir_info.get("spacing_pattern") or ""),
            stirrup_zone_count=int(stir_info.get("zone_count") or 0),
            stirrup_segments=segs,
            curtailment_type=str(curtailment.get("curtailment_type") or "UNKNOWN"),
            side_face=bool(side.get("side_face")),
            engineering_notes=notes,
            evidence=evidence,
            source_phase="R.1.2D",
            development_rule=str(ld.get("development_rule") or ""),
            development_source=str(ld.get("development_source") or ""),
            support_region=str(support.get("support_region") or "UNKNOWN"),
            intent_confidence=float(getattr(intent, "intent_confidence", 0) or 0),
        )
        self._confidence.apply(
            detail,
            {
                "intent": detail.intent_confidence,
                "support": float(support.get("confidence") or 0.5),
                "continuity": float(continuity.get("confidence") or 0.5),
                "curtailment": float(curtailment.get("confidence") or 0.5),
                "development": float(ld.get("confidence") or 0.5),
                "stirrup": float(stir_info.get("confidence") or 0.7),
                "side_face": float(side.get("confidence") or 0.7),
            },
        )
        return detail
