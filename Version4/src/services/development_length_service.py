"""Development length resolution via engineering rule cache."""

from __future__ import annotations

from typing import Any, Optional

from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import EngineeringValue


class DevelopmentLengthService:
    """Resolve bar development length from project engineering rules."""

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache

    def get_development_length(
        self,
        diameter_mm: int,
        concrete_grade: Optional[str] = None,
        steel_grade: Optional[str] = None,
    ) -> Optional[EngineeringValue]:
        concrete = concrete_grade or self._cache.get_default_concrete_grade() or "M30"
        if steel_grade:
            return self._cache.get_ld(steel_grade, concrete, diameter_mm)
        return self._cache.get_active_ld(diameter_mm, concrete)

    def to_registry_entry(self) -> dict[str, Any]:
        return {
            "service_id": "development_length",
            "description": "Bar development length from General Notes tables",
            "rule_reference": "RULE::PROJECT",
            "status": "READY",
        }
