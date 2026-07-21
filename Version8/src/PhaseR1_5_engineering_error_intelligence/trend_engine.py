"""
Project-level trend summaries from EngineeringIssues.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from engineering_issue_model import EngineeringIssue, RawFinding

MODEL_VERSION = "8.7.0"


class TrendEngine:
    def analyze(
        self,
        issues: List[EngineeringIssue],
        findings: List[RawFinding],
        official_total_kg: float,
        steel_gap_kg: float,
    ) -> Dict[str, Any]:
        if not issues:
            return {"model_version": MODEL_VERSION, "trends": {}}

        top_recurring = max(issues, key=lambda i: (i.frequency, i.engineering_impact))
        largest_steel = max(issues, key=lambda i: (i.steel_impact_kg, i.frequency))
        largest_weight = max(issues, key=lambda i: (i.weight_percentage, i.frequency))
        largest_source = max(issues, key=lambda i: (i.engineering_impact, i.frequency))

        role_counter = Counter()
        for f in findings:
            if f.role:
                role_counter[f.role] += 1
        dia_counter = Counter()
        for f in findings:
            if f.diameter:
                dia_counter[f.diameter] += 1
        missing_reinf = Counter()
        for f in findings:
            if f.error_type == "Missing Reinforcement Row" and f.role:
                missing_reinf[f.role] += 1

        return {
            "model_version": MODEL_VERSION,
            "trends": {
                "top_recurring_issue": {
                    "issue_id": top_recurring.issue_id,
                    "category": top_recurring.category,
                    "frequency": top_recurring.frequency,
                },
                "largest_steel_loss": {
                    "issue_id": largest_steel.issue_id,
                    "category": largest_steel.category,
                    "steel_impact_kg": largest_steel.steel_impact_kg,
                    "steel_impact_mt": round(largest_steel.steel_impact_kg / 1000.0, 3),
                },
                "largest_weight_loss": {
                    "issue_id": largest_weight.issue_id,
                    "category": largest_weight.category,
                    "weight_percentage": largest_weight.weight_percentage,
                },
                "most_common_wrong_role": role_counter.most_common(1)[0] if role_counter else None,
                "most_common_diameter_mismatch": dia_counter.most_common(1)[0] if dia_counter else None,
                "most_common_missing_reinforcement": (
                    missing_reinf.most_common(1)[0] if missing_reinf else None
                ),
                "largest_source_of_production_error": {
                    "issue_id": largest_source.issue_id,
                    "category": largest_source.category,
                    "engineering_impact": largest_source.engineering_impact,
                    "originating_phase": largest_source.originating_phase,
                },
                "project_steel_gap_kg": round(steel_gap_kg, 3),
                "official_total_kg": round(official_total_kg, 3),
            },
        }
