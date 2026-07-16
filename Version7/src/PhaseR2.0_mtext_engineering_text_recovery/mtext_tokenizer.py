"""STEP 2 — Tokenize MTEXT into formatting and engineering tokens."""
from __future__ import annotations

import re
from typing import List, Tuple

from .mtext_models import EngineeringToken, FormattingToken, MtextEntity, MtextTokenization

# Formatting patterns with labels
_FMT_PATTERNS: List[Tuple[str, str]] = [
    (r"\\[A-Za-z][^;{}]*;", "FORMAT_SEMI"),   # \A1; \H3x; \fArial|b0;
    (r"\\[LlOoKk]", "FORMAT_TOGGLE"),          # \L \l \O \o \K \k
    (r"\\P", "FORMAT_PARA"),                    # paragraph break
    (r"\\\\", "FORMAT_ESC_BS"),                 # escaped backslash
    (r"\{|\}", "FORMAT_BRACE"),                 # brace delimiters
    (r"%%[A-Za-z]", "FORMAT_PCT"),              # %%d %%p etc.
]

# Engineering patterns with labels
_ENG_PATTERNS: List[Tuple[str, str]] = [
    (r"\d+\s*[-–]?\s*[YyRrTt]\s*\d+\s*@\s*\d+(?:/\d+)*", "STIRRUP_NOTATION"),
    (r"\d+\s*L[-\s]*[YyRrTt]\s*\d+", "MULTI_LEG"),
    (r"\d+\s*[-–]?\s*[YyRrTt]\s*\d+", "BAR_NOTATION"),
    (r"[YyRrTt]\s*\d+\s*@\s*\d+(?:/\d+)*", "STIRRUP_NO_QTY"),
    (r"[YyRrTt]\s*\d+", "GRADE_DIA"),
    (r"\d+(?:/\d+){2,}", "ZONE_SPACING"),
    (r"S\.?F\.?R\.?", "SFR_ABBREV"),
    (r"O\.?E\.?F\.?", "OEF_ABBREV"),
    (r"\bLd\b", "DEV_LENGTH"),
    (r"\bLap\b", "LAP_SPLICE"),
    (r"\bHook\b", "HOOK"),
    (r"TYP\.?", "TYPICAL"),
    (r"T\s*&\s*B", "TOP_AND_BOT"),
    (r"\bBOT\b", "BOTTOM"),
    (r"\bTOP\b", "TOP"),
    (r"\([^)]+\)", "PAREN_MODIFIER"),
]

_FMT_COMPILED = [(re.compile(p, re.I), label) for p, label in _FMT_PATTERNS]
_ENG_COMPILED = [(re.compile(p, re.I), label) for p, label in _ENG_PATTERNS]


class MtextTokenizer:

    def tokenize(self, entity: MtextEntity) -> MtextTokenization:
        raw = entity.raw_text
        fmt_tokens = []
        eng_tokens = []

        for rx, label in _FMT_COMPILED:
            for m in rx.finditer(raw):
                fmt_tokens.append(FormattingToken(
                    token_type=label,
                    raw_token=m.group(0),
                    position=m.start(),
                ))

        for rx, label in _ENG_COMPILED:
            for m in rx.finditer(raw):
                eng_tokens.append(EngineeringToken(
                    token_type=label,
                    value=m.group(0),
                    position=m.start(),
                ))

        fmt_tokens.sort(key=lambda t: t.position)
        eng_tokens.sort(key=lambda t: t.position)

        return MtextTokenization(
            entity_id=entity.entity_id,
            raw_text=raw,
            formatting_tokens=fmt_tokens,
            engineering_tokens=eng_tokens,
        )

    def tokenize_all(self, entities: List[MtextEntity]) -> List[MtextTokenization]:
        return [self.tokenize(e) for e in entities]
