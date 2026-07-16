"""STEP 12-13 — Coverage scores and root cause classification."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .regex_validation_models import (
    EngineeringNotationRecord,
    MtextCleaningRecord,
    PatternRecord,
    RegexMatchResult,
)


class RegexCoverageAnalyzer:

    def analyze(
        self,
        patterns: List[PatternRecord],
        matches: List[RegexMatchResult],
        clean_map: Dict[str, MtextCleaningRecord],
        eng_records: List[EngineeringNotationRecord],
        unsupported: List[Dict],
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        reinf_candidates = stats.get("reinforcement_candidates", 0)
        matched = stats.get("regex_matched", 0)
        cleaning_fail = stats.get("cleaning_failures", 0)
        regex_fail = stats.get("regex_failures", stats.get("regex_failed", 0))
        semantic_fail = stats.get("semantic_failures", 0)

        supported_patterns = sum(
            1 for p in patterns
            if p.pattern in ("N-YD", "YD@S", "NL-YD@S", "N-YD@S", "N-YD+MYD", "YD")
        )
        unique_patterns = len(patterns)
        unsupported_count = len(unsupported)

        pattern_cov = round(
            100.0 * supported_patterns / unique_patterns, 2
        ) if unique_patterns else 0.0
        regex_cov = round(
            100.0 * matched / reinf_candidates, 2
        ) if reinf_candidates else 0.0
        eng_preserved = sum(1 for e in eng_records if e.preserved)
        eng_cov = round(
            100.0 * eng_preserved / len(eng_records), 2
        ) if eng_records else 100.0
        cleaning_ok = sum(
            1 for c in clean_map.values()
            if not c.entire_annotation_removed
        )
        cleaning_acc = round(
            100.0 * cleaning_ok / len(clean_map), 2
        ) if clean_map else 100.0
        semantic_acc = round(
            100.0 * (matched - semantic_fail) / matched, 2
        ) if matched else 100.0

        parser_readiness = round(
            (pattern_cov + regex_cov + eng_cov + cleaning_acc + semantic_acc) / 5.0, 2
        )

        root_causes = self._classify_root_causes(matches, clean_map, eng_records)

        return {
            "pattern_coverage_pct": pattern_cov,
            "regex_coverage_pct": regex_cov,
            "engineering_coverage_pct": eng_cov,
            "cleaning_accuracy_pct": cleaning_acc,
            "semantic_accuracy_pct": semantic_acc,
            "parser_readiness_score": parser_readiness,
            "total_reinforcement_annotations": reinf_candidates,
            "supported_patterns": supported_patterns,
            "unsupported_patterns": unsupported_count,
            "unique_patterns": unique_patterns,
            "regex_success": matched,
            "regex_failures": regex_fail,
            "cleaning_failures": cleaning_fail,
            "semantic_failures": semantic_fail,
            "overall_coverage_pct": regex_cov,
            "root_cause_counts": dict(root_causes),
        }

    def _classify_root_causes(
        self,
        matches: List[RegexMatchResult],
        clean_map: Dict[str, MtextCleaningRecord],
        eng_records: List[EngineeringNotationRecord],
    ) -> Counter:
        causes: Counter = Counter()
        for m in matches:
            if m.matched:
                continue
            cause = m.root_cause or "UNKNOWN"
            cleaning = clean_map.get(m.entity_id)
            if cleaning and cleaning.status == "ENGINEERING_TEXT_LOST":
                cause = "ENGINEERING_TEXT_LOST"
            elif cleaning and cleaning.entire_annotation_removed:
                cause = "MTEXT_CLEANING"
            elif cause == "REGEX_UNSUPPORTED":
                cause = "REGEX_UNSUPPORTED"
            elif cause == "PATTERN_UNSUPPORTED":
                cause = "PATTERN_UNSUPPORTED"
            causes[cause] += 1

        for e in eng_records:
            if not e.preserved:
                causes[e.root_cause or "SEMANTIC_UNKNOWN"] += 1

        return causes
