"""
Improvement backlog from ranked engineering issues.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from typing import Any, Dict, List

from engineering_issue_model import EngineeringIssue

MODEL_VERSION = "8.7.0"


class ImprovementBacklogEngine:
    def build(self, ranked_issues: List[EngineeringIssue], max_items: int = 15) -> Dict[str, Any]:
        # Deduplicate by category keeping highest impact issue per category for backlog headline
        seen_cats = set()
        items = []
        for issue in ranked_issues:
            if issue.category in seen_cats and issue.category not in (
                "Role Classification",  # allow role families separately via subcategory
            ):
                # still allow distinct subcategories for role-like issues
                key = (issue.category, issue.subcategory)
            else:
                key = (issue.category, issue.subcategory)
            if key in seen_cats:
                continue
            seen_cats.add(key)
            items.append({
                "priority": len(items) + 1,
                "issue_id": issue.issue_id,
                "title": f"Improve {issue.category}"
                + (f" ({issue.subcategory})" if issue.subcategory else ""),
                "category": issue.category,
                "subcategory": issue.subcategory,
                "recommended_phase": issue.recommended_phase,
                "expected_accuracy_gain_pct": issue.expected_accuracy_gain,
                "steel_impact_kg": issue.steel_impact_kg,
                "severity": issue.severity,
                "confidence": issue.confidence,
                "recommended_fix": issue.recommended_fix,
                "priority_band": issue.priority,
            })
            if len(items) >= max_items:
                break
        total_gain = round(sum(i["expected_accuracy_gain_pct"] for i in items), 2)
        return {
            "model_version": MODEL_VERSION,
            "item_count": len(items),
            "cumulative_expected_gain_pct": total_gain,
            "items": items,
        }
