"""
Implementation roadmap from prioritized rules.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Any, Dict, List

from engineering_rule_model import EngineeringRule

MODEL_VERSION = "8.8.0"


class RuleLibraryBuilder:
    def build_roadmap(self, rules: List[EngineeringRule]) -> Dict[str, Any]:
        ordered = sorted(rules, key=lambda r: r.priority)
        items = []
        for r in ordered:
            items.append({
                "priority": r.priority,
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "rule_family": r.rule_family,
                "expected_accuracy_gain_pct": r.expected_accuracy_gain,
                "estimated_steel_gain_kg": r.estimated_steel_gain_kg,
                "dependencies": list(r.dependencies),
                "implementation_phase": r.implementation_phase,
                "engineering_risk": r.engineering_risk,
                "estimated_complexity": r.estimated_effort,
                "status": r.status,
                "gap_type": r.gap_type,
            })
        return {
            "model_version": MODEL_VERSION,
            "rule_count": len(items),
            "cumulative_expected_gain_pct": round(sum(i["expected_accuracy_gain_pct"] for i in items), 2),
            "cumulative_steel_gain_kg": round(sum(i["estimated_steel_gain_kg"] for i in items), 3),
            "items": items,
        }

    def library_index(self, rules: List[EngineeringRule]) -> Dict[str, Any]:
        return {
            "model_version": MODEL_VERSION,
            "title": "Engineering Rule Library",
            "single_source_of_truth": True,
            "rule_count": len(rules),
            "families": sorted({r.rule_family for r in rules}),
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "rule_family": r.rule_family,
                    "priority": r.priority,
                    "status": r.status,
                    "implementation_phase": r.implementation_phase,
                    "expected_accuracy_gain": r.expected_accuracy_gain,
                    "originating_issues": list(r.originating_issues),
                }
                for r in sorted(rules, key=lambda x: x.priority)
            ],
        }
