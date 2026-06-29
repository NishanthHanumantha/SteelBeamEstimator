"""Beam stationing model and station ↔ global conversion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.framing.engineering_coordinate_system import EngineeringCoordinateSystem


@dataclass
class StationPoint:
    station_mm: float
    fraction: float
    label: str
    global_x: float
    global_y: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "station_mm": round(self.station_mm, 3),
            "fraction": round(self.fraction, 4),
            "label": self.label,
            "global": {"x": round(self.global_x, 3), "y": round(self.global_y, 3)},
        }


class BeamStationing:
    """Station-based positioning along a beam local axis."""

    DEFAULT_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
    DEFAULT_LABELS = ("START", "0.25L", "0.50L", "0.75L", "END")

    def __init__(self, ecs: EngineeringCoordinateSystem) -> None:
        self._ecs = ecs
        self._span = ecs.station_end
        self._ox = ecs.global_origin["x"]
        self._oy = ecs.global_origin["y"]
        self._ux = ecs.unit_vector["x"]
        self._uy = ecs.unit_vector["y"]

    @property
    def span_mm(self) -> float:
        return self._span

    def station_fraction(self, station_mm: float) -> Optional[float]:
        if self._span <= 0:
            return None
        return max(0.0, min(1.0, station_mm / self._span))

    def station_to_global(self, station_mm: float) -> Tuple[float, float]:
        t = max(0.0, min(self._span, station_mm))
        return (
            self._ox + self._ux * t,
            self._oy + self._uy * t,
        )

    def global_to_station(self, x: float, y: float) -> float:
        return (x - self._ox) * self._ux + (y - self._oy) * self._uy

    def build_station_model(self) -> dict[str, Any]:
        stations: List[StationPoint] = []
        for frac, label in zip(self.DEFAULT_FRACTIONS, self.DEFAULT_LABELS):
            station_mm = self._span * frac
            gx, gy = self.station_to_global(station_mm)
            stations.append(
                StationPoint(
                    station_mm=station_mm,
                    fraction=frac,
                    label=label,
                    global_x=gx,
                    global_y=gy,
                )
            )
        return {
            "beam_id": self._ecs.beam_id,
            "station_start": 0.0,
            "station_end": round(self._span, 3),
            "coordinate_system_id": f"ECS_{self._ecs.beam_id}",
            "stations": [s.to_dict() for s in stations],
        }


def station_to_global(beam: dict[str, Any], station_mm: float) -> Tuple[float, float]:
    """Convert station (mm along beam) to global coordinates."""
    from src.framing.engineering_coordinate_system import EngineeringCoordinateSystemBuilder

    ecs = EngineeringCoordinateSystemBuilder().build_for_beam(beam)
    return BeamStationing(ecs).station_to_global(station_mm)


def global_to_station(beam: dict[str, Any], x: float, y: float) -> float:
    """Convert global coordinates to station along beam."""
    from src.framing.engineering_coordinate_system import EngineeringCoordinateSystemBuilder

    ecs = EngineeringCoordinateSystemBuilder().build_for_beam(beam)
    return BeamStationing(ecs).global_to_station(x, y)


def station_fraction(beam: dict[str, Any], station_mm: float) -> Optional[float]:
    """Return L-fraction for a station value."""
    from src.framing.engineering_coordinate_system import EngineeringCoordinateSystemBuilder

    ecs = EngineeringCoordinateSystemBuilder().build_for_beam(beam)
    return BeamStationing(ecs).station_fraction(station_mm)
