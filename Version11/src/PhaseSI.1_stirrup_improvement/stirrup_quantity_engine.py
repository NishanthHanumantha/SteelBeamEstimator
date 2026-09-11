"""
Stirrup Quantity Engine — Phase SI.1 MODULE 4

Calculates stirrup count per zone group (deterministic, no interpolation).

Formulas (calibrated to estimator reference workbook):

  UNIFORM (single zone):
    N = floor(span / spacing) + 1

  VARIABLE — merged support zones (left + right, same spacing):
    N = floor(total_support_length / spacing) + 1
    where total_support_length = left_zone_length + right_zone_length

  VARIABLE — single midspan zone:
    N = floor(zone_length / spacing)

Verification (B2: 2L-Y8@100/200/100, span=4280mm):
  zone = 4280/3 = 1426.7mm
  Support merged: floor(2×1426.7/100)+1 = floor(28.53)+1 = 29 ✓
  Middle:         floor(1426.7/200)      = floor(7.13)   = 7  ✓
  Total = 36 ✓
"""
import math
from typing import List

from stirrup_models import StirrupZone, ZoneRole, StirrupType


class StirrupQuantityEngine:
    """
    Computes stirrup quantity for one zone-group (i.e., one BBS row).
    """

    def calculate(
        self,
        zones: List[StirrupZone],
        stirrup_type: StirrupType,
        span_mm: float,
    ) -> int:
        """
        Returns the stirrup count for this group of zones.
        """
        if not zones:
            return 0

        spacing = zones[0].spacing_mm
        total_length = sum(z.length_mm for z in zones)

        roles = {z.role for z in zones}
        has_support = ZoneRole.LEFT_SUPPORT in roles or ZoneRole.RIGHT_SUPPORT in roles
        all_midspan = all(z.role == ZoneRole.MIDSPAN for z in zones)

        if stirrup_type == StirrupType.UNIFORM:
            # One zone = entire span
            return math.floor(span_mm / spacing) + 1

        if has_support:
            # Merged support zones — IS 456 end correction
            return math.floor(total_length / spacing) + 1

        # Pure midspan zones
        return math.floor(total_length / spacing)

    def legacy_quantity(self, span_mm: float, spacing_mm: int) -> int:
        """
        Returns the OLD (V.B.1) calculation for comparison:
        treats the full beam as one zone (always uniform).
        """
        if spacing_mm <= 0 or span_mm <= 0:
            return 0
        return math.floor(span_mm / spacing_mm) + 1
