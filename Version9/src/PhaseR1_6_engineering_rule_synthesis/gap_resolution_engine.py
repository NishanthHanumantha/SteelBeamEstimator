"""
Gap resolution plan per rule.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Any, Dict, List

from engineering_rule_model import EngineeringRule

MODEL_VERSION = "8.8.0"

_FAMILY_MODULES = {
    "Beam Discovery": ["PhaseR.1_generalized_reinforcement_discovery"],
    "Annotation Association": ["PhaseR.1_generalized_reinforcement_discovery", "PhaseR1_1B_production_integration"],
    "Role Resolution": ["PhaseR1_2C_engineering_intent_resolution"],
    "Diameter Resolution": ["PhaseR1_2C_engineering_intent_resolution", "PhaseR1_2D_reinforcement_detailing"],
    "Stirrup Interpretation": ["PhaseR1_2D_reinforcement_detailing", "PhaseSI.0", "PhaseSI.1"],
    "Hook Interpretation": ["PhaseR1_2D_reinforcement_detailing"],
    "Spacer Interpretation": ["PhaseR1_2C_engineering_intent_resolution", "PhaseR1_2D_reinforcement_detailing"],
    "Side Face Reinforcement": ["PhaseR1_2D_reinforcement_detailing"],
    "Cut Length": ["PhaseR1_3_reinforcement_piece_generation"],
    "Piece Generation": ["PhaseR1_3_reinforcement_piece_generation"],
    "Steel Aggregation": ["PhaseVB.1_production_output_completion", "PhaseR1.3_pipeline_integration"],
    "Weight Calculation": ["PhaseVB.1_production_output_completion"],
    "Workbook Mapping": ["PhaseVB.1_production_output_completion"],
}


class GapResolutionEngine:
    def plan(self, rules: List[EngineeringRule]) -> Dict[str, Any]:
        items = []
        for r in sorted(rules, key=lambda x: x.priority):
            items.append({
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "rule_family": r.rule_family,
                "current_status": r.status,
                "gap_type": r.gap_type,
                "replacement": None if r.status != "Deprecated" else "TBD",
                "required_modules": _FAMILY_MODULES.get(r.rule_family, []),
                "affected_production_phases": [r.implementation_phase],
                "engineering_risk": r.engineering_risk,
                "estimated_implementation_effort": r.estimated_effort,
                "expected_accuracy_gain": r.expected_accuracy_gain,
                "dependencies": list(r.dependencies),
            })
        return {
            "model_version": MODEL_VERSION,
            "item_count": len(items),
            "items": items,
        }
