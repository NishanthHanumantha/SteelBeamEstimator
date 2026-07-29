"""Markdown report for Phase R.2.0.1."""
from __future__ import annotations

from typing import Any, Dict, List

from .notation_models import PriorityItem, VocabularyEntry


class NotationReporter:

    MODEL_VERSION = "7.9.1"

    def build_markdown(
        self,
        stats: Dict[str, Any],
        validation: Dict[str, Any],
        entries: List[VocabularyEntry],
        priorities: List[PriorityItem],
        unsupported: List[VocabularyEntry],
    ) -> str:
        lines = [
            "# Phase R.2.0.1 — Engineering Notation Semantic Inventory",
            "",
            f"**MODEL_VERSION:** {self.MODEL_VERSION}",
            f"**Status:** {'PASS' if validation.get('all_passed') else 'FAIL'}",
            f"**Validation:** {validation.get('score')}",
            "",
            "## 1. Architecture",
            "",
            "READ-ONLY discovery pipeline:",
            "",
            "```",
            "DXF TEXT/MTEXT/ATTRIB/ATTDEF",
            "  -> NotationInventoryLoader (R.2.0 MTEXT recovery, read-only)",
            "  -> NotationExtractor",
            "  -> NotationNormalizer",
            "  -> NotationPatternGrouper",
            "  -> EngineeringSymbolDetector",
            "  -> SemanticCategoryClassifier",
            "  -> NotationSupportAnalyzer (production regex check, read-only)",
            "  -> NotationInventoryDatabase",
            "  -> Coverage Statistics + R.2.1 Priorities",
            "```",
            "",
            "No production parser, regex, calculation, or semantic interpretation was modified.",
            "",
            "## 2. Notation Inventory",
            "",
            f"- Total DXF entities: **{stats.get('total_dxf_entities', 0)}**",
            f"- Entity types: `{stats.get('entity_type_counts', {})}`",
            f"- Unique notations: **{stats.get('total_unique_notations', 0)}**",
            f"- Total occurrences: **{stats.get('total_occurrences', 0)}**",
            f"- Engineering symbols discovered: **{stats.get('engineering_symbols_discovered', 0)}**",
            "",
            "## 3. Category Distribution",
            "",
        ]
        unique_counts = stats.get("category_distribution", {}).get("unique_counts", {})
        for cat, n in sorted(unique_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- **{cat}**: {n} unique")

        lines.extend([
            "",
            "## 4. Support Distribution",
            "",
            f"- Supported: **{stats.get('supported_pct')}%** "
            f"({stats.get('support_distribution', {}).get('SUPPORTED', 0)})",
            f"- Partially Supported: **{stats.get('partially_supported_pct')}%** "
            f"({stats.get('support_distribution', {}).get('PARTIALLY_SUPPORTED', 0)})",
            f"- Unsupported: **{stats.get('unsupported_pct')}%** "
            f"({stats.get('support_distribution', {}).get('UNSUPPORTED', 0)})",
            f"- Unknown: **{stats.get('unknown_pct')}%** "
            f"({stats.get('support_distribution', {}).get('UNKNOWN', 0)})",
            "",
            "## 5. Engineering Vocabulary (Top 20 by Frequency)",
            "",
        ])
        for e in entries[:20]:
            lines.append(
                f"- `{e.notation}` — freq={e.frequency}, "
                f"cat={e.category}, status={e.support_status}"
            )

        lines.extend([
            "",
            "## 6. Coverage Statistics",
            "",
            f"- Symbol families: {', '.join(stats.get('symbol_families', [])[:20])}",
            "",
            "### Most Common Unsupported",
            "",
        ])
        for item in stats.get("most_common_unsupported", [])[:15]:
            lines.append(
                f"- `{item.get('notation')}` — freq={item.get('frequency')} "
                f"({item.get('reason', '')})"
            )

        lines.extend([
            "",
            "## 7. Unsupported Engineering Symbols",
            "",
        ])
        for e in unsupported[:25]:
            if e.is_engineering_symbol or e.category in (
                "REINFORCEMENT_ROLE", "MODIFIER", "DEVELOPMENT", "POSITION"
            ):
                lines.append(
                    f"- **{e.notation}** [{e.category}] freq={e.frequency} — {e.support_reason}"
                )

        lines.extend([
            "",
            "## 8. Implementation Priorities (Phase R.2.1)",
            "",
        ])
        for p in priorities:
            lines.append(
                f"{p.priority}. **{p.notation}** — Impact: {p.impact} "
                f"(freq={p.frequency}) — {p.reason}"
            )

        lines.extend([
            "",
            "## 9. Validation",
            "",
        ])
        for rid, rule in sorted(validation.get("rules", {}).items()):
            lines.append(f"- **{rid}**: {rule['status']} — {rule['detail']}")

        lines.extend([
            "",
            "## 10. Recommendations",
            "",
            "1. Use this vocabulary database as the complete input set for Phase R.2.1.",
            "2. Implement HIGH-impact unsupported symbols first (S.F.R., O.E.F., face phrases).",
            "3. Do not incrementally invent semantics outside this inventory.",
            "4. Re-run this phase after new benchmark drawings are added.",
            "",
        ])
        return "\n".join(lines)
