"""
Deterministic severity assignment.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from typing import List

from engineering_issue_model import RawFinding

MODEL_VERSION = "8.7.0"

_CATEGORY_SEVERITY = {
    "Beam Discovery": "Critical",
    "Annotation Association": "Major",
    "Steel Aggregation": "Critical",
    "Weight Calculation": "Critical",
    "Diameter Interpretation": "Major",
    "Stirrup Interpretation": "Major",
    "Role Classification": "Major",
    "Cut Length": "Major",
    "Hook Interpretation": "Moderate",
    "Spacer Interpretation": "Moderate",
    "Side Face Reinforcement": "Moderate",
    "Piece Generation": "Major",
    "Quantity Interpretation": "Major",
    "Development Length": "Moderate",
    "Support Zone Interpretation": "Major",
    "Curtailment": "Moderate",
    "Continuity": "Moderate",
    "Workbook Export": "Minor",
    "Unknown": "Informational",
}


class SeverityEngine:
    def severity(
        self,
        category: str,
        findings: List[RawFinding],
        steel_impact_kg: float,
        engineering_impact: float,
    ) -> str:
        base = _CATEGORY_SEVERITY.get(category, "Informational")
        # escalate by impact
        if steel_impact_kg >= 1500 or engineering_impact >= 0.75:
            return "Critical"
        if steel_impact_kg >= 500 or engineering_impact >= 0.45:
            if base in ("Minor", "Informational", "Moderate"):
                return "Major"
            return base if base == "Critical" else "Major"
        if len(findings) >= 20 and base == "Moderate":
            return "Major"
        return base
