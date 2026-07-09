"""Local engineering coordinate system per beam."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EngineeringCoordinateSystem:
    """Local beam coordinate system anchored at start support."""

    beam_id: str
    origin: str
    x_axis: str
    station_start: float
    station_end: float
    direction: str
    global_origin: dict[str, float]
    global_end: dict[str, float]
    unit_vector: dict[str, float]
    governing_span_mm: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "beam_id": self.beam_id,
            "local_coordinate_system": {
                "origin": self.origin,
                "x_axis": self.x_axis,
                "station_start": round(self.station_start, 3),
                "station_end": round(self.station_end, 3),
                "direction": self.direction,
            },
            "global_coordinates": {
                "origin": self.global_origin,
                "end": self.global_end,
                "unit_vector": self.unit_vector,
            },
            "governing_span_mm": round(self.governing_span_mm, 3),
        }


class EngineeringCoordinateSystemBuilder:
    """Build local coordinate systems from beam geometry and length model."""

    def build_for_beam(self, beam: dict[str, Any]) -> EngineeringCoordinateSystem:
        geometry = beam.get("geometry", {})
        centerline = geometry.get("centerline") or {}
        start = centerline.get("start_point", {})
        end = centerline.get("end_point", {})

        ox = float(start.get("x", 0.0))
        oy = float(start.get("y", 0.0))
        ex = float(end.get("x", 0.0))
        ey = float(end.get("y", 0.0))

        dx, dy = ex - ox, ey - oy
        length = math.hypot(dx, dy)
        if length == 0:
            ux, uy = 1.0, 0.0
        else:
            ux, uy = dx / length, dy / length

        lm = beam.get("length_model", {})
        governing = lm.get("governing_span", {})
        station_end = float(governing.get("value") or lm.get("centerline_length", {}).get("value") or length)

        return EngineeringCoordinateSystem(
            beam_id=beam["beam_id"],
            origin="START_SUPPORT",
            x_axis="ALONG_BEAM",
            station_start=0.0,
            station_end=station_end,
            direction="START_TO_END",
            global_origin={"x": round(ox, 3), "y": round(oy, 3)},
            global_end={"x": round(ex, 3), "y": round(ey, 3)},
            unit_vector={"x": round(ux, 6), "y": round(uy, 6)},
            governing_span_mm=station_end,
        )

    def build_all(self, beams: List[dict[str, Any]]) -> Dict[str, EngineeringCoordinateSystem]:
        return {beam["beam_id"]: self.build_for_beam(beam) for beam in beams}
