"""Deterministic steel weight calculator — Phase I.11."""

from __future__ import annotations

import math
from typing import Any

from src.engineering_calculations.steel_weight.steel_weight_types import (
    CONVERSION_FACTOR,
    ENGINEERING_PRECISION,
    EXPORT_PRECISION,
    FORMULA_NAME,
    FORMULA_VERSION,
    STEEL_DENSITY_KG_M3,
    UNIT_KG,
)


class SteelWeightCalculator:
    """Compute engineering steel weight from diameter and cut length only."""

    @staticmethod
    def calculate(diameter_mm: float, cut_length_mm: float) -> dict[str, Any]:
        diameter = float(diameter_mm)
        cut_length = float(cut_length_mm)
        length_m = cut_length / 1000.0
        diameter_m = diameter / 1000.0

        weight_pi_formula = (
            (math.pi / 4.0)
            * (diameter_m ** 2)
            * length_m
            * STEEL_DENSITY_KG_M3
        )
        weight_d2_formula = length_m * (diameter ** 2) / CONVERSION_FACTOR

        raw = round(weight_pi_formula, ENGINEERING_PRECISION)
        alternate = round(weight_d2_formula, ENGINEERING_PRECISION)
        export_value = round(raw, EXPORT_PRECISION)
        export_alternate = round(alternate, EXPORT_PRECISION)
        if export_value != export_alternate:
            export_value = export_alternate
            raw = round(weight_d2_formula, ENGINEERING_PRECISION)

        return {
            "weight_kg_raw": raw,
            "weight_kg": export_value,
            "unit": UNIT_KG,
            "formula": FORMULA_NAME,
            "formula_version": FORMULA_VERSION,
            "density_kg_m3": STEEL_DENSITY_KG_M3,
            "conversion_factor": CONVERSION_FACTOR,
            "engineering_precision": ENGINEERING_PRECISION,
            "export_precision": EXPORT_PRECISION,
            "diameter_mm": diameter,
            "cut_length_mm": cut_length,
            "length_m": round(length_m, ENGINEERING_PRECISION),
            "alternate_formula_kg": alternate,
            "alternate_formula_export_kg": export_alternate,
        }
