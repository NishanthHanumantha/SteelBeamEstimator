"""
Root-cause ranking — Top engineering issues.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from typing import Any, Dict, List

from engineering_issue_model import EngineeringIssue

MODEL_VERSION = "8.7.0"


class RootCauseEngine:
    def rank(self, issues: List[EngineeringIssue], top_n: int = 20) -> Dict[str, Any]:
        ranked = sorted(
            issues,
            key=lambda i: (-i.engineering_impact, -i.frequency, -i.confidence, i.issue_id),
        )
        top = ranked[:top_n]
        return {
            "model_version": MODEL_VERSION,
            "top_n": len(top),
            "sort_order": ["engineering_impact", "frequency", "confidence"],
            "rankings": [
                {
                    "rank": idx + 1,
                    "issue_id": i.issue_id,
                    "category": i.category,
                    "subcategory": i.subcategory,
                    "originating_phase": i.originating_phase,
                    "frequency": i.frequency,
                    "severity": i.severity,
                    "engineering_impact": i.engineering_impact,
                    "steel_impact_kg": i.steel_impact_kg,
                    "confidence": i.confidence,
                    "root_cause": i.root_cause,
                    "recommended_fix": i.recommended_fix,
                    "expected_accuracy_gain": i.expected_accuracy_gain,
                }
                for idx, i in enumerate(top)
            ],
        }
