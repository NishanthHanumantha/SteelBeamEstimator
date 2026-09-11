"""Adapters around existing R.1.3 / V.B.1 engineering engines. Do not rewrite formulas."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PhaseR1_3_reinforcement_piece_generation.piece_geometry import PieceGeometry

_VB1 = Path(__file__).resolve().parents[1] / "PhaseVB.1_production_output_completion"
if str(_VB1) not in sys.path:
    sys.path.insert(0, str(_VB1))

from steel_weight_completion import SteelWeightCompletion  # type: ignore  # noqa: E402

_SWC = SteelWeightCompletion(Path("."), loader=None)
_SWC._improver = None

FORMULA_WEIGHT = "W = (pi * d^2 / 4) * L * qty * 7850 / 1e9"
FORMULA_SOURCE = "PhaseR1_3_reinforcement_piece_generation.piece_geometry.PieceGeometry.weight_kg"
CUT_SOURCE = "PhaseVB.1_production_output_completion.steel_weight_completion.SteelWeightCompletion._derive_cut_length"


def map_engineering_role(layer: Any, role: Any) -> str:
    layer_u = str(layer or "").upper()
    role_u = str(role or "").upper()
    if role_u == "SPACER" or layer_u == "SPACER":
        return "SPACER"
    if role_u == "STIRRUP" or layer_u == "STIRRUP":
        return "STIRRUP"
    if role_u == "EXTRA":
        if layer_u == "BOTTOM":
            return "BOTTOM_EXTRA"
        return "TOP_EXTRA"
    if layer_u == "BOTTOM":
        return "BOTTOM_MAIN"
    return "TOP_MAIN"


def derive_cut_length_mm(
    *,
    role: str,
    diameter_mm: float,
    span_mm: float,
    depth_mm: Optional[float],
    width_mm: Optional[float],
    provided_cut_mm: Optional[float] = None,
) -> Tuple[Optional[float], str]:
    if provided_cut_mm is not None:
        try:
            val = float(provided_cut_mm)
        except (TypeError, ValueError):
            val = None
        else:
            if val > 0:
                return val, "EXISTING_INSTANCE_CUT_LENGTH"
    cut, source = _SWC._derive_cut_length(
        role,
        float(diameter_mm),
        float(span_mm or 0.0),
        depth_mm,
        width_mm,
        None,
        1,
        provided_cut_mm=None,
    )
    return cut, f"DETERMINISTIC_ENGINE:{CUT_SOURCE}:{source}"


def weight_kg(diameter_mm: float, cut_mm: Optional[float], quantity: int) -> Optional[float]:
    return PieceGeometry.weight_kg(float(diameter_mm), cut_mm, int(quantity))


def development_length_mm(diameter_mm: float) -> int:
    return int(_SWC._development_length_mm(float(diameter_mm)))


def numeric_cut(value: Any) -> Optional[float]:
    if value in (None, "", "UNAVAILABLE", "UNKNOWN"):
        return None
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


__all__ = [
    "FORMULA_SOURCE",
    "FORMULA_WEIGHT",
    "derive_cut_length_mm",
    "development_length_mm",
    "map_engineering_role",
    "numeric_cut",
    "weight_kg",
]
