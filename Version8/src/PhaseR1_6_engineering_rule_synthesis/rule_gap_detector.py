"""
Detect gap type for each issue/family.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Any, Dict

MODEL_VERSION = "8.8.0"

_FAMILY_GAP = {
    "Beam Discovery": "Missing Rule",
    "Annotation Association": "Incorrect Mapping",
    "Role Resolution": "Incomplete Classification",
    "Diameter Resolution": "Incorrect Rule",
    "Stirrup Interpretation": "Incomplete Rule",
    "Hook Interpretation": "Missing Dependency",
    "Spacer Interpretation": "Incomplete Rule",
    "Side Face Reinforcement": "Unsupported Engineering Case",
    "Cut Length": "Incorrect Rule",
    "Steel Aggregation": "Incorrect Aggregation",
    "Weight Calculation": "Incorrect Aggregation",
    "Workbook Mapping": "Weak Validation",
    "Piece Generation": "Incomplete Rule",
    "Support Zone": "Incomplete Rule",
    "Curtailment": "Incomplete Rule",
    "Continuity": "Incomplete Rule",
    "Development Length": "Incorrect Rule",
    "Future": "Unsupported Engineering Case",
}


class RuleGapDetector:
    def detect(self, family: str, issue: Dict[str, Any]) -> Dict[str, Any]:
        gap = _FAMILY_GAP.get(family, "Missing Rule")
        freq = int(issue.get("frequency") or 0)
        # escalate incomplete → missing when high frequency and low classification coverage signals
        if family == "Stirrup Interpretation" and freq >= 10:
            gap = "Incomplete Rule"
        if family == "Hook Interpretation":
            gap = "Missing Dependency"  # depends on stirrup rule
        if family == "Role Resolution" and freq >= 3:
            gap = "Incomplete Classification"
        status = {
            "Missing Rule": "Missing",
            "Incomplete Rule": "Partial",
            "Incorrect Rule": "Partial",
            "Weak Validation": "Partial",
            "Missing Dependency": "Partial",
            "Incorrect Mapping": "Partial",
            "Incomplete Classification": "Partial",
            "Incorrect Aggregation": "Partial",
            "Unsupported Engineering Case": "Missing",
            "Unsupported Estimator Convention": "Missing",
        }.get(gap, "Missing")
        return {
            "gap_type": gap,
            "status": status,
            "rationale": f"{family} gap classified as {gap} from issue {issue.get('issue_id')}",
        }
