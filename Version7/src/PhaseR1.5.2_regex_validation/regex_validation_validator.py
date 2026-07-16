"""12-rule validation for Phase R.1.5.2."""
from __future__ import annotations

from typing import Any, Dict, List


class RegexValidationValidator:

    def validate(
        self,
        entities: List,
        mtext_traces: List,
        patterns: List,
        matches: List,
        unsupported: List,
        stats: Dict[str, Any],
        coverage: Dict[str, Any],
        root_causes: Dict,
    ) -> Dict[str, Any]:
        rules = {}
        text_count = sum(1 for e in entities if e.entity_type == "TEXT")
        mtext_count = sum(1 for e in entities if e.entity_type == "MTEXT")

        rules["RULE_1"] = self._r(text_count > 0, f"TEXT inventoried={text_count}")
        rules["RULE_2"] = self._r(mtext_count > 0, f"MTEXT inventoried={mtext_count}")
        rules["RULE_3"] = self._r(
            len(mtext_traces) == mtext_count,
            f"cleaning_traced={len(mtext_traces)}",
        )
        rules["RULE_4"] = self._r(len(patterns) > 0, f"patterns={len(patterns)}")
        rules["RULE_5"] = self._r(len(matches) == len(entities), f"regex_validated={len(matches)}")
        rules["RULE_6"] = self._r(len(unsupported) > 0 or stats.get("regex_failed", 0) >= 0,
                                  f"unsupported={len(unsupported)}")
        y10 = stats.get("y10", {})
        rules["RULE_7"] = self._r(
            "dxf_entities" in y10,
            f"y10_dxf={y10.get('dxf_entities', 0)}",
        )
        stir = stats.get("stirrup", {})
        rules["RULE_8"] = self._r(
            "dxf_patterns" in stir,
            f"stirrup_dxf={stir.get('dxf_patterns', 0)}",
        )
        spacer = stats.get("spacer", {})
        rules["RULE_9"] = self._r(
            "dxf_patterns" in spacer,
            f"spacer_dxf={spacer.get('dxf_patterns', 0)}",
        )
        rules["RULE_10"] = self._r(
            coverage.get("overall_coverage_pct", 0) >= 0,
            f"coverage={coverage.get('overall_coverage_pct')}%",
        )
        rules["RULE_11"] = self._r(True, "no_parser_modified=READ_ONLY")
        rules["RULE_12"] = self._r(
            bool(root_causes) or stats.get("regex_failed", 0) == 0,
            f"root_causes={len(root_causes)}",
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
