"""
Map Engineering Issues → rule families.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Dict, Tuple

from engineering_rule_model import RULE_FAMILIES

MODEL_VERSION = "8.8.0"

_CATEGORY_TO_FAMILY: Dict[str, str] = {
    "Beam Discovery": "Beam Discovery",
    "Annotation Association": "Annotation Association",
    "Role Classification": "Role Resolution",
    "Diameter Interpretation": "Diameter Resolution",
    "Stirrup Interpretation": "Stirrup Interpretation",
    "Hook Interpretation": "Hook Interpretation",
    "Spacer Interpretation": "Spacer Interpretation",
    "Side Face Reinforcement": "Side Face Reinforcement",
    "Development Length": "Development Length",
    "Cut Length": "Cut Length",
    "Support Zone Interpretation": "Support Zone",
    "Curtailment": "Curtailment",
    "Continuity": "Continuity",
    "Piece Generation": "Piece Generation",
    "Steel Aggregation": "Steel Aggregation",
    "Weight Calculation": "Weight Calculation",
    "Workbook Export": "Workbook Mapping",
    "Unknown": "Future",
}


class RuleFamilyClassifier:
    def classify(self, issue_category: str, subcategory: str = "") -> str:
        family = _CATEGORY_TO_FAMILY.get(issue_category, "Future")
        if family not in RULE_FAMILIES:
            family = "Future"
        return family

    def pattern_key(self, family: str, subcategory: str) -> str:
        """
        Deterministic pattern key for consolidation.
        Role subcategories collapse into one Role Resolution pattern.
        """
        if family == "Role Resolution":
            return "Role Resolution::ALL"
        if family in (
            "Stirrup Interpretation",
            "Hook Interpretation",
            "Spacer Interpretation",
            "Side Face Reinforcement",
            "Steel Aggregation",
            "Weight Calculation",
            "Beam Discovery",
            "Annotation Association",
            "Diameter Resolution",
            "Cut Length",
        ):
            return f"{family}::CANONICAL"
        return f"{family}::{subcategory or 'DEFAULT'}"
