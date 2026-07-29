"""Station conversion along beam local axis."""

from __future__ import annotations

import math
from typing import Any, Optional, Tuple


class StationService:
    """Station ↔ global coordinate conversions using beam station API."""

    def station_to_global(
        self,
        station_api: dict[str, Any],
        station_mm: float,
    ) -> Tuple[float, float]:
        origin = station_api.get("origin") or {}
        unit = station_api.get("unit_vector") or {}
        ox = float(origin.get("x", 0.0))
        oy = float(origin.get("y", 0.0))
        ux = float(unit.get("x", 1.0))
        uy = float(unit.get("y", 0.0))
        span = float(station_api.get("span_mm") or 0.0)
        t = max(0.0, min(span, station_mm))
        return ox + ux * t, oy + uy * t

    def global_to_station(
        self,
        station_api: dict[str, Any],
        x: float,
        y: float,
    ) -> float:
        origin = station_api.get("origin") or {}
        unit = station_api.get("unit_vector") or {}
        ox = float(origin.get("x", 0.0))
        oy = float(origin.get("y", 0.0))
        ux = float(unit.get("x", 1.0))
        uy = float(unit.get("y", 0.0))
        return (x - ox) * ux + (y - oy) * uy

    def station_fraction(self, station_api: dict[str, Any], station_mm: float) -> Optional[float]:
        span = float(station_api.get("span_mm") or 0.0)
        if span <= 0:
            return None
        return max(0.0, min(1.0, station_mm / span))

    def to_registry_entry(self) -> dict[str, Any]:
        return {
            "service_id": "station",
            "description": "Beam stationing and coordinate conversion",
            "rule_reference": None,
            "status": "READY",
        }
