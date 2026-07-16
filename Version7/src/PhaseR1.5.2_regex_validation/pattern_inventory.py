"""STEP 3 — Reinforcement pattern inventory from DXF text."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from .regex_validation_models import PatternRecord, RawTextEntity

# Known engineering notation tokens
_TOKEN_PATTERNS = [
    (r"\d+\s*L[-\s]*Y\s*\d+\s*@\s*\d+(?:/\d+)*", "NL-YD@S"),
    (r"\d+\s*L[-\s]*Y\s*\d+", "NL-YD"),
    (r"\d+\s*[-–]?\s*[YyRrTt]\s*\d+\s*@\s*\d+(?:/\d+)*", "N-YD@S"),
    (r"\d+\s*[-–]?\s*[YyRrTt]\s*\d+\s*\+\s*\d+\s*[YyRrTt]\s*\d+", "N-YD+MYD"),
    (r"\d+\s*[-–]?\s*[YyRrTt]\s*\d+", "N-YD"),
    (r"[YyRrTt]\s*\d+\s*@\s*\d+(?:/\d+)*", "YD@S"),
    (r"[YyRrTt]\s*\d+", "YD"),
    (r"\d+(?:/\d+)+", "SPACING_RATIO"),
    (r"S\.?\s*F\.?\s*R\.?", "S.F.R."),
    (r"O\.?\s*E\.?\s*F\.?", "O.E.F."),
    (r"\bLd\b", "Ld"),
    (r"\bLap\b", "Lap"),
    (r"Spacer|S\.P\.|SP\.", "Spacer"),
    (r"\bHook\b", "Hook"),
    (r"\bBend\b", "Bend"),
    (r"Curtailment", "Curtailment"),
    (r"Development", "Development"),
    (r"Anchor", "Anchor"),
    (r"TYP\.?", "TYP."),
    (r"T\s*&\s*B", "T&B"),
    (r"\bBOT\b", "BOT"),
    (r"\bTOP\b", "TOP"),
    (r"\([^)]+\)", "PAREN_MODIFIER"),
]

_COMPILED = [(re.compile(p, re.I), label) for p, label in _TOKEN_PATTERNS]


class PatternInventory:

    def build(
        self,
        entities: List[RawTextEntity],
        clean_map: Dict[str, str],
    ) -> List[PatternRecord]:
        counter: Counter = Counter()
        examples: Dict[str, List[str]] = defaultdict(list)

        for ent in entities:
            texts = [ent.raw_text]
            cleaned = clean_map.get(ent.entity_id, ent.raw_text)
            if cleaned and cleaned != ent.raw_text:
                texts.append(cleaned)

            for text in texts:
                if not text or len(text) < 2:
                    continue
                found_in_entity = set()
                for rx, label in _COMPILED:
                    if rx.search(text):
                        counter[label] += 1
                        found_in_entity.add(label)
                for label in found_in_entity:
                    if len(examples[label]) < 5:
                        examples[label].append(text[:120])

        records = []
        for pattern, freq in counter.most_common():
            records.append(PatternRecord(
                pattern=pattern,
                frequency=freq,
                examples=examples.get(pattern, []),
            ))
        return records

    def unique_count(self, records: List[PatternRecord]) -> int:
        return len(records)
