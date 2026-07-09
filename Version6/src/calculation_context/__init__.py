"""Engineering Calculation Context — Phase I.1."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.calculation_context.context_builder import CalculationContextBuilder

__all__ = ["CalculationContextBuilder"]


def __getattr__(name: str):
    if name == "CalculationContextBuilder":
        from src.calculation_context.context_builder import CalculationContextBuilder

        return CalculationContextBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
