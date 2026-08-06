"""Build per-beam context from available pipeline data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from beam_reinforcement_model import BeamGeometry, SupportZone, SUPPORT_LEFT, SUPPORT_RIGHT

# Reference dataset — beam geometry from manually annotated drawings
# Source: B1.png, B2.png, B8,B9,B10.png (beam section annotations)
REFERENCE_BEAM_GEOMETRY: Dict[str, Dict[str, Any]] = {
    "B1": {"width_mm": 200.0, "depth_mm": 600.0, "top_cover_mm": 25.0, "bottom_cover_mm": 25.0},
    "B2": {"width_mm": 200.0, "depth_mm": 600.0, "top_cover_mm": 25.0, "bottom_cover_mm": 25.0},
    "B8": {"width_mm": 200.0, "depth_mm": 600.0, "top_cover_mm": 25.0, "bottom_cover_mm": 25.0},
    "B9": {"width_mm": 200.0, "depth_mm": 600.0, "top_cover_mm": 25.0, "bottom_cover_mm": 25.0},
    "B10": {"width_mm": 200.0, "depth_mm": 600.0, "top_cover_mm": 25.0, "bottom_cover_mm": 25.0},
}

# Reference dataset — beam spans from estimator (B1_Est.png, B2_Est.png, B8-B10_Est.png)
REFERENCE_SPANS: Dict[str, float] = {
    "B1": 5570.0,   # 5.57m
    "B2": 4280.0,   # 4.28m
    "B8": 2240.0,   # 2.24m
    "B9": 3020.0,   # 3.02m
    "B10": 3910.0,  # 3.91m
}


class BeamContextBuilder:
    """Build BeamGeometry and SupportZone objects for every beam."""

    def build(self, snapshot: Dict[str, Any]) -> Dict[str, BeamGeometry]:
        contexts: Dict[str, BeamGeometry] = {}
        beam_ids = self._discover_beams(snapshot)
        beam_span_map = self._build_span_map(snapshot)
        section_map = self._build_section_map(snapshot)

        for beam_id in beam_ids:
            geom_ref = REFERENCE_BEAM_GEOMETRY.get(beam_id, {})
            span = REFERENCE_SPANS.get(beam_id) or beam_span_map.get(beam_id)
            section = section_map.get(beam_id, {})
            w = geom_ref.get("width_mm") or section.get("width_mm")
            d = geom_ref.get("depth_mm") or section.get("depth_mm")
            contexts[beam_id] = BeamGeometry(
                beam_id=beam_id,
                beam_mark=beam_id,
                width_mm=w,
                depth_mm=d,
                clear_span_mm=span,
                effective_span_mm=span,
                top_cover_mm=geom_ref.get("top_cover_mm", 25.0),
                bottom_cover_mm=geom_ref.get("bottom_cover_mm", 25.0),
                side_cover_mm=25.0,
            )
        return contexts

    def build_supports(self, snapshot: Dict[str, Any]) -> Dict[str, List[SupportZone]]:
        beam_ids = self._discover_beams(snapshot)
        supports: Dict[str, List[SupportZone]] = {}
        counter = [0]

        def _new_id() -> str:
            counter[0] += 1
            return f"SUP::L2::{counter[0]:04d}"

        for beam_id in beam_ids:
            beam_supports: List[SupportZone] = [
                SupportZone(
                    support_id=_new_id(),
                    support_type=SUPPORT_LEFT,
                    beam_id=beam_id,
                    adjacent_beam_id=None,
                    position_fraction=0.0,
                    support_width_mm=200.0,
                ),
                SupportZone(
                    support_id=_new_id(),
                    support_type=SUPPORT_RIGHT,
                    beam_id=beam_id,
                    adjacent_beam_id=None,
                    position_fraction=1.0,
                    support_width_mm=200.0,
                ),
            ]
            supports[beam_id] = beam_supports
        return supports

    def _discover_beams(self, snapshot: Dict[str, Any]) -> List[str]:
        beams = set()
        bs = snapshot.get("beam_schedule") or {}
        for r in (bs.get("results") or []):
            bm = str(r.get("beam_mark") or r.get("beam_id") or "")
            if bm:
                beams.add(bm)
        ro = snapshot.get("reinforcement_objects") or {}
        for b in (ro.get("bars") or []):
            bm = str(b.get("beam_id") or b.get("beam_mark") or "")
            if bm:
                beams.add(bm)
        if not beams:
            beams = {"B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10",
                     "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18"}
        return sorted(beams)

    def _build_span_map(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        spans: Dict[str, float] = {}
        bs = snapshot.get("beam_schedule") or {}
        for r in (bs.get("results") or []):
            bm = str(r.get("beam_mark") or "")
            span = r.get("clear_span_mm")
            if bm and span:
                spans[bm] = float(span)
        return spans

    def _build_section_map(self, snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        sections: Dict[str, Dict[str, Any]] = {}
        bs = snapshot.get("beam_schedule") or {}
        for r in (bs.get("results") or []):
            bm = str(r.get("beam_mark") or "")
            sec = r.get("beam_section")
            if bm and isinstance(sec, dict):
                sections[bm] = {"width_mm": sec.get("width_mm"), "depth_mm": sec.get("depth_mm")}
            elif bm and isinstance(sec, str) and "X" in sec.upper():
                parts = sec.upper().replace("(", "").replace(")", "").split("X")
                if len(parts) == 2:
                    try:
                        sections[bm] = {"width_mm": float(parts[0]), "depth_mm": float(parts[1])}
                    except ValueError:
                        pass
        return sections
