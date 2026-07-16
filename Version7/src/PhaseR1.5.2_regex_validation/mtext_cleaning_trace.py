"""STEP 2 — MTEXT cleaning trace using production _strip_mtext (read-only)."""
from __future__ import annotations

import re
from typing import Dict, List

from .production_regex_loader import get_mtext_code_pattern, get_strip_mtext
from .regex_validation_models import MtextCleaningRecord, RawTextEntity


class MtextCleaningTrace:

    _ENGINEERING_HINTS = re.compile(
        r"S\.?F\.?R\.?|O\.?E\.?F\.?|Ld|Lap|Spacer|Hook|Bend|Curtailment|"
        r"Development|Anchor|TYP\.?|T&B|BOT|TOP|Y\d+|R\d+",
        re.IGNORECASE,
    )

    def trace_all(self, entities: List[RawTextEntity]) -> List[MtextCleaningRecord]:
        records = []
        for ent in entities:
            if ent.entity_type != "MTEXT":
                continue
            records.append(self._trace_one(ent))
        return records

    def trace_entity(self, ent: RawTextEntity) -> MtextCleaningRecord:
        """Trace cleaning for any entity type (MTEXT gets full trace)."""
        if ent.entity_type == "MTEXT":
            return self._trace_one(ent)
        cleaned = ent.raw_text.strip()
        return MtextCleaningRecord(
            entity_id=ent.entity_id,
            entity_type=ent.entity_type,
            raw_text=ent.raw_text,
            cleaned_text=cleaned,
            characters_removed=0,
            loss_pct=0.0,
            status="NOT_MTEXT",
            nearest_beam_id=ent.nearest_beam_id,
        )

    def _trace_one(self, ent: RawTextEntity) -> MtextCleaningRecord:
        strip_mtext = get_strip_mtext()
        mtext_code = get_mtext_code_pattern()
        raw = ent.raw_text
        cleaned = strip_mtext(raw)
        raw_len = len(raw) or 1
        removed = len(raw) - len(cleaned)
        loss_pct = round(100.0 * removed / raw_len, 2)

        fmt_removed = bool(mtext_code.search(raw))
        eng_in_raw = bool(self._ENGINEERING_HINTS.search(raw))
        eng_in_clean = bool(self._ENGINEERING_HINTS.search(cleaned)) if cleaned else False
        eng_removed = eng_in_raw and not eng_in_clean
        entire_removed = bool(raw.strip()) and not cleaned

        status = "OK"
        if entire_removed and eng_in_raw:
            status = "ENGINEERING_TEXT_LOST"
        elif entire_removed:
            status = "ENTIRE_ANNOTATION_REMOVED"
        elif eng_removed:
            status = "ENGINEERING_TEXT_LOST"
        elif fmt_removed and removed > 0:
            status = "FORMATTING_REMOVED"

        return MtextCleaningRecord(
            entity_id=ent.entity_id,
            entity_type=ent.entity_type,
            raw_text=raw,
            cleaned_text=cleaned,
            characters_removed=removed,
            loss_pct=loss_pct,
            status=status,
            formatting_removed=fmt_removed,
            engineering_text_removed=eng_removed,
            entire_annotation_removed=entire_removed,
            nearest_beam_id=ent.nearest_beam_id,
        )

    def build_clean_map(
        self, entities: List[RawTextEntity]
    ) -> Dict[str, MtextCleaningRecord]:
        return {e.entity_id: self.trace_entity(e) for e in entities}
