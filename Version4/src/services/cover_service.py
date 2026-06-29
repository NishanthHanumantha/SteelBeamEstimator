"""Cover resolution via engineering rule cache."""

from __future__ import annotations

from typing import Any, Optional

from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import EngineeringValue


class CoverService:
    """Resolve member cover from project engineering rules."""

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache

    def get_cover(self, member_type: str = "BEAM") -> Optional[EngineeringValue]:
        cover = self._cache.get_cover(member_type)
        if cover:
            return cover
        return self._cache.get_default_cover()

    def to_registry_entry(self) -> dict[str, Any]:
        return {
            "service_id": "cover",
            "description": "Member cover from General Notes cover table",
            "rule_reference": "RULE::PROJECT",
            "status": "READY",
        }
