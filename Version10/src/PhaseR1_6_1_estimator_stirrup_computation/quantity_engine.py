"""
Quantity engine — estimator formulas.
MODEL_VERSION: 8.8.1

Uniform:  (Beam Length / Spacing) + 1
Variable: sum over zones of (Zone Length / Zone Spacing) + 1
"""
from __future__ import annotations

from typing import List, Sequence

from stirrup_model import StirrupZone

MODEL_VERSION = "8.8.1"


class QuantityEngine:
    def zone_quantity(self, length_mm: float, spacing_mm: float) -> int:
        if spacing_mm <= 0:
            raise ValueError("spacing_mm must be > 0")
        if length_mm <= 0:
            return 0
        # Deterministic integer formula matching estimator examples
        return int(length_mm // spacing_mm) + 1

    def uniform_quantity(self, beam_length_mm: float, spacing_mm: float) -> int:
        return self.zone_quantity(beam_length_mm, spacing_mm)

    def total_from_zones(self, zones: Sequence[StirrupZone]) -> int:
        return sum(z.quantity for z in zones)
