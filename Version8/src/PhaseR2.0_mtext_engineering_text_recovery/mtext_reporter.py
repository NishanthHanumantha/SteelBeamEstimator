"""MTEXT recovery markdown report."""
from __future__ import annotations

from typing import Any, Dict, List


class MtextReporter:

    MODEL_VERSION = "7.9.0"

    def build_markdown(
        self,
        stats: Dict[str, Any],
        validation: Dict[str, Any],
        regression: Dict[str, Any],
        unsupported: List[str],
    ) -> str:
        lines = [
            "# Phase R.2.0 — MTEXT Engineering Text Recovery",
            "",
            f"**MODEL_VERSION:** {self.MODEL_VERSION}",
            f"**Status:** {'PASS' if validation.get('all_passed') else 'FAIL'}",
            f"**Validation:** {validation.get('score')}",
            "",
            "## Engineering Report",
            "",
            f"1. Total MTEXT entities: **{stats.get('total_mtext', 0)}**",
            f"2. Containing engineering information: **{stats.get('engineering_preserved', 0)}**",
            f"3. Previously lost engineering text: **{stats.get('previously_lost', 0)}**",
            f"4. Now recovered: **{stats.get('recovered', 0)}**",
            f"5. Formatting commands removed: **{stats.get('formatting_tokens_removed', 0)}**",
            f"6. Engineering abbreviations preserved: see engineering_text_validation.json",
            f"7. Y10 annotations recovered: **{regression.get('y10_recovered', 0)}**",
            f"8. Brace-block annotations recovered: **{stats.get('recovered', 0)}**",
            f"9. Backward compatibility maintained: **{stats.get('backward_compat_pct', 100.0)}%**",
            f"10. Remaining unsupported: **{len(unsupported)}**",
            "",
            "## Recovery Statistics",
            "",
            f"- Recovery %: {stats.get('recovery_pct')}%",
            f"- Backward compatibility: {stats.get('backward_compat_pct')}%",
            f"- Regex match before: {stats.get('regex_match_before')}",
            f"- Regex match after: {stats.get('regex_match_after')}",
            "",
            "## Y10 Regression Test",
            "",
        ]

        y10 = regression.get("y10_tests", [])
        for t in y10:
            lines.append(f"- Raw: `{t.get('raw', '')[:80]}`")
            lines.append(f"  - Old clean: `{t.get('old_clean', '')}`")
            lines.append(f"  - New clean: `{t.get('new_clean', '')}`")
            lines.append(f"  - Status: **{t.get('status')}**")
            lines.append(f"  - Regex match: {t.get('regex_match')}")

        lines.extend([
            "",
            "## Pipeline Integration",
            "",
            "- `beam_detail_segmenter._strip_mtext()` → replaced with `EngineeringTextRecovery.clean()`",
            "- `RE_BAR`, `RE_STIRRUP`, `RE_COMPOSITE` → unchanged",
            "- `EngineeringBarBuilder` → unchanged",
            "- `SteelWeight`, `BBS`, `Excel` → unchanged",
            "",
            "## Validation Rules",
            "",
        ])
        for rid, rule in sorted(validation.get("rules", {}).items()):
            lines.append(f"- **{rid}**: {rule['status']} — {rule['detail']}")

        lines.extend([
            "",
            "## Remaining Unsupported (Phase R.2.1)",
            "",
        ])
        for item in unsupported:
            lines.append(f"- {item}")

        lines.extend([
            "",
            "## Architecture",
            "",
            "The engineering text recovery inserts a new preprocessing step before regex matching:",
            "",
            "```",
            "DXF MTEXT",
            "  -> EngineeringTextRecovery.clean()  [Phase R.2.0]",
            "     -> Open brace blocks, strip inner formatting, preserve engineering text",
            "     -> Strip remaining format codes (original production logic)",
            "  -> RE_BAR / RE_STIRRUP / RE_COMPOSITE  [unchanged]",
            "  -> AnnotationDiscovery  [unchanged]",
            "  -> EngineeringBarModel  [unchanged]",
            "```",
        ])
        return "\n".join(lines)
