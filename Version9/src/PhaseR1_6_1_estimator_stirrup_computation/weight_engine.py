"""
Weight engine — IS unit weights.
MODEL_VERSION: 8.8.1

Total Length = Cut Length × Quantity
Weight = Total Length(m) × unit weight
"""
from __future__ import annotations

from typing import Tuple

from stirrup_model import IS_UNIT_WEIGHT_KG_PER_M

MODEL_VERSION = "8.8.1"


class WeightEngine:
    def unit_weight(self, diameter_mm: float) -> float:
        d = int(round(diameter_mm))
        if d not in IS_UNIT_WEIGHT_KG_PER_M:
            raise ValueError(f"No IS unit weight for diameter {d} mm")
        return IS_UNIT_WEIGHT_KG_PER_M[d]

    def compute(
        self,
        cut_length_mm: float,
        quantity: int,
        diameter_mm: float,
    ) -> Tuple[float, float, float]:
        """Return (total_length_m, unit_weight, weight_kg)."""
        if cut_length_mm <= 0 or quantity < 0:
            raise ValueError("invalid cut_length/quantity")
        uw = self.unit_weight(diameter_mm)
        total_m = (cut_length_mm / 1000.0) * float(quantity)
        weight = total_m * uw
        return round(total_m, 6), uw, round(weight, 4)
