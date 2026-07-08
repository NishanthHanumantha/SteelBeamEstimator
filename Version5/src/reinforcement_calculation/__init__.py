"""Engineering Reinforcement Calculation — Phase I.2."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.reinforcement_calculation.reinforcement_builder import ReinforcementBuilder

__all__ = ["ReinforcementBuilder"]


def __getattr__(name: str):
    if name == "ReinforcementBuilder":
        from src.reinforcement_calculation.reinforcement_builder import ReinforcementBuilder

        return ReinforcementBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
