"""
Assign deterministic priorities to rules.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import List, Tuple

from engineering_rule_model import EngineeringRule

MODEL_VERSION = "8.8.0"


class RulePriorityEngine:
    def prioritize(self, rules: List[EngineeringRule]) -> List[EngineeringRule]:
        # Sort by expected gain, steel gain, confidence; then topological preference:
        # dependents after dependencies when gains equal-ish — primarily gain-driven for roadmap
        ordered = sorted(
            rules,
            key=lambda r: (
                -r.expected_accuracy_gain,
                -r.estimated_steel_gain_kg,
                -r.confidence,
                r.rule_family,
                r.rule_id,
            ),
        )
        out = []
        for idx, r in enumerate(ordered, start=1):
            d = r.to_dict()
            d.pop("model_version", None)
            d["priority"] = idx
            out.append(EngineeringRule(**{k: v for k, v in d.items() if k in EngineeringRule.__dataclass_fields__}))
        return out
