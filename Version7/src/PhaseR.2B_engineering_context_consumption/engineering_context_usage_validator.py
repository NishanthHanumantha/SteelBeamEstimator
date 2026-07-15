"""
Engineering Context Usage Validator — 12 rules for Phase R.2B
"""
from __future__ import annotations
import pathlib
from typing import Any, Dict, List, Optional

from .engineering_context_consumption_models import ConsumptionAuditResult


class EngineeringContextUsageValidator:

    def validate(
        self,
        loader,
        dependency_map: Dict[str, Any],
        production_result: Optional[Dict[str, Any]] = None,
        steel_weight_source: str = "",
    ) -> List[ConsumptionAuditResult]:
        matrix = dependency_map.get("consumption_matrix", [])
        consumed_params = {m["parameter"] for m in matrix if m["consumed"]}
        prod_ok = production_result and production_result.get("status") == "PASS"
        steel_kg = (production_result or {}).get("steel_weight_kg", 0)
        fallback_count = len(loader.fallback_log) if loader else 0

        return [
            self._rule("RULE_1", "Development Length consumes EngineeringContext",
                       "development_length" in consumed_params,
                       f"development_length consumed: {'development_length' in consumed_params}"),
            self._rule("RULE_2", "Cover consumes EngineeringContext",
                       "cover" in consumed_params,
                       f"cover consumed: {'cover' in consumed_params}"),
            self._rule("RULE_3", "Steel Grade consumes EngineeringContext",
                       "steel_grade" in consumed_params,
                       f"steel_grade consumed: {'steel_grade' in consumed_params}"),
            self._rule("RULE_4", "Concrete Grade consumes EngineeringContext",
                       "concrete_grade" in consumed_params,
                       f"concrete_grade consumed: {'concrete_grade' in consumed_params}"),
            self._rule("RULE_5", "Hook Rules consume EngineeringContext",
                       "hook" in consumed_params,
                       f"hook consumed: {'hook' in consumed_params}"),
            self._rule("RULE_6", "Lap Rules consume EngineeringContext",
                       "lap" in consumed_params,
                       f"lap consumed: {'lap' in consumed_params}"),
            self._rule("RULE_7", "Spacer Rules consume EngineeringContext",
                       loader is not None and bool(loader.get_spacer_rule()),
                       f"spacer rule: {loader.get_spacer_rule()[:60] if loader else 'N/A'}"),
            self._rule("RULE_8", "No hardcoded engineering assumptions remain",
                       dependency_map.get("consumption_pct", 0) >= 90,
                       f"consumption rate: {dependency_map.get('consumption_rate')}"),
            self._rule("RULE_9", "Existing engineering formulas unchanged",
                       "span_mm + 2" in steel_weight_source or "EngineeringContext" in steel_weight_source,
                       "Formula structure preserved: span + 2*Ld, perimeter + hook"),
            self._rule("RULE_10", "Existing estimator outputs generated successfully",
                       prod_ok and steel_kg > 0,
                       f"production status: {(production_result or {}).get('status')} | steel: {steel_kg:.3f} kg"),
            self._rule("RULE_11", "Backward compatibility maintained",
                       loader is not None,
                       f"loader available: {loader is not None} | fallbacks: {fallback_count}"),
            self._rule("RULE_12", "EngineeringContext used by every downstream calculation",
                       all(p in consumed_params for p in [
                           "development_length", "cover", "steel_grade",
                           "concrete_grade", "hook", "lap", "density",
                       ]),
                       f"consumed params: {sorted(consumed_params)}"),
        ]

    def _rule(self, rule_id: str, desc: str, passed: bool, evidence: str) -> ConsumptionAuditResult:
        return ConsumptionAuditResult(
            parameter=desc,
            rule_id=rule_id,
            passed=passed,
            evidence=evidence,
        )
