"""Reporter for Phase R.2B consumption audit."""
from __future__ import annotations
from typing import Any, Dict, List


class EngineeringContextReporter:

    def build_summary(
        self,
        usage_results: List,
        dependency_map: Dict[str, Any],
        production_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        passed = sum(1 for r in usage_results if r.passed)
        return {
            "phase": "R.2B",
            "model_version": "7.6.0",
            "validation_score": f"{passed}/{len(usage_results)}",
            "all_pass": passed == len(usage_results),
            "consumption_rate": dependency_map.get("consumption_rate"),
            "production_status": production_result.get("status"),
            "steel_weight_kg": production_result.get("steel_weight_kg"),
            "workbook_generated": bool(production_result.get("workbook_path")),
            "rules": [r.to_dict() for r in usage_results],
        }
