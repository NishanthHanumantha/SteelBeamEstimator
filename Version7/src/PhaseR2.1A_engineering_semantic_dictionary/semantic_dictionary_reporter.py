"""Markdown report for Phase R.2.1A."""
from __future__ import annotations

from typing import Any, Dict, List

from .semantic_dictionary_models import DictionaryEntry, SemanticDictionary


class SemanticDictionaryReporter:

    MODEL_VERSION = "7.10.0"

    def build_markdown(
        self,
        dictionary: SemanticDictionary,
        stats: Dict[str, Any],
        validation: Dict[str, Any],
    ) -> str:
        entries = list(dictionary.entries.values())
        high = sorted(
            [e for e in entries if e.priority == "HIGH"],
            key=lambda e: (-e.frequency, e.notation),
        )
        lines = [
            "# Phase R.2.1A — Engineering Semantic Dictionary",
            "",
            f"**MODEL_VERSION:** {self.MODEL_VERSION}",
            f"**Dictionary Version:** {dictionary.version.dictionary_version}",
            f"**Status:** {'PASS' if validation.get('all_passed') else 'FAIL'}",
            f"**Validation:** {validation.get('score')}",
            "",
            "## 1. Architecture Summary",
            "",
            "```",
            "Phase R.2.0.1 Inventory",
            "  -> NotationInventoryLoader",
            "  -> SemanticDictionaryBuilder + EngineeringVocabularyResolver",
            "  -> SemanticDictionaryValidator",
            "  -> SemanticDictionaryVersioning",
            "  -> SemanticDictionaryLoader API + Cache",
            "  -> Exports",
            "```",
            "",
            "READ-ONLY foundation. No parser consumption. Phase R.2.1B is first consumer.",
            "",
            "## 2. Dictionary Summary",
            "",
            f"- Entries: **{stats.get('unique_entries', 0)}**",
            f"- Inventory hash: `{stats.get('inventory_hash')}`",
            f"- Supported: {stats.get('supported')} | "
            f"Unsupported: {stats.get('unsupported')} | "
            f"Unknown: {stats.get('unknown')}",
            f"- Coverage (mapped meanings): **{stats.get('coverage_pct')}%**",
            f"- Vocabulary completeness: **{stats.get('vocabulary_completeness_pct')}%**",
            "",
            "## 3. Vocabulary Summary",
            "",
            f"- Vocabulary aliases: {stats.get('vocabulary_aliases')}",
            f"- Unsupported with mapped meaning: {stats.get('unsupported_with_meaning')}",
            f"- High-priority entries: {stats.get('high_priority_entries')}",
            "",
            "### High-Priority Vocabulary",
            "",
        ]
        for e in high[:15]:
            lines.append(
                f"- `{e.notation}` → **{e.engineering_meaning}** "
                f"(role={e.engineering_role}, pos={e.position}, "
                f"mult={e.quantity_multiplier}, status={e.support_status})"
            )

        lines.extend([
            "",
            "## 4. Category Distribution",
            "",
        ])
        for cat, n in sorted(stats.get("categories", {}).items(), key=lambda x: -x[1]):
            lines.append(f"- **{cat}**: {n}")

        lines.extend([
            "",
            "## 5. Engineering Meaning Distribution",
            "",
        ])
        for m, n in sorted(
            stats.get("meaning_distribution", {}).items(), key=lambda x: -x[1]
        ):
            lines.append(f"- **{m}**: {n}")

        lines.extend([
            "",
            "## 6. Priority Distribution",
            "",
        ])
        for p, n in sorted(stats.get("priority_distribution", {}).items()):
            lines.append(f"- **{p}**: {n}")

        lines.extend([
            "",
            "## 7. Dictionary Statistics",
            "",
            f"- Role distribution: `{stats.get('role_distribution')}`",
            f"- Position distribution: `{stats.get('position_distribution')}`",
            f"- Ready for R.2.1B: **{stats.get('ready_for_r21b')}**",
            "",
            "## 8. Validation Summary",
            "",
        ])
        for rid, rule in sorted(validation.get("rules", {}).items()):
            lines.append(f"- **{rid}**: {rule['status']} — {rule['detail']}")

        lines.extend([
            "",
            "## 9. Exports",
            "",
            "See `Version7/data/output/PhaseR2.1A_engineering_semantic_dictionary/`.",
            "",
            "## 10. Recommendations",
            "",
            "1. Phase R.2.1B should consume `SemanticDictionaryLoader` exclusively.",
            "2. Add new engineering conventions via YAML vocabulary aliases — not Python.",
            "3. Re-run R.2.0.1 then R.2.1A when new benchmark drawings are introduced.",
            "4. Do not wire this dictionary into production parsers until R.2.1B.",
            "",
        ])
        return "\n".join(lines)
