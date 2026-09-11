"""
Piece generator — ReinforcementDetail → ReinforcementPiece(s).
MODEL_VERSION: 8.5.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .piece_geometry import PieceGeometry
from .piece_model import (
    ANCHOR_BAR,
    BOTTOM_EXTRA_LEFT,
    BOTTOM_EXTRA_RIGHT,
    BOTTOM_MAIN,
    CONTINUOUS_BAR,
    CURTAILED_BAR,
    FAB_HOOKED,
    FAB_SPACER,
    FAB_STIRRUP,
    FAB_STRAIGHT,
    FAB_UNKNOWN,
    SIDE_FACE,
    SPACER,
    STIRRUP_ZONE_A,
    STIRRUP_ZONE_B,
    STIRRUP_ZONE_C,
    SUPPORT_BAR,
    TOP_EXTRA_LEFT,
    TOP_EXTRA_RIGHT,
    TOP_MAIN,
    UNKNOWN_PIECE,
    ReinforcementPiece,
)
from .piece_quantity import PieceQuantity

MODEL_VERSION = "8.5.0"

_ZONE_PIECE = {
    "Zone_A": STIRRUP_ZONE_A,
    "ZONE_A": STIRRUP_ZONE_A,
    "Zone_B": STIRRUP_ZONE_B,
    "ZONE_B": STIRRUP_ZONE_B,
    "Zone_C": STIRRUP_ZONE_C,
    "ZONE_C": STIRRUP_ZONE_C,
}


class PieceGenerator:
    """Deterministic Detail → Piece expansion. Never fabricates unknown facts."""

    def __init__(self, engineering_context: Optional[Dict[str, Any]] = None):
        self._ctx = engineering_context or {}
        self._geo = PieceGeometry()
        self._qty = PieceQuantity()
        self._seq = 0

    def generate_for_details(
        self,
        details: List[Any],
        geometry_by_beam: Dict[str, Dict[str, Any]],
    ) -> List[ReinforcementPiece]:
        pieces: List[ReinforcementPiece] = []
        for det in details:
            geo = geometry_by_beam.get(str(det.beam_id)) or {}
            pieces.extend(self.generate_from_detail(det, geo))
        return pieces

    def generate_from_detail(
        self, detail: Any, geometry: Dict[str, Any]
    ) -> List[ReinforcementPiece]:
        role = str(getattr(detail, "role", "") or "")
        if role == "STIRRUP":
            return self._expand_stirrup(detail, geometry)
        curtail = str(getattr(detail, "curtailment_type", "") or "UNKNOWN")
        support = str(getattr(detail, "support_region", "") or "UNKNOWN")
        if curtail in ("BOTH_SUPPORTS",) or (
            support == "BOTH_SUPPORTS" and role in ("TOP_EXTRA", "BOTTOM_EXTRA")
        ):
            return self._expand_both_supports(detail, geometry)
        return [self._single_piece(detail, geometry)]

    def _expand_stirrup(
        self, detail: Any, geometry: Dict[str, Any]
    ) -> List[ReinforcementPiece]:
        segs = list(getattr(detail, "stirrup_segments", None) or [])
        if not segs:
            # Single unknown/full stirrup piece — do not invent zones
            return [self._make_piece(
                detail, geometry,
                piece_type=STIRRUP_ZONE_A if getattr(detail, "spacing_mm", None) else UNKNOWN_PIECE,
                fabrication_type=FAB_STIRRUP,
                zone="STIRRUP",
                start=None, end=None,
                quantity=self._qty.from_detail(detail),
                spacing=getattr(detail, "spacing_mm", None),
                evidence=("stirrup_no_segments_single_piece",),
            )]
        # Prefer unique zone segments; if detail only has matching spacing subset,
        # expand those; if all_beam pattern stored only matching — use what's on detail.
        pieces = []
        seen = set()
        for seg in segs:
            zname = str(seg.get("zone_name") or "Zone_A")
            ptype = _ZONE_PIECE.get(zname, STIRRUP_ZONE_A)
            key = (zname, seg.get("spacing_mm"), seg.get("start_mm"), seg.get("end_mm"))
            if key in seen:
                continue
            seen.add(key)
            pieces.append(self._make_piece(
                detail, geometry,
                piece_type=ptype,
                fabrication_type=FAB_STIRRUP,
                zone=zname,
                start=seg.get("start_mm"),
                end=seg.get("end_mm"),
                quantity=self._qty.from_segment(seg, self._qty.from_detail(detail)),
                spacing=seg.get("spacing_mm", getattr(detail, "spacing_mm", None)),
                evidence=(
                    f"stirrup_zone={zname}",
                    f"spacing={seg.get('spacing_mm')}",
                    "expanded_from_detail_segments",
                ),
                estimated_weight=seg.get("weight_kg"),
            ))
        return pieces or [self._single_piece(detail, geometry)]

    def _expand_both_supports(
        self, detail: Any, geometry: Dict[str, Any]
    ) -> List[ReinforcementPiece]:
        role = str(detail.role)
        if role == "TOP_EXTRA":
            left_t, right_t = TOP_EXTRA_LEFT, TOP_EXTRA_RIGHT
        elif role == "BOTTOM_EXTRA":
            left_t, right_t = BOTTOM_EXTRA_LEFT, BOTTOM_EXTRA_RIGHT
        else:
            left_t = right_t = SUPPORT_BAR

        span = geometry.get("clear_span_mm")
        left_end = float(span) * 0.25 if span else None
        right_start = float(span) * 0.75 if span else None
        span_f = float(span) if span else None

        return [
            self._make_piece(
                detail, geometry,
                piece_type=left_t,
                fabrication_type=FAB_HOOKED,
                zone="LEFT_SUPPORT",
                start=0.0 if span_f is not None else None,
                end=left_end,
                quantity=self._qty.from_detail(detail),
                evidence=("both_supports_left_piece", "0.25L_when_span_known"),
            ),
            self._make_piece(
                detail, geometry,
                piece_type=right_t,
                fabrication_type=FAB_HOOKED,
                zone="RIGHT_SUPPORT",
                start=right_start,
                end=span_f,
                quantity=self._qty.from_detail(detail),
                evidence=("both_supports_right_piece", "0.75L_when_span_known"),
            ),
        ]

    def _single_piece(self, detail: Any, geometry: Dict[str, Any]) -> ReinforcementPiece:
        role = str(detail.role)
        curtail = str(getattr(detail, "curtailment_type", "") or "UNKNOWN")
        continuity = str(getattr(detail, "continuity", "") or "UNKNOWN")
        side = bool(getattr(detail, "side_face", False))

        if side or role == "SIDE_FACE_REINFORCEMENT":
            ptype, fab = SIDE_FACE, FAB_STRAIGHT
        elif role == "SPACER_BAR":
            ptype, fab = SPACER, FAB_SPACER
        elif role == "TOP_MAIN":
            ptype, fab = TOP_MAIN, FAB_STRAIGHT
        elif role == "BOTTOM_MAIN":
            ptype, fab = BOTTOM_MAIN, FAB_STRAIGHT
        elif continuity == "CONTINUOUS" or curtail == "FULL_SPAN":
            ptype, fab = CONTINUOUS_BAR, FAB_STRAIGHT
        elif curtail in ("LEFT_SUPPORT",):
            ptype = TOP_EXTRA_LEFT if "TOP" in role else BOTTOM_EXTRA_LEFT
            fab = FAB_HOOKED
        elif curtail in ("RIGHT_SUPPORT",):
            ptype = TOP_EXTRA_RIGHT if "TOP" in role else BOTTOM_EXTRA_RIGHT
            fab = FAB_HOOKED
        elif curtail in ("CURTAILED", "MID_SPAN"):
            ptype, fab = CURTAILED_BAR, FAB_HOOKED
        elif role in ("TOP_EXTRA", "BOTTOM_EXTRA"):
            ptype, fab = SUPPORT_BAR, FAB_HOOKED
        elif curtail == "UNKNOWN" and continuity == "UNKNOWN":
            ptype, fab = UNKNOWN_PIECE, FAB_UNKNOWN
        else:
            ptype, fab = CURTAILED_BAR if "EXTRA" in role else CONTINUOUS_BAR, FAB_STRAIGHT

        span = geometry.get("clear_span_mm")
        start = end = None
        if span and ptype in (TOP_MAIN, BOTTOM_MAIN, CONTINUOUS_BAR):
            start, end = 0.0, float(span)
        elif span and ptype in (TOP_EXTRA_LEFT, BOTTOM_EXTRA_LEFT):
            start, end = 0.0, float(span) * 0.25
        elif span and ptype in (TOP_EXTRA_RIGHT, BOTTOM_EXTRA_RIGHT):
            start, end = float(span) * 0.75, float(span)

        return self._make_piece(
            detail, geometry,
            piece_type=ptype,
            fabrication_type=fab,
            zone=str(getattr(detail, "zone", "") or ""),
            start=start,
            end=end,
            quantity=self._qty.from_detail(detail),
            evidence=(f"piece_type={ptype}", f"curtailment={curtail}", f"role={role}"),
        )

    def _make_piece(
        self,
        detail: Any,
        geometry: Dict[str, Any],
        *,
        piece_type: str,
        fabrication_type: str,
        zone: str,
        start: Optional[float],
        end: Optional[float],
        quantity: int,
        evidence: Tuple[str, ...] = (),
        spacing: Optional[float] = None,
        estimated_weight: Optional[float] = None,
    ) -> ReinforcementPiece:
        self._seq += 1
        span = geometry.get("clear_span_mm")
        depth = geometry.get("depth_mm")
        width = geometry.get("width_mm")
        hook_mult = self._ctx.get("hook_multiple_135") or self._ctx.get("hook_multiple")
        dia = float(getattr(detail, "diameter_mm", 0) or 0)
        ld = getattr(detail, "development_length_mm", None)

        cut, geo_ev, geo_flags = self._geo.cut_length(
            span_mm=float(span) if span is not None else None,
            development_length_mm=ld,
            hook_multiple=float(hook_mult) if hook_mult is not None else None,
            diameter_mm=dia,
            piece_start_mm=start,
            piece_end_mm=end,
            fabrication_type=fabrication_type,
            role=str(detail.role),
            depth_mm=float(depth) if depth is not None else None,
            width_mm=float(width) if width is not None else None,
        )
        weight = estimated_weight
        if weight is None:
            weight = self._geo.weight_kg(dia, cut, quantity)

        shape = self._shape_code(piece_type, fabrication_type)
        flags = list(geo_flags) + list(getattr(detail, "validation_flags", None) or [])
        if cut is None:
            flags.append("cut_length_unavailable")

        all_evidence = tuple(evidence) + tuple(geo_ev) + (
            f"detail_id={detail.detail_id}",
            f"intent_id={detail.intent_id}",
        )

        # Confidence: blend detail confidence with geometry availability
        dconf = float(getattr(detail, "confidence", 0) or 0.5)
        gconf = 0.9 if cut is not None else 0.4
        conf = round(0.6 * dconf + 0.4 * gconf, 4)

        return ReinforcementPiece(
            piece_id=f"PCE::{detail.beam_id}::{self._seq:04d}",
            detail_id=str(detail.detail_id),
            intent_id=str(detail.intent_id),
            beam_id=str(detail.beam_id),
            role=str(detail.role),
            layer=str(getattr(detail, "layer", "") or ""),
            diameter_mm=dia,
            quantity=int(quantity),
            piece_type=piece_type,
            fabrication_type=fabrication_type,
            cut_length_mm=cut,
            development_length_mm=ld,
            lap_length_mm=getattr(detail, "lap_length_mm", None),
            hook_type=str(getattr(detail, "hook_type", "") or "UNKNOWN"),
            anchor_type=str(getattr(detail, "anchor_type", "") or "UNKNOWN"),
            continuity=str(getattr(detail, "continuity", "") or "UNKNOWN"),
            curtailment=str(getattr(detail, "curtailment_type", "") or "UNKNOWN"),
            support_region=str(getattr(detail, "support_region", "") or "UNKNOWN"),
            zone=zone,
            piece_start_mm=start,
            piece_end_mm=end,
            shape_code=shape,
            estimated_weight_kg=weight,
            confidence=conf,
            evidence=all_evidence,
            validation_flags=tuple(flags),
            source_phase="R.1.3",
            bar_label=str(getattr(detail, "bar_label", "") or ""),
            spacing_mm=spacing if spacing is not None else getattr(detail, "spacing_mm", None),
            spacing_pattern=str(getattr(detail, "spacing_pattern", "") or ""),
            detail_confidence=dconf,
            annotation_ids=tuple(),
            geometry_ids=(f"GEO::{detail.beam_id}",) if span else tuple(),
            relationship_ids=tuple(),
            fact_ids=tuple(),
        )

    @staticmethod
    def _shape_code(piece_type: str, fabrication_type: str) -> str:
        if fabrication_type == FAB_STIRRUP:
            return "SHAPE_STIRRUP_CLOSED"
        if fabrication_type == FAB_SPACER:
            return "SHAPE_SPACER"
        if piece_type in (TOP_EXTRA_LEFT, BOTTOM_EXTRA_LEFT, TOP_EXTRA_RIGHT, BOTTOM_EXTRA_RIGHT):
            return "SHAPE_SUPPORT_EXTRA"
        if fabrication_type == FAB_HOOKED:
            return "SHAPE_HOOKED"
        if fabrication_type == FAB_STRAIGHT:
            return "SHAPE_STRAIGHT"
        return "SHAPE_UNKNOWN"
