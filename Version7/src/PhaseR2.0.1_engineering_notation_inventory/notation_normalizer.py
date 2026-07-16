"""STEP 2 — Normalize whitespace / abbreviation punctuation only. No meaning inference."""
from __future__ import annotations

import re
from typing import List

from .notation_models import ExtractedNotation, NormalizedNotation

# Abbreviation canonical forms (punctuation/spacing only — no semantic rewrite)
_ABBREV_RULES = [
    (re.compile(r"^S\s*\.?\s*F\s*\.?\s*R\s*\.?$", re.I), "S.F.R."),
    (re.compile(r"^O\s*\.?\s*E\s*\.?\s*F\s*\.?$", re.I), "O.E.F."),
    (re.compile(r"^T\s*\.?\s*O\s*\.?\s*F\s*\.?$", re.I), "T.O.F."),
    (re.compile(r"^B\s*\.?\s*O\s*\.?\s*F\s*\.?$", re.I), "B.O.F."),
    (re.compile(r"^N\s*\.?\s*F\s*\.?$", re.I), "N.F."),
    (re.compile(r"^F\s*\.?\s*F\s*\.?$", re.I), "F.F."),
    (re.compile(r"^CONT\.?$", re.I), "CONT"),
    (re.compile(r"^TYP\.?$", re.I), "TYP."),
    (re.compile(r"^U[-\s]?BAR$", re.I), "U-BAR"),
    (re.compile(r"^T\s*&\s*B$", re.I), "T&B"),
    (re.compile(r"^BOTH\s+FACES?$", re.I), "BOTH FACE"),
    (re.compile(r"^ON\s+BOTH\s+FACES?$", re.I), "ON BOTH FACE"),
    (re.compile(r"^NEAR\s+FACE$", re.I), "NEAR FACE"),
    (re.compile(r"^FAR\s+FACE$", re.I), "FAR FACE"),
    (re.compile(r"^EACH\s+FACE$", re.I), "EACH FACE"),
    (re.compile(r"^BOTTOM$", re.I), "BOT"),
    (re.compile(r"^LD$", re.I), "Ld"),
    (re.compile(r"^LAP$", re.I), "Lap"),
]


def _normalize_token(token: str) -> str:
    t = re.sub(r"\s+", " ", token.strip())
    for rx, canon in _ABBREV_RULES:
        if rx.match(t):
            return canon
    # Normalize bar callouts: collapse spaces around - and @
    t = re.sub(r"\s*-\s*", "-", t)
    t = re.sub(r"\s*@\s*", "@", t)
    t = re.sub(r"\s*\+\s*", "+", t)
    t = re.sub(r"\s*/\s*", "/", t)
    # Canonical grade letter uppercase for Y/R/T patterns
    t = re.sub(r"([YyRrTt])(\d+)", lambda m: m.group(1).upper() + m.group(2), t)
    return t


class NotationNormalizer:

    def normalize_all(
        self, extracted: List[ExtractedNotation]
    ) -> List[NormalizedNotation]:
        return [
            NormalizedNotation(
                raw_token=e.raw_token,
                normalized=_normalize_token(e.raw_token),
                entity_id=e.entity_id,
                beam_id=e.beam_id,
                drawing_id=e.drawing_id,
                source_text=e.source_text,
                entity_type=e.entity_type,
                x=e.x,
                y=e.y,
            )
            for e in extracted
        ]
