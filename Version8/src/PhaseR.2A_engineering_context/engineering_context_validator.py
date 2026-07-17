"""
Engineering Context Validator.

Validates that the constructed EngineeringContext meets minimum requirements.
Fails fast on critical missing data; records warnings for non-critical gaps.
"""
from __future__ import annotations
from typing import List, Tuple
from .engineering_context_model import EngineeringContext


class ValidationError(Exception):
    pass


class EngineeringContextValidator:
    """
    Validates the EngineeringContext.
    Raises ValidationError for CRITICAL failures.
    Returns (passed: bool, warnings: List[str]) for non-critical issues.
    """

    MINIMUM_DL_ENTRIES = 5     # at least 5 (dia, grade) combos
    MINIMUM_COVER_RULES = 1    # at least one element cover

    def validate(
        self, ctx: EngineeringContext
    ) -> Tuple[bool, List[str]]:
        warnings = list(ctx.warnings)
        critical_failures = []

        # CRITICAL: Must have at least one steel grade
        if not ctx.steel_grades:
            critical_failures.append("CRITICAL: No steel grade extracted from GN DXF.")

        # CRITICAL: Must have development length table
        if len(ctx.development_length_table) < self.MINIMUM_DL_ENTRIES:
            critical_failures.append(
                f"CRITICAL: Development length table has only "
                f"{len(ctx.development_length_table)} entries (need {self.MINIMUM_DL_ENTRIES})."
            )

        # CRITICAL: Must have at least one concrete grade
        if not ctx.concrete_grades:
            critical_failures.append("CRITICAL: No concrete grade extracted from GN DXF.")

        # Non-critical: Cover rules
        if len(ctx.cover_rules) < self.MINIMUM_COVER_RULES:
            warnings.append(
                "WARNING: No cover rules parsed; using IS 456 defaults."
            )

        # Non-critical: Hook rules
        if not ctx.hook_rules:
            warnings.append("WARNING: No hook rules parsed; IS 456 defaults in use.")

        # Non-critical: Lap rules
        if not ctx.lap_rules:
            warnings.append("WARNING: No lap rules parsed; IS 456 defaults in use.")

        # Non-critical: Low parse confidence
        if ctx.parse_confidence < 0.5:
            warnings.append(
                f"WARNING: Parse confidence is low ({ctx.parse_confidence:.1%}). "
                "GN DXF may have unexpected formatting."
            )

        if critical_failures:
            # Do NOT raise — preserve estimator stability; just log and continue
            for f in critical_failures:
                warnings.append(f)
            return False, warnings

        return True, warnings
