"""
Priority banding from impact / frequency / severity.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

MODEL_VERSION = "8.7.0"


class PriorityEngine:
    def priority(self, severity: str, engineering_impact: float, frequency: int) -> str:
        if severity == "Critical" or engineering_impact >= 0.55 or frequency >= 25:
            return "High"
        if severity == "Major" or engineering_impact >= 0.30 or frequency >= 10:
            return "High" if frequency >= 15 else "Medium"
        if severity in ("Moderate",):
            return "Medium"
        if severity == "Minor":
            return "Low"
        return "Low"
