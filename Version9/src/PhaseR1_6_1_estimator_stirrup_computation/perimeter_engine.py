"""
Perimeter engine.
MODEL_VERSION: 8.8.1

Perimeter = 2 × [(B − 2C) + (D − 2C)]
"""
from __future__ import annotations

MODEL_VERSION = "8.8.1"


class PerimeterEngine:
    def compute(
        self,
        beam_width_mm: float,
        beam_depth_mm: float,
        cover_mm: float,
    ) -> float:
        if beam_width_mm <= 0 or beam_depth_mm <= 0:
            raise ValueError("beam width/depth must be > 0")
        if cover_mm < 0:
            raise ValueError("cover_mm must be >= 0")
        clear_b = beam_width_mm - 2.0 * cover_mm
        clear_d = beam_depth_mm - 2.0 * cover_mm
        if clear_b <= 0 or clear_d <= 0:
            raise ValueError("cover too large for beam section")
        return 2.0 * (clear_b + clear_d)
