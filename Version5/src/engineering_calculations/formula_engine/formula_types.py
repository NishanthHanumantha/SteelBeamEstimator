"""Formula evaluation input types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LapLengthFormulaInput:
    """Pure numeric inputs for lap length evaluation."""

    development_length_mm: int
    lap_factor: float
    minimum_lap_mm: int
