"""Cut length formula engine — pure mathematical evaluation only."""

from __future__ import annotations

from dataclasses import dataclass

from src.engineering_calculations.cut_length_types import (
    SPAN_BASIS_CLEAR_SPAN,
    SPAN_BASIS_SECTION_PERIMETER,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedCutLengthRule


@dataclass(frozen=True)
class CutLengthFormulaInput:
    """Pure numeric inputs for cut length evaluation."""

    clear_span_mm: int
    effective_span_mm: int
    development_length_mm: int
    hook_length_mm: int
    lap_length_mm: int
    beam_width_mm: int
    beam_depth_mm: int
    cover_side_mm: int
    resolved_rule: ResolvedCutLengthRule


class CutLengthFormulaEngine:
    """Evaluate cut length from resolved numeric inputs only."""

    @classmethod
    def evaluate(cls, formula_input: CutLengthFormulaInput) -> int:
        rule = formula_input.resolved_rule
        if rule.span_basis == SPAN_BASIS_SECTION_PERIMETER:
            base_span = cls._section_perimeter_mm(
                formula_input.beam_width_mm,
                formula_input.beam_depth_mm,
                formula_input.cover_side_mm,
            )
        elif rule.use_effective_span:
            base_span = int(formula_input.effective_span_mm)
        else:
            base_span = int(formula_input.clear_span_mm)

        development_total = (
            int(rule.development_length_end_count) * int(formula_input.development_length_mm)
        )
        hook_total = int(rule.hook_length_end_count) * int(formula_input.hook_length_mm)
        lap_total = int(rule.lap_length_adjustment_count) * int(formula_input.lap_length_mm)
        return int(base_span + development_total + hook_total + lap_total)

    @staticmethod
    def _section_perimeter_mm(
        beam_width_mm: int,
        beam_depth_mm: int,
        cover_side_mm: int,
    ) -> int:
        inner_width = max(int(beam_width_mm) - (2 * int(cover_side_mm)), 0)
        inner_depth = max(int(beam_depth_mm) - (2 * int(cover_side_mm)), 0)
        return int((2 * inner_width) + (2 * inner_depth))
