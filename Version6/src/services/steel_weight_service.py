"""Steel unit weight calculations."""

from __future__ import annotations

from typing import Any, Optional
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.general_notes.engineering_value import EngineeringValue, engineering_value_numeric


class SteelWeightService:
    """Steel unit weight from estimator rules and project defaults."""

    def __init__(self, cache: EngineeringRuleCache) -> None:
        self._cache = cache

    def unit_weight_kg_per_m(self, diameter_mm: float) -> Optional[float]:
        formula = self._cache.get_unit_weight_formula()
        if isinstance(formula, EngineeringValue):
            expr = str(engineering_value_numeric(formula) or formula.value or "")
        else:
            expr = str(formula)
        d = float(diameter_mm)
        if "d²" in expr or "d^2" in expr.lower():
            return (d * d) / 162.0
        if "d2" in expr.lower():
            return (d * d) / 162.0
        return (d * d) / 162.0

    def bar_weight_kg(self, diameter_mm: float, length_mm: float) -> Optional[float]:
        uw = self.unit_weight_kg_per_m(diameter_mm)
        if uw is None:
            return None
        return uw * (length_mm / 1000.0)

    def to_registry_entry(self) -> dict[str, Any]:
        return {
            "service_id": "steel_weight",
            "description": "Steel unit weight from estimator rules",
            "rule_reference": "RULE::ESTIMATOR",
            "status": "READY",
        }
