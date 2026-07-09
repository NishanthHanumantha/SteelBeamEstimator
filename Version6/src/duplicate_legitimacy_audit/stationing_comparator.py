"""Compare beam station and engineering location across duplicate members."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.duplicate_legitimacy_audit.duplicate_group_loader import STATION_TOLERANCE_MM


class StationingComparator:
    """Compare duplicate members by beam station and coordinate span."""

    def analyze(self, contexts: List[dict[str, Any]]) -> dict[str, Any]:
        stations = [item.get("beam_station") for item in contexts if item.get("beam_station") is not None]
        supports = [str(item.get("support") or "UNKNOWN") for item in contexts]
        coordinates = [item.get("coordinate") or {} for item in contexts]
        x_values = [float(item.get("x")) for item in coordinates if item.get("x") is not None]
        y_values = [float(item.get("y")) for item in coordinates if item.get("y") is not None]
        station_spread = self._spread(stations)
        x_spread = self._spread(x_values)
        y_spread = self._spread(y_values)
        unique_supports = sorted(set(supports))
        return {
            "stations": stations,
            "station_spread": station_spread,
            "station_variant": station_spread is not None and station_spread > STATION_TOLERANCE_MM,
            "x_spread": x_spread,
            "y_spread": y_spread,
            "span_variant": y_spread is not None and y_spread > STATION_TOLERANCE_MM,
            "supports": supports,
            "unique_supports": unique_supports,
            "support_variant": len(unique_supports) > 1,
        }

    @staticmethod
    def _spread(values: List[Any]) -> Optional[float]:
        numeric = [float(value) for value in values if value is not None]
        if len(numeric) < 2:
            return 0.0
        return round(max(numeric) - min(numeric), 3)
