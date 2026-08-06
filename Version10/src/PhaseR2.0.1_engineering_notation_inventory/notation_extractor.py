"""STEP 1 — Extract engineering notation tokens from recovered text."""
from __future__ import annotations

import re
from typing import List

from .notation_models import ExtractedNotation, RawTextEntity

# Ordered longest-first to prefer full patterns over fragments
_EXTRACT_PATTERNS = [
    # Composite / stirrup / bar callouts
    r"\d+\s*L[-\s]*[YyRrTt]\s*\d+\s*@\s*\d+(?:/\d+)*",
    r"\d+\s*[-\u2013]?\s*[YyRrTt]\s*\d+\s*\+\s*\d+\s*[YyRrTt]\s*\d+",
    r"\d+\s*[-\u2013]?\s*[YyRrTt]\s*\d+\s*@\s*\d+(?:/\d+)*",
    r"[YyRrTt]\s*\d+\s*@\s*\d+(?:/\d+)*(?:\s*C/?C)?",
    r"\d+\s*L[-\s]*[YyRrTt]\s*\d+",
    r"\d+\s*[-\u2013]?\s*[YyRrTt]\s*\d+",
    r"[YyRrTt]\s*\d+",
    # Multi-zone spacing
    r"\d+(?:/\d+){2,}",
    # Dot abbreviations
    r"S\.?\s*F\.?\s*R\.?",
    r"O\.?\s*E\.?\s*F\.?",
    r"T\.?\s*O\.?\s*F\.?",
    r"B\.?\s*O\.?\s*F\.?",
    r"N\.?\s*F\.?",
    r"F\.?\s*F\.?",
    # Face phrases
    r"BOTH\s+FACE[S]?",
    r"NEAR\s+FACE",
    r"FAR\s+FACE",
    r"EACH\s+FACE",
    r"ON\s+BOTH\s+FACE[S]?",
    # Development / detailing
    r"\bLd\s*\+?\s*\d*\s*d?b?\b",
    r"\bLd\b",
    r"\bLap\b",
    r"\bCrank\b",
    r"\bHook\b",
    r"\bBend\b",
    r"\bAnchor\b",
    r"\bDev(?:elopment)?\b",
    r"\bSpacer\b",
    r"\bU[-\s]?BAR\b",
    r"\bCONT\.?\b",
    r"\bTYP\.?\b",
    r"\bTOP\b",
    r"\bBOT(?:TOM)?\b",
    r"\bMID\b",
    r"\bFACE\b",
    r"T\s*&\s*B",
    r"\([^)]+\)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _EXTRACT_PATTERNS]


class NotationExtractor:

    def extract_all(self, entities: List[RawTextEntity]) -> List[ExtractedNotation]:
        results: List[ExtractedNotation] = []
        for ent in entities:
            # Prefer recovered text (R.2.0); fall back to raw if recovered empty
            text = ent.recovered_text or ent.raw_text or ""
            if not text.strip():
                continue
            seen_spans = set()
            for rx in _COMPILED:
                for m in rx.finditer(text):
                    span = (m.start(), m.end())
                    # Skip nested/overlapping shorter matches already covered
                    if any(s[0] <= span[0] and span[1] <= s[1] and s != span for s in seen_spans):
                        continue
                    # Remove spans fully contained by this new longer match
                    seen_spans = {
                        s for s in seen_spans
                        if not (span[0] <= s[0] and s[1] <= span[1] and s != span)
                    }
                    seen_spans.add(span)
                    token = m.group(0).strip()
                    if not token or len(token) < 2:
                        continue
                    results.append(ExtractedNotation(
                        entity_id=ent.entity_id,
                        raw_token=token,
                        source_text=text[:200],
                        entity_type=ent.entity_type,
                        beam_id=ent.nearest_beam_id,
                        drawing_id=ent.drawing_id,
                        x=ent.x,
                        y=ent.y,
                    ))
        return results
