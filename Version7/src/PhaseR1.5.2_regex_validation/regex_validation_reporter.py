"""Forensic regex validation report generator."""
from __future__ import annotations

from typing import Any, Dict, List


class RegexValidationReporter:

    MODEL_VERSION = "7.8.3"

    def build_markdown(
        self,
        stats: Dict[str, Any],
        coverage: Dict[str, Any],
        validation: Dict[str, Any],
        unsupported: List[Dict],
        y10: Dict[str, Any],
    ) -> str:
        stir = stats.get("stirrup", {})
        spacer = stats.get("spacer", {})
        lines = [
            "# Phase R.1.5.2 — Reinforcement Pattern Coverage & Regex Validation",
            "",
            f"**MODEL_VERSION:** {self.MODEL_VERSION}",
            f"**Status:** {'PASS' if validation.get('all_passed') else 'FAIL'}",
            f"**Validation:** {validation.get('score')}",
            "",
            "## Engineering Report",
            "",
            f"1. Reinforcement text entities: **{stats.get('total_dxf_entities', 0)}**",
            f"2. Unique reinforcement patterns: **{coverage.get('unique_patterns', 0)}**",
            f"3. Supported patterns: **{coverage.get('supported_patterns', 0)}**",
            f"4. Unsupported patterns: **{coverage.get('unsupported_patterns', 0)}**",
            f"5. MTEXT cleaning failures: **{coverage.get('cleaning_failures', 0)}**",
            f"6. Regex failures: **{coverage.get('regex_failures', 0)}**",
            f"7. Semantic failures: **{coverage.get('semantic_failures', 0)}**",
            f"8. Y10 annotations in DXF: **{y10.get('dxf_entities', 0)}**",
            f"9. Y10 parsed: **{y10.get('parsed', 0)}**",
            f"10. Stirrup patterns in DXF: **{stir.get('dxf_patterns', 0)}**",
            f"11. Stirrups parsed: **{stir.get('parsed', 0)}**",
            f"12. Spacer patterns in DXF: **{spacer.get('dxf_patterns', 0)}**",
            f"13. Spacers parsed: **{spacer.get('parsed', 0)}**",
            f"14. Parser coverage: **{coverage.get('overall_coverage_pct', 0)}%**",
            "",
            "## Coverage Scores",
            "",
            f"- Pattern Coverage: {coverage.get('pattern_coverage_pct')}%",
            f"- Regex Coverage: {coverage.get('regex_coverage_pct')}%",
            f"- Engineering Coverage: {coverage.get('engineering_coverage_pct')}%",
            f"- Cleaning Accuracy: {coverage.get('cleaning_accuracy_pct')}%",
            f"- Semantic Accuracy: {coverage.get('semantic_accuracy_pct')}%",
            f"- Parser Readiness Score: {coverage.get('parser_readiness_score')}",
            "",
            "## Y10 Coverage Audit",
            "",
        ]
        for item in y10.get("dxf_details", []):
            lines.append(f"- `{item.get('raw_text', '')[:80]}`")
            lines.append(f"  - Cleaned: `{item.get('cleaned_text', '')}`")
            lines.append(f"  - Matched: {item.get('matched')} ({item.get('regex_name')})")
            lines.append(f"  - Root cause: **{item.get('root_cause')}**")
            lines.append(f"  - Beam: {item.get('nearest_beam_id')}")

        lines.extend([
            "",
            "## Root Cause Summary",
            "",
        ])
        for cause, count in sorted(coverage.get("root_cause_counts", {}).items()):
            lines.append(f"- {cause}: {count}")

        lines.extend([
            "",
            "## Unsupported Engineering Notations (Phase R.2)",
            "",
        ])
        seen = set()
        for u in unsupported:
            key = u.get("pattern_type", "")
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- **{key}**: {u.get('recommendation', '')}")

        lines.extend([
            "",
            "## Validation Rules",
            "",
        ])
        for rid, rule in sorted(validation.get("rules", {}).items()):
            lines.append(f"- **{rid}**: {rule['status']} — {rule['detail']}")

        lines.extend([
            "",
            "## Recommended Parser Improvements (DO NOT IMPLEMENT)",
            "",
            "1. Fix `_strip_mtext()` to extract inner text from `{...}` MTEXT blocks before "
            "removing format codes.",
            "2. Add regex for `N-Y10(O.E.F)` parenthetical modifiers with S.F.R. role.",
            "3. Support `2L-Y10@100/100/100` zone-split stirrup spacing.",
            "4. Parse `Ld+10db` development length notation.",
            "5. Add spacer/pin bar discovery regex for SPACER annotations.",
            "6. Classify S.F.R. / O.E.F. as side-face reinforcement roles.",
            "",
            "*This phase is READ-ONLY. No parser modifications were applied.*",
        ])
        return "\n".join(lines)
