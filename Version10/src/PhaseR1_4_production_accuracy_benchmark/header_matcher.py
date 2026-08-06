"""
Semantic header matching — fuzzy, layout-agnostic.
MODEL_VERSION: 8.6.0

Never depends on worksheet names, colours, fonts, or merged-cell layout.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Optional, Sequence, Tuple

MODEL_VERSION = "8.6.0"


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = text.lower().strip()
    text = text.replace("ø", "dia").replace("Ø", "dia")
    text = re.sub(r"[_\-/\\|]+", " ", text)
    text = re.sub(r"[^\w\s.&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_set(text: str) -> set:
    return {t for t in normalize_text(text).split() if t}


def fuzzy_score(candidate: object, patterns: Sequence[str]) -> float:
    """
    Score candidate against semantic patterns in [0, 1].
    Uses exact / substring / token-overlap heuristics (no ML).
    """
    cand = normalize_text(candidate)
    if not cand:
        return 0.0
    best = 0.0
    for raw in patterns:
        pat = normalize_text(raw)
        if not pat:
            continue
        if cand == pat:
            best = max(best, 1.0)
            continue
        if pat in cand or cand in pat:
            best = max(best, 0.92)
            continue
        ct, pt = token_set(cand), token_set(pat)
        if not ct or not pt:
            continue
        overlap = len(ct & pt) / max(len(pt), 1)
        if overlap >= 0.6:
            best = max(best, 0.55 + 0.4 * overlap)
        # compact form without spaces (8mm vs 8 mm)
        c_compact = cand.replace(" ", "")
        p_compact = pat.replace(" ", "")
        if c_compact == p_compact or p_compact in c_compact:
            best = max(best, 0.9)
    return round(best, 4)


def best_match(candidate: object, patterns: Sequence[str], threshold: float = 0.7) -> Optional[Tuple[str, float]]:
    score = fuzzy_score(candidate, patterns)
    if score < threshold:
        return None
    # return first pattern that contributed strongly
    cand = normalize_text(candidate)
    for pat in patterns:
        if fuzzy_score(cand, [pat]) >= threshold:
            return pat, score
    return patterns[0], score


def parse_diameter_mm(value: object) -> Optional[int]:
    """Extract bar diameter from headers like '8 mm', '8mm', 'Ø8', '8'."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        d = int(round(float(value)))
        return d if d in (8, 10, 12, 16, 20, 25, 32) else None
    text = normalize_text(value)
    if not text:
        return None
    m = re.search(r"(?:dia|d)?\s*(\d{1,2})\s*(?:mm)?\b", text)
    if not m:
        m = re.search(r"^(\d{1,2})$", text)
    if not m:
        return None
    d = int(m.group(1))
    return d if d in (8, 10, 12, 16, 20, 25, 32) else None


def is_beam_mark(value: object) -> bool:
    text = normalize_text(value).upper().replace(" ", "")
    return bool(re.match(r"^B\d+[A-Z]?$", text, re.I))


def beam_mark(value: object) -> Optional[str]:
    if not is_beam_mark(value):
        return None
    return normalize_text(value).upper().replace(" ", "")


# Semantic header pattern libraries (synonyms, not workbook-specific wording)
ABSTRACT_PATTERNS = ("abstract",)
REINF_MT_KG_PATTERNS = (
    "reinforcement in mt kg",
    "reinforcement in mt&kg",
    "reinforcement mt kg",
    "reinforcement-in mt&kg",
)
QUANTITY_BREAKUP_PATTERNS = (
    "concrete shuttering and reinforcement quantity breakup",
    "reinforcement quantity breakup",
    "quantity breakup",
    "concrete shuttering reinforcement",
)
SUMMARY_HEADER_PATTERNS = {
    "concrete": ("concrete",),
    "shuttering": ("shuttering", "shuttering m2", "shuttering (m2)"),
    "total_mt": ("total mt", "total-mt", "totalmt"),
    "kg": ("kg", "kilogram", "total kg"),
}
# Prefer exact / near-exact for short headers so "Grade of concrete" does not steal "Concrete"
SUMMARY_HEADER_EXACT = {
    "concrete": ("concrete",),
    "shuttering": ("shuttering",),
    "kg": ("kg",),
}
DETAIL_HEADER_PATTERNS = {
    "description": ("description", "desc"),
    "no_dia": ("no dia", "no./dia", "nodia", "dia", "no dia."),
    "spacing": ("l spcng", "l/spcng", "spcng", "spacing", "l spcng m"),
    "breadth_no": ("b m no", "b(m)/no", "b m / no", "no of bars", "b(m) no"),
    "development": ("d dvlp", "d/dvlp", "dvlp", "development", "d dvlp l"),
    "depth": ("d m", "d (m)"),
    "quantity": ("quantity", "concrete m3", "concrete (m3)"),
    "shuttering": ("shuttering", "shuttering m2"),
    "cutting_length": ("cutting length", "cut length"),
    "total_length": ("total length",),
    "steel": ("steel", "steel kg"),
}
