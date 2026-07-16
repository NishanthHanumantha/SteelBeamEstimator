"""STEP 5 — Classify reinforcement patterns."""
from __future__ import annotations

import re
from typing import Dict, List

from .regex_validation_models import RawTextEntity, RegexMatchResult

_CLASSIFIERS = [
    (re.compile(r"STIRRUP|@\d|2L[-\s]*Y", re.I), "STIRRUP"),
    (re.compile(r"SPACER|S\.P\.|SP\.", re.I), "SPACER"),
    (re.compile(r"S\.?\s*F\.?\s*R\.?", re.I), "SFR"),
    (re.compile(r"\bLd\b|Development|Anchor", re.I), "DEVELOPMENT"),
    (re.compile(r"\bLap\b", re.I), "LAP"),
    (re.compile(r"\bHook\b", re.I), "HOOK"),
    (re.compile(r"\bTOP\b|T\s*&\s*B", re.I), "TOP_BAR"),
    (re.compile(r"\bBOT\b", re.I), "BOTTOM_BAR"),
    (re.compile(r"EXTRA|ADD", re.I), "EXTRA_BAR"),
    (re.compile(r"O\.?\s*E\.?\s*F\.?", re.I), "SFR"),
]


class PatternClassifier:

    def classify(
        self,
        ent: RawTextEntity,
        match: RegexMatchResult,
        clean_text: str,
    ) -> str:
        combined = f"{ent.raw_text} {clean_text}"
        if match.matched:
            if match.regex_name == "RE_STIRRUP":
                return "STIRRUP"
            if match.regex_name == "RE_COMPOSITE":
                return "MAIN_BAR"
            if match.regex_name == "RE_BAR":
                if re.search(r"EXTRA|ADD", combined, re.I):
                    return "EXTRA_BAR"
                if re.search(r"\bTOP\b", combined, re.I):
                    return "TOP_BAR"
                if re.search(r"\bBOT\b", combined, re.I):
                    return "BOTTOM_BAR"
                return "MAIN_BAR"

        for rx, label in _CLASSIFIERS:
            if rx.search(combined):
                return label
        return "UNKNOWN"

    def apply_all(
        self,
        entities: List[RawTextEntity],
        matches: List[RegexMatchResult],
        clean_map: Dict[str, str],
    ) -> List[RegexMatchResult]:
        ent_by_id = {e.entity_id: e for e in entities}
        for m in matches:
            ent = ent_by_id[m.entity_id]
            m.classification = self.classify(
                ent, m, clean_map.get(m.entity_id, m.text)
            )
        return matches
