"""
semantic_reporter.py — Generate Markdown report for Phase R.2.1B.
MODEL_VERSION: 7.11.0
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


class SemanticReporter:

    def generate(
        self,
        statistics: Dict[str, Any],
        validation: Dict[str, Any],
        production_result: Dict[str, Any],
        model_version: str = "7.11.0",
    ) -> str:
        now = datetime.utcnow().isoformat()
        lines = [
            "# Phase R.2.1B — Engineering Semantic Interpreter",
            f"**MODEL_VERSION**: {model_version}  |  **Generated**: {now}",
            "",
            "---",
            "",
            "## 1. Architecture Summary",
            "",
            "Phase R.2.1B sits between the R.2.1A Semantic Dictionary and the",
            "EngineeringBarBuilder. It converts raw R.1 parsed annotations into",
            "structured `EngineeringSemanticObject`s with full engineering meaning.",
            "",
            "```",
            "DXF → R.1 Discovery → R.2.0 MTEXT → R.2.1A Dict → R.2.1B Interpreter",
            "    → EngineeringBarBuilder → EngineeringBarModel → Steel → BBS → Excel",
            "```",
            "",
            "## 2. Semantic Pipeline",
            "",
            "1. **SemanticContextBuilder** — gather annotation facts + dictionary lookup",
            "2. **SemanticModifierParser** — detect O.E.F., S.F.R., BOTH FACE, etc.",
            "3. **SemanticRoleResolver** — Explicit Modifier > Dictionary > Regex",
            "4. **SemanticQuantityResolver** — preserve qty without multiplication",
            "5. **SemanticPlacementResolver** — NEAR/FAR/BOTH/SIDE/TOP/BOTTOM",
            "6. **SemanticConflictResolver** — adjudicate, set confidence/source",
            "7. **EngineeringMeaningBuilder** — produce final EngineeringSemanticObject",
            "",
            "## 3. Statistics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total semantic objects | {statistics.get('total_semantic_objects', 0)} |",
            f"| Beams covered | {statistics.get('beams_covered', 0)} |",
            f"| UNKNOWN count | {statistics.get('unknown_count', 0)} |",
            f"| Role overrides | {statistics.get('role_overrides', 0)} |",
            f"| Objects with modifiers | {statistics.get('objects_with_modifiers', 0)} |",
            f"| Semantic coverage | {statistics.get('semantic_coverage_pct', 0):.1f}% |",
            f"| Dictionary coverage | {statistics.get('dictionary_coverage_pct', 0):.1f}% |",
            f"| Semantic confidence | {statistics.get('semantic_confidence_pct', 0):.1f}% |",
            "",
            "### 3a. Role Distribution",
            "",
        ]
        for role, count in (statistics.get("role_distribution") or {}).items():
            lines.append(f"- `{role}`: {count}")

        lines += [
            "",
            "### 3b. Meaning Distribution",
            "",
        ]
        for meaning, count in (statistics.get("meaning_distribution") or {}).items():
            lines.append(f"- `{meaning}`: {count}")

        lines += [
            "",
            "### 3c. Modifier Distribution",
            "",
        ]
        for mod, count in (statistics.get("modifier_distribution") or {}).items():
            lines.append(f"- `{mod}`: {count}")

        lines += [
            "",
            "### 3d. Placement Distribution",
            "",
        ]
        for place, count in (statistics.get("placement_distribution") or {}).items():
            lines.append(f"- `{place}`: {count}")

        lines += [
            "",
            "## 4. Validation Summary",
            "",
            f"**Result**: {validation.get('summary', '')}",
            "",
            "| Rule | Status | Detail |",
            "|------|--------|--------|",
        ]
        for rule_id, rule_data in (validation.get("rules") or {}).items():
            status = "✓" if rule_data.get("passed") else "✗"
            detail = rule_data.get("detail", "")
            rule_name = rule_data.get("detail", rule_id)[:60]
            lines.append(f"| {rule_id} | {status} {rule_data.get('status')} | {detail[:80]} |")

        lines += [
            "",
            "## 5. Pipeline Integration",
            "",
            "The semantic interpreter enriches R.1 beam models before",
            "EngineeringBarBuilder processes them. Role overrides are applied",
            "to the groups JSON so existing bar-building logic picks up",
            "the correct engineering role.",
            "",
        ]

        if production_result:
            steel = production_result.get("total_steel_kg", 0)
            beams = production_result.get("beams_reaching_steel", 0)
            bbs   = production_result.get("bbs_rows", 0)
            wb    = production_result.get("workbook_generated", False)
            lines += [
                "## 6. Production Run",
                "",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Steel weight (kg) | {steel:.1f} |",
                f"| Beams reaching steel | {beams} |",
                f"| BBS rows | {bbs} |",
                f"| Workbook generated | {'Yes' if wb else 'No'} |",
                "",
            ]

        lines += [
            "## 7. Remaining Engineering Limitations",
            "",
            "- Quantity multiplier for O.E.F. / BOTH FACE deferred to future calculation engine",
            "- Top/bottom placement for MAIN_BAR / EXTRA_BAR requires geometry context from R.3",
            "- Lap and development length semantic role detection is pattern-based (no equation)",
            "- UNKNOWN annotations without bar specs (e.g. label-only S.F.R. text) are not",
            "  counted as reinforcement — this is correct engineering behaviour",
            "",
            f"**MODEL_VERSION**: {model_version}",
        ]

        return "\n".join(lines)
