"""Lap length formula engine — pure mathematical evaluation only."""

from __future__ import annotations

from src.engineering_calculations.formula_engine.formula_types import LapLengthFormulaInput


class LapLengthFormulaEngine:
    """Evaluate lap length from resolved numeric inputs only."""

    @staticmethod
    def evaluate(
        development_length_mm: int,
        lap_factor: float,
        minimum_lap_mm: int,
    ) -> int:
        return max(int(round(development_length_mm * lap_factor)), minimum_lap_mm)

    @classmethod
    def evaluate_input(cls, formula_input: LapLengthFormulaInput) -> int:
        return cls.evaluate(
            formula_input.development_length_mm,
            formula_input.lap_factor,
            formula_input.minimum_lap_mm,
        )
