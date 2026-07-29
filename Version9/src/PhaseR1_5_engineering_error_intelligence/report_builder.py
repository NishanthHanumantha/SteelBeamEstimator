"""
Markdown + dashboard report builder.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from engineering_issue_model import EngineeringIssue

MODEL_VERSION = "8.7.0"


class ReportBuilder:
    def build_dashboard(
        self,
        issues: List[EngineeringIssue],
        rankings: Dict[str, Any],
        backlog: Dict[str, Any],
        trends: Dict[str, Any],
        validation: Dict[str, Any],
        overall_accuracy: float,
        steel_gap_kg: float,
    ) -> Dict[str, Any]:
        return {
            "model_version": MODEL_VERSION,
            "headline": "What engineering problems should be solved first to maximize production accuracy?",
            "overall_production_accuracy": overall_accuracy,
            "steel_gap_kg": steel_gap_kg,
            "issue_count": len(issues),
            "top_5": (rankings.get("rankings") or [])[:5],
            "backlog_top_5": (backlog.get("items") or [])[:5],
            "cumulative_expected_gain_pct": backlog.get("cumulative_expected_gain_pct"),
            "trends": trends.get("trends") or {},
            "validation_passed": validation.get("overall_passed"),
        }

    def phase_summary(self, issues: List[EngineeringIssue]) -> Dict[str, Any]:
        counts = Counter(i.originating_phase for i in issues)
        impact = {}
        for i in issues:
            impact[i.originating_phase] = round(
                impact.get(i.originating_phase, 0.0) + i.engineering_impact, 4
            )
        return {
            "model_version": MODEL_VERSION,
            "issue_counts_by_phase": dict(counts),
            "impact_sum_by_phase": impact,
            "primary_phase": counts.most_common(1)[0][0] if counts else None,
        }

    def severity_summary(self, issues: List[EngineeringIssue]) -> Dict[str, Any]:
        counts = Counter(i.severity for i in issues)
        return {
            "model_version": MODEL_VERSION,
            "counts": dict(counts),
            "critical": counts.get("Critical", 0),
            "major": counts.get("Major", 0),
            "moderate": counts.get("Moderate", 0),
            "minor": counts.get("Minor", 0),
            "informational": counts.get("Informational", 0),
        }

    def markdown(self, payload: Dict[str, Any]) -> str:
        issues: List[EngineeringIssue] = payload["issues"]
        rankings = payload["rankings"]
        backlog = payload["backlog"]
        trends = payload["trends"].get("trends") or {}
        validation = payload["validation"]
        rec = payload.get("recommendation", "B")

        lines = [
            "# Phase R.1.5 — Engineering Error Intelligence",
            "",
            f"**MODEL_VERSION:** {MODEL_VERSION}",
            f"**Recommendation:** {rec}",
            f"**Validation:** {validation.get('passed')}/{validation.get('total')}",
            f"**Overall production accuracy (from R.1.4):** {round(payload.get('overall_accuracy', 0)*100, 2)}%",
            f"**Steel gap:** {payload.get('steel_gap_kg')} kg",
            "",
            "## Executive Answer",
            "",
            "> What engineering problems should be solved first to maximize production accuracy?",
            "",
        ]
        for item in (backlog.get("items") or [])[:5]:
            lines.append(
                f"{item['priority']}. **{item['title']}** — expected gain "
                f"**{item['expected_accuracy_gain_pct']}%** "
                f"(phase: {item['recommended_phase']}, severity: {item['severity']})"
            )

        lines.extend(["", "## Top Engineering Problems", ""])
        for row in (rankings.get("rankings") or [])[:10]:
            lines.append(
                f"{row['rank']}. `{row['issue_id']}` {row['category']} / {row['subcategory']} — "
                f"impact {row['engineering_impact']}, freq {row['frequency']}, "
                f"steel {row['steel_impact_kg']} kg, conf {row['confidence']}"
            )

        lines.extend([
            "",
            "## Frequency / Severity / Phase",
            "",
            f"- Issues: **{len(issues)}** from **{payload.get('finding_count')}** findings",
            f"- Severity: `{payload['severity_summary'].get('counts')}`",
            f"- Phase attribution: `{payload['phase_summary'].get('issue_counts_by_phase')}`",
            "",
            "## Trends",
            "",
            f"- Top recurring: `{trends.get('top_recurring_issue')}`",
            f"- Largest steel loss: `{trends.get('largest_steel_loss')}`",
            f"- Most common missing reinforcement: `{trends.get('most_common_missing_reinforcement')}`",
            f"- Largest error source: `{trends.get('largest_source_of_production_error')}`",
            "",
            "## Regression",
            "",
            f"- Passed: `{payload['regression'].get('passed')}`",
            "",
            "---",
            f"*Phase R.1.5 | MODEL_VERSION {MODEL_VERSION}*",
            "",
        ])
        return "\n".join(lines)
