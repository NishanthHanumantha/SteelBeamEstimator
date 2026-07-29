"""
Frequency analysis across clustered issues.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from typing import Any, Dict, List

from engineering_issue_model import EngineeringIssue

MODEL_VERSION = "8.7.0"


class FrequencyAnalysisEngine:
    def analyze(self, issues: List[EngineeringIssue], total_findings: int) -> Dict[str, Any]:
        rows = []
        for issue in issues:
            pct = (issue.frequency / total_findings * 100.0) if total_findings else 0.0
            rows.append({
                "issue_id": issue.issue_id,
                "category": issue.category,
                "subcategory": issue.subcategory,
                "occurrences": issue.frequency,
                "affected_beams": len(issue.affected_beams),
                "affected_roles": list(issue.affected_roles),
                "affected_diameters": list(issue.affected_diameters),
                "pct_of_findings": round(pct, 2),
            })
        rows.sort(key=lambda r: (-r["occurrences"], r["category"], r["subcategory"]))
        return {
            "model_version": MODEL_VERSION,
            "total_findings": total_findings,
            "issue_count": len(issues),
            "rows": rows,
        }
