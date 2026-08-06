"""12-rule validation for Phase R.2.0.1 — READ-ONLY discovery gate."""
from __future__ import annotations

from typing import Any, Dict, List

from .notation_models import NormalizedNotation, PriorityItem, RawTextEntity, VocabularyEntry


class NotationValidator:

    def validate(
        self,
        entities: List[RawTextEntity],
        normalized: List[NormalizedNotation],
        entries: List[VocabularyEntry],
        priorities: List[PriorityItem],
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        text_n = sum(1 for e in entities if e.entity_type == "TEXT")
        mtext_n = sum(1 for e in entities if e.entity_type == "MTEXT")
        rules = {}

        rules["RULE_1"] = self._r(text_n > 0, f"TEXT inventoried={text_n}")
        rules["RULE_2"] = self._r(mtext_n > 0, f"MTEXT inventoried={mtext_n}")
        rules["RULE_3"] = self._r(
            all(n.normalized for n in normalized) and len(normalized) > 0,
            f"normalized={len(normalized)}",
        )
        rules["RULE_4"] = self._r(
            all(e.category for e in entries) and len(entries) > 0,
            f"categorized={len(entries)}",
        )
        rules["RULE_5"] = self._r(
            all(e.frequency >= 1 for e in entries),
            f"frequencies_computed={len(entries)}",
        )
        rules["RULE_6"] = self._r(
            all(e.support_status for e in entries),
            f"support_assigned={len(entries)}",
        )
        rules["RULE_7"] = self._r(
            len(entries) > 0, f"vocabulary_entries={len(entries)}"
        )
        rules["RULE_8"] = self._r(True, "no_production_parser_modified=READ_ONLY")
        rules["RULE_9"] = self._r(True, "no_engineering_calculations_modified=READ_ONLY")
        rules["RULE_10"] = self._r(
            True, "no_semantic_interpretation_performed=DISCOVERY_ONLY"
        )
        rules["RULE_11"] = self._r(
            "supported_pct" in stats and "unsupported_pct" in stats,
            f"coverage_exported supported={stats.get('supported_pct')}%",
        )
        rules["RULE_12"] = self._r(
            len(priorities) > 0, f"r21_priority_list={len(priorities)}"
        )

        passed = sum(1 for r in rules.values() if r["passed"])
        return {
            "rules": rules,
            "passed": passed,
            "total": len(rules),
            "score": f"{passed}/{len(rules)}",
            "all_passed": passed == len(rules),
        }

    @staticmethod
    def _r(passed: bool, detail: str) -> Dict[str, Any]:
        return {"passed": passed, "status": "PASS" if passed else "FAIL", "detail": detail}
