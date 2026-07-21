"""
Markdown report for Phase R.1.6.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from engineering_rule_model import EngineeringRule

MODEL_VERSION = "8.8.0"


class ReportGenerator:
    def markdown(self, payload: Dict[str, Any]) -> str:
        rules: List[EngineeringRule] = payload["rules"]
        roadmap = payload["roadmap"]
        patterns = payload["patterns"]
        deps = payload["dependencies"]
        conflicts = payload["conflicts"]
        validation = payload["validation"]
        rec = payload.get("recommendation", "B")

        fam_counts = Counter(r.rule_family for r in rules)
        gap_counts = Counter(r.gap_type for r in rules)

        lines = [
            "# Phase R.1.6 — Engineering Rule Synthesis & Gap Resolution",
            "",
            f"**MODEL_VERSION:** {MODEL_VERSION}",
            f"**Recommendation:** {rec}",
            f"**Validation:** {validation.get('passed')}/{validation.get('total')}",
            "",
            "## Executive Answer",
            "",
            "> Which deterministic engineering rule is missing, incomplete, or incorrect?",
            "",
        ]
        for item in (roadmap.get("items") or [])[:5]:
            lines.append(
                f"{item['priority']}. **{item['rule_id']}** {item['rule_name']} "
                f"({item['gap_type']}) — gain **{item['expected_accuracy_gain_pct']}%**, "
                f"phase {item['implementation_phase']}"
            )

        lines.extend([
            "",
            "## Rule Statistics",
            "",
            f"- Rules in library: **{len(rules)}**",
            f"- Families: `{dict(fam_counts)}`",
            f"- Gap types: `{dict(gap_counts)}`",
            f"- Patterns consolidated: **{patterns.get('pattern_count')}**",
            f"- Dependency edges: **{deps.get('edge_count')}** (acyclic={deps.get('acyclic')})",
            f"- Conflicts: **{conflicts.get('conflict_count')}** (hard={conflicts.get('hard_conflict_count')})",
            "",
            "## Implementation Roadmap",
            "",
        ])
        for item in roadmap.get("items") or []:
            lines.append(
                f"{item['priority']}. `{item['rule_id']}` {item['rule_family']} — "
                f"+{item['expected_accuracy_gain_pct']}% / {item['estimated_steel_gain_kg']} kg "
                f"(deps={item['dependencies']}, risk={item['engineering_risk']})"
            )

        lines.extend([
            "",
            f"- Cumulative expected gain (attributed, overlapping): **{roadmap.get('cumulative_expected_gain_pct')}%**",
            f"- Cumulative steel gain (attributed): **{roadmap.get('cumulative_steel_gain_kg')} kg**",
            "",
            "## Regression",
            "",
            f"- Passed: `{payload['regression'].get('passed')}`",
            "",
            "---",
            f"*Phase R.1.6 | MODEL_VERSION {MODEL_VERSION}*",
            "",
        ])
        return "\n".join(lines)
