"""
Stirrup Weight Engine — Phase SI.1 MODULE 6
Updated: Phase R.2B — EngineeringContext consumption (MODEL_VERSION 7.6.0)

Formula (IS 2502) unchanged — cover and hook sourced from EngineeringContext.
"""
import math
from typing import Optional, Any

_DENSITY_KG_M3 = 7850.0
_COVER_MM = 40.0
_HOOK_MULTIPLE = 10


class StirrupWeightEngine:
    """Deterministic steel weight calculator for stirrup groups."""

    def __init__(self, loader: Optional[Any] = None) -> None:
        self._loader = loader

    def _cover_mm(self, cover_mm: Optional[float]) -> float:
        if cover_mm is not None:
            return cover_mm
        if self._loader:
            return float(self._loader.get_cover("BEAM"))
        return _COVER_MM

    def _hook_multiple(self) -> int:
        if self._loader:
            return self._loader.get_hook_multiple(135)
        return _HOOK_MULTIPLE

    def _density(self) -> float:
        if self._loader:
            return self._loader.get_steel_density()
        return _DENSITY_KG_M3

    def cut_length_mm(
        self,
        diameter_mm: float,
        width_mm: float,
        depth_mm: float,
        cover_mm: Optional[float] = None,
    ) -> float:
        """Returns the cut length (mm) of one stirrup."""
        c = self._cover_mm(cover_mm)
        perimeter = (
            2 * (width_mm - 2 * c)
            + 2 * (depth_mm - 2 * c)
        )
        hook = 2 * self._hook_multiple() * diameter_mm
        return perimeter + hook

    def area_mm2(self, diameter_mm: float) -> float:
        return math.pi * diameter_mm ** 2 / 4.0

    def weight_per_unit_kg(
        self,
        diameter_mm: float,
        cut_length_mm: float,
    ) -> float:
        return self.area_mm2(diameter_mm) * cut_length_mm * self._density() / 1e9

    def total_weight_kg(
        self,
        diameter_mm: float,
        cut_length_mm: float,
        quantity: int,
    ) -> float:
        return self.weight_per_unit_kg(diameter_mm, cut_length_mm) * quantity
