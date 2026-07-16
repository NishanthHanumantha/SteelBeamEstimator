"""STEP 4 — Validate every text against production regex (read-only)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .production_regex_loader import get_production_patterns
from .regex_validation_models import MtextCleaningRecord, RawTextEntity, RegexMatchResult


class RegexMatchValidator:

    def __init__(self):
        patterns = get_production_patterns()
        self._re_bar = patterns["RE_BAR"]
        self._re_stirrup = patterns["RE_STIRRUP"]
        self._re_composite = patterns["RE_COMPOSITE"]
        self._is_noise = patterns["is_noise"]

    def validate_entity(
        self,
        ent: RawTextEntity,
        cleaning: MtextCleaningRecord,
    ) -> RegexMatchResult:
        clean = cleaning.cleaned_text
        if not clean:
            return RegexMatchResult(
                entity_id=ent.entity_id,
                text=clean,
                matched=False,
                regex_name="NONE",
                captured_groups={},
                failure_reason="EMPTY_AFTER_CLEANING",
                root_cause="MTEXT_CLEANING" if ent.entity_type == "MTEXT" else "FORMATTING_REMOVED",
            )

        if self._is_noise(clean):
            return RegexMatchResult(
                entity_id=ent.entity_id,
                text=clean,
                matched=False,
                regex_name="NOISE_FILTER",
                captured_groups={},
                failure_reason="NOISE_PATTERN_MATCH",
                root_cause="PATTERN_UNSUPPORTED",
            )

        if re.match(r"^B\d+\w*\s*[\(\[]?\d*[xX]?\d*[\)\]]?", clean, re.I):
            return RegexMatchResult(
                entity_id=ent.entity_id,
                text=clean,
                matched=False,
                regex_name="BEAM_LABEL_SKIP",
                captured_groups={},
                failure_reason="BEAM_LABEL",
                root_cause="PATTERN_UNSUPPORTED",
            )

        return self._match_clean_text(ent.entity_id, clean)

    def _match_clean_text(self, entity_id: str, clean: str) -> RegexMatchResult:
        m_comp = self._re_composite.match(clean)
        if m_comp:
            return self._build_result(
                entity_id, clean, "RE_COMPOSITE", m_comp,
                qty=int(m_comp.group(1)), dia=float(m_comp.group(3)),
                modifier=f"+{m_comp.group(4)}{m_comp.group(5)}{m_comp.group(6)}",
            )

        m_stir = self._re_stirrup.search(clean)
        if m_stir:
            legs = int(m_stir.group(1)) if m_stir.group(1) else 2
            return self._build_result(
                entity_id, clean, "RE_STIRRUP", m_stir,
                qty=legs, dia=float(m_stir.group(3)),
                spacing=m_stir.group(4),
            )

        m_bar = self._re_bar.search(clean)
        if m_bar:
            return self._build_result(
                entity_id, clean, "RE_BAR", m_bar,
                qty=int(m_bar.group(1)), dia=float(m_bar.group(3)),
            )

        return RegexMatchResult(
            entity_id=entity_id,
            text=clean,
            matched=False,
            regex_name="NONE",
            captured_groups={},
            failure_reason="NO_REGEX_MATCH",
            root_cause="REGEX_UNSUPPORTED",
        )

    def validate_all(
        self,
        entities: List[RawTextEntity],
        clean_map: Dict[str, MtextCleaningRecord],
    ) -> List[RegexMatchResult]:
        return [
            self.validate_entity(ent, clean_map[ent.entity_id])
            for ent in entities
        ]

    @staticmethod
    def _build_result(
        entity_id: str,
        clean: str,
        regex_name: str,
        match,
        qty: Optional[int] = None,
        dia: Optional[float] = None,
        spacing: Optional[str] = None,
        modifier: Optional[str] = None,
    ) -> RegexMatchResult:
        groups = {f"g{i}": match.group(i) for i in range(1, match.lastindex + 1)}
        return RegexMatchResult(
            entity_id=entity_id,
            text=clean,
            matched=True,
            regex_name=regex_name,
            captured_groups=groups,
            parsed_quantity=qty,
            parsed_diameter=dia,
            parsed_spacing=spacing,
            parsed_modifier=modifier,
            root_cause="",
        )
