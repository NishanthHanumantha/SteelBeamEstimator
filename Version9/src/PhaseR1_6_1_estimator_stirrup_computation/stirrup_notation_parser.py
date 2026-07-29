"""
Parse stirrup labels: 2L-Y8@100/200/100C/C
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

import re
from typing import Optional

from spacing_pattern_parser import SpacingPatternParser
from stirrup_model import StirrupNotation

MODEL_VERSION = "8.8.1"

# 2L-Y8@100/200/100 or 2L-Y8@100C/C or Y8@150 etc.
_NOTATION_RE = re.compile(
    r"(?:(?P<legs>\d+)\s*[Ll]-?)?"
    r"(?:[Yy]|Ø|ø|DIA)?"
    r"(?P<dia>\d{1,2})"
    r"\s*[@\u0040]\s*"
    r"(?P<spacing>[\d./\s]+)"
    r"(?:\s*[Cc]\s*/\s*[Cc])?",
    re.I,
)


class StirrupNotationParser:
    def __init__(self):
        self._spacing = SpacingPatternParser()

    def parse(self, label: str) -> Optional[StirrupNotation]:
        text = (label or "").strip()
        if not text:
            return None
        # strip trailing descriptive noise
        cleaned = re.sub(r"\s+", "", text)
        m = _NOTATION_RE.search(cleaned)
        if not m:
            # try with original spaces preserved in spacing part only
            m = _NOTATION_RE.search(text.replace(" ", ""))
        if not m:
            return None

        legs = int(m.group("legs") or 2)
        dia = float(m.group("dia"))
        spacing_raw = m.group("spacing")
        values = self._spacing.parse(spacing_raw)
        if not values:
            return None
        pattern = self._spacing.to_pattern(values)
        ntype = "UNIFORM" if len(values) == 1 else "VARIABLE"
        return StirrupNotation(
            raw_label=label.strip(),
            legs=legs,
            diameter_mm=dia,
            spacing_values_mm=tuple(values),
            spacing_pattern=pattern,
            notation_type=ntype,
        )
