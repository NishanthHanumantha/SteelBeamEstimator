"""STEP 7 — Engineering notation semantic validation."""
from __future__ import annotations

import re
from typing import Dict, List

from .regex_validation_models import (
    EngineeringNotationRecord,
    MtextCleaningRecord,
    RawTextEntity,
    RegexMatchResult,
)


class EngineeringNotationValidator:

    _SFR = re.compile(r"S\.?\s*F\.?\s*R\.?", re.I)
    _OEF = re.compile(r"O\.?\s*E\.?\s*F\.?", re.I)
    _BAR = re.compile(r"(\d+)\s*[-–]?\s*Y\s*(\d+)", re.I)
    _STIRRUP = re.compile(
        r"(?:(\d+)\s*L[-\s]*)?Y\s*(\d+)\s*@\s*(\d+(?:/\d+)*)", re.I
    )

    def validate_all(
        self,
        entities: List[RawTextEntity],
        clean_map: Dict[str, MtextCleaningRecord],
        matches: Dict[str, RegexMatchResult],
    ) -> List[EngineeringNotationRecord]:
        records = []
        for ent in entities:
            cleaning = clean_map[ent.entity_id]
            match = matches[ent.entity_id]
            meaning = self._infer_meaning(ent.raw_text, cleaning.cleaned_text)
            if not meaning:
                continue
            preserved = self._meaning_preserved(meaning, match, cleaning)
            status = "PARSED" if preserved else "FAILED"
            root = match.root_cause or ("SEMANTIC_UNKNOWN" if not preserved else "")
            records.append(EngineeringNotationRecord(
                entity_id=ent.entity_id,
                raw_text=ent.raw_text[:200],
                cleaned_text=cleaning.cleaned_text[:200],
                engineering_meaning=meaning,
                parser_status=status,
                preserved=preserved,
                root_cause=root,
            ))
        return records

    def _infer_meaning(self, raw: str, cleaned: str) -> str:
        parts = []
        text = raw or cleaned
        if self._SFR.search(text):
            parts.append("Side Face Reinforcement")
        if self._OEF.search(text):
            parts.append("One Each Face")
        m_bar = self._BAR.search(cleaned) or self._BAR.search(raw)
        if m_bar:
            parts.append(f"{m_bar.group(1)} bars Y{m_bar.group(2)}")
        m_stir = self._STIRRUP.search(cleaned) or self._STIRRUP.search(raw)
        if m_stir:
            legs = m_stir.group(1) or "2"
            parts.append(f"{legs}L-Y{m_stir.group(2)}@{m_stir.group(3)} stirrup")
        if re.search(r"SPACER|S\.P\.", text, re.I):
            parts.append("Spacer/support bar")
        if re.search(r"\bLd\b", text, re.I):
            parts.append("Development length notation")
        if re.search(r"\bLap\b", text, re.I):
            parts.append("Lap splice notation")
        return "; ".join(parts)

    @staticmethod
    def _meaning_preserved(
        meaning: str,
        match: RegexMatchResult,
        cleaning: MtextCleaningRecord,
    ) -> bool:
        if cleaning.entire_annotation_removed or cleaning.status == "ENGINEERING_TEXT_LOST":
            return False
        if not match.matched:
            return False
        if "Side Face" in meaning and match.classification not in ("SFR", "MAIN_BAR", "STIRRUP"):
            if match.regex_name == "RE_BAR":
                return True
            return False
        return True
