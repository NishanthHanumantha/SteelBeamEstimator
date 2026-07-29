"""Thin consumer wrappers delegating to EngineeringContextLoader."""
from __future__ import annotations
from typing import Any


class DevelopmentLengthConsumer:
    def __init__(self, loader: Any):
        self._loader = loader

    def get_development_length_mm(
        self, diameter_mm: int, concrete_grade: str = None, steel_grade: str = None
    ) -> int:
        return self._loader.get_development_length_mm(diameter_mm, concrete_grade, steel_grade)

    def get_development_length_factor(
        self, concrete_grade: str = None, steel_grade: str = None
    ) -> int:
        return self._loader.get_development_length_factor(concrete_grade, steel_grade)


class CoverRuleConsumer:
    def __init__(self, loader: Any):
        self._loader = loader

    def get_cover(self, element_type: str = "BEAM") -> int:
        return self._loader.get_cover(element_type)


class SteelGradeConsumer:
    def __init__(self, loader: Any):
        self._loader = loader

    def get_steel_grade(self) -> str:
        return self._loader.get_steel_grade()


class ConcreteGradeConsumer:
    def __init__(self, loader: Any):
        self._loader = loader

    def get_concrete_grade(self, element: str = "BEAM") -> str:
        return self._loader.get_concrete_grade(element)


class HookRuleConsumer:
    def __init__(self, loader: Any):
        self._loader = loader

    def get_hook_rule(self, hook_angle: int = 135) -> int:
        return self._loader.get_hook_multiple(hook_angle)


class LapRuleConsumer:
    def __init__(self, loader: Any):
        self._loader = loader

    def get_lap_rule(self, bar_diameter: int = None, location: str = "") -> int:
        return self._loader.get_lap_rule(bar_diameter, location)


class SpacerRuleConsumer:
    def __init__(self, loader: Any):
        self._loader = loader

    def get_spacer_rule(self) -> str:
        return self._loader.get_spacer_rule()
