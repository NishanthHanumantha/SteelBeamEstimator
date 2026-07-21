"""
Human-readable recommendations from the rule library.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Any, Dict, List

from engineering_rule_model import EngineeringRule

MODEL_VERSION = "8.8.0"


class RecommendationGenerator:
    def generate(self, rules: List[EngineeringRule]) -> Dict[str, Any]:
        ordered = sorted(rules, key=lambda r: r.priority)
        recs = []
        for r in ordered:
            recs.append({
                "priority": r.priority,
                "rule_id": r.rule_id,
                "title": f"Implement {r.rule_name}",
                "rule_family": r.rule_family,
                "gap_type": r.gap_type,
                "implementation_phase": r.implementation_phase,
                "expected_accuracy_gain_pct": r.expected_accuracy_gain,
                "estimated_steel_gain_kg": r.estimated_steel_gain_kg,
                "dependencies": list(r.dependencies),
                "decision_logic": list(r.decision_logic),
                "validation_criteria": list(r.validation_criteria),
                "confidence": r.confidence,
            })
        return {"model_version": MODEL_VERSION, "recommendations": recs}
