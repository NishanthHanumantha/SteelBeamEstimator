"""
Equal zone builder: Zone Length = Beam Length / N
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

from typing import List, Sequence

from quantity_engine import QuantityEngine
from stirrup_model import StirrupZone

MODEL_VERSION = "8.8.1"


class ZoneBuilder:
    def __init__(self):
        self._qty = QuantityEngine()

    def build(
        self,
        beam_length_mm: float,
        spacing_values_mm: Sequence[int],
    ) -> List[StirrupZone]:
        if beam_length_mm <= 0:
            raise ValueError("beam_length_mm must be > 0")
        n = len(spacing_values_mm)
        if n <= 0:
            raise ValueError("spacing_values_mm must be non-empty")

        zone_length = beam_length_mm / float(n)
        zones: List[StirrupZone] = []
        for i, spacing in enumerate(spacing_values_mm):
            start = i * zone_length
            end = (i + 1) * zone_length
            qty = self._qty.zone_quantity(zone_length, spacing)
            zones.append(StirrupZone(
                zone_index=i + 1,
                zone_name=f"Zone_{i + 1}",
                start_mm=round(start, 3),
                end_mm=round(end, 3),
                length_mm=round(zone_length, 3),
                spacing_mm=int(spacing),
                quantity=qty,
            ))
        return zones
