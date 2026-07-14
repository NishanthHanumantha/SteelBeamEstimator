"""
Stirrup Weight Engine — Phase SI.1 MODULE 6

Computes steel weight for each stirrup group (zone-merged BBS row).

Formula (IS 2502):
  Stirrup cut length = 2(W - 2c) + 2(D - 2c) + 2 × hook
  hook = 10d  (standard 135-degree hook allowance, IS 2502)
  cover c = 40mm (IS 456:2000 Table 16)

  Bar area  = pi × d² / 4   [mm²]
  Density   = 7850 kg/m³
  Weight    = area × cut_length × qty × 7850 / 1e9   [kg]
"""
import math
from typing import Optional

_DENSITY_KG_M3 = 7850.0
_COVER_MM = 40.0
_HOOK_MULTIPLE = 10       # 10d per hook end (135-degree)


class StirrupWeightEngine:
    """Deterministic steel weight calculator for stirrup groups."""

    def cut_length_mm(
        self,
        diameter_mm: float,
        width_mm: float,
        depth_mm: float,
        cover_mm: float = _COVER_MM,
    ) -> float:
        """Returns the cut length (mm) of one stirrup."""
        perimeter = (
            2 * (width_mm - 2 * cover_mm)
            + 2 * (depth_mm - 2 * cover_mm)
        )
        hook = 2 * _HOOK_MULTIPLE * diameter_mm
        return perimeter + hook

    def area_mm2(self, diameter_mm: float) -> float:
        return math.pi * diameter_mm ** 2 / 4.0

    def weight_per_unit_kg(
        self,
        diameter_mm: float,
        cut_length_mm: float,
    ) -> float:
        """Weight of ONE stirrup in kg."""
        return self.area_mm2(diameter_mm) * cut_length_mm * _DENSITY_KG_M3 / 1e9

    def total_weight_kg(
        self,
        diameter_mm: float,
        cut_length_mm: float,
        quantity: int,
    ) -> float:
        return self.weight_per_unit_kg(diameter_mm, cut_length_mm) * quantity
