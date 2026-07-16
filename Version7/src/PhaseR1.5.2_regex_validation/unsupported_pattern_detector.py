"""STEP 6 — Detect patterns in DXF unsupported by production regex."""
from __future__ import annotations

import re
from typing import Dict, List, Set

from .regex_validation_models import PatternRecord, RawTextEntity, RegexMatchResult

# Patterns that exist in DXF but production regex cannot parse
_UNSUPPORTED_SIGNATURES = [
    (re.compile(r"S\.?\s*F\.?\s*R\.?", re.I), "S.F.R."),
    (re.compile(r"O\.?\s*E\.?\s*F\.?", re.I), "O.E.F."),
    (re.compile(r"2L[-\s]*Y\s*10", re.I), "2L-Y10"),
    (re.compile(r"2L[-\s]*Y\s*10\s*@\s*\d+/\d+/\d+", re.I), "2L-Y10@100/100/100"),
    (re.compile(r"Ld\s*\+\s*\d+\s*db", re.I), "Ld+10db"),
    (re.compile(r"\d+[-\s]*Y\s*10\s*\([^)]+\)", re.I), "N-Y10(PAREN)"),
    (re.compile(r"\{[^}]*Y\s*10[^}]*\}", re.I), "MTEXT_BRACE_Y10"),
    (re.compile(r"SPACER|S\.P\.", re.I), "SPACER_NOTATION"),
    (re.compile(r"\d+/\d+/\d+", re.I), "ZONE_SPACING_RATIO"),
]


class UnsupportedPatternDetector:

    def detect(
        self,
        entities: List[RawTextEntity],
        matches: List[RegexMatchResult],
        patterns: List[PatternRecord],
    ) -> List[Dict]:
        match_by_id = {m.entity_id: m for m in matches}
        unsupported: List[Dict] = []
        seen: Set[str] = set()

        for ent in entities:
            text = f"{ent.raw_text}"
            clean_match = match_by_id.get(ent.entity_id)
            if clean_match and clean_match.matched:
                continue

            for rx, label in _UNSUPPORTED_SIGNATURES:
                if not rx.search(text):
                    continue
                key = f"{label}|{text[:80]}"
                if key in seen:
                    continue
                seen.add(key)
                unsupported.append({
                    "pattern_type": label,
                    "entity_id": ent.entity_id,
                    "entity_type": ent.entity_type,
                    "raw_text": text[:200],
                    "clean_text": clean_match.text if clean_match else "",
                    "nearest_beam_id": ent.nearest_beam_id,
                    "root_cause": clean_match.root_cause if clean_match else "UNKNOWN",
                    "recommendation": self._recommendation(label),
                })

        # Add pattern inventory items with zero regex support
        pattern_labels = {p.pattern for p in patterns}
        structural = {"S.F.R.", "O.E.F.", "Ld", "Lap", "Spacer", "Hook", "Development"}
        for label in structural:
            if label in pattern_labels:
                if not any(u["pattern_type"] == label for u in unsupported):
                    unsupported.append({
                        "pattern_type": label,
                        "entity_id": "PATTERN_INVENTORY",
                        "entity_type": "INVENTORY",
                        "raw_text": "",
                        "clean_text": "",
                        "nearest_beam_id": "",
                        "root_cause": "REGEX_UNSUPPORTED",
                        "recommendation": self._recommendation(label),
                        "frequency": next(
                            (p.frequency for p in patterns if p.pattern == label), 0
                        ),
                    })

        return unsupported

    @staticmethod
    def _recommendation(label: str) -> str:
        recs = {
            "S.F.R.": "Parse side-face reinforcement role before bar quantity",
            "O.E.F.": "Parse 'One Each Face' quantity modifier",
            "2L-Y10": "Extend stirrup regex for 2L-Y10 without spacing",
            "2L-Y10@100/100/100": "Support zone-split stirrup spacing ratios",
            "Ld+10db": "Add development length notation parser",
            "N-Y10(PAREN)": "Preserve parenthetical modifiers in bar regex",
            "MTEXT_BRACE_Y10": "Fix _strip_mtext to preserve inner brace text",
            "SPACER_NOTATION": "Add spacer bar discovery regex",
            "ZONE_SPACING_RATIO": "Parse multi-zone stirrup spacing",
        }
        return recs.get(label, f"Add regex support for {label}")
