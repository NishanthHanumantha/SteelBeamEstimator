"""Classify QuantityIntent records into Vision candidate reason codes."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .config import (
    REASON_AMBIGUOUS_QUANTITY,
    REASON_DEFER_ENGINEERING_RULE,
    REASON_NON_QUANTITY_NOTE,
    REASON_OCR_CORRUPTION,
    REASON_SEMANTIC_CONTEXT_REQUIRED,
    REASON_STIRRUP_PATTERN_UNPARSED,
    REASON_UNRESOLVED_QUANTITY,
    REASON_VISION_NOT_REQUIRED,
)

# OCR corruption markers observed in Fourth Set (preserve exact raw text)
_OCR_RE = re.compile(r"\\X|\\\\X|\uFFFD|�", re.IGNORECASE)

# Development-length / engineering notes (not quantity callouts)
_DEV_NOTE_RE = re.compile(
    r"^(Ld|LD)(\+.*)?$|bd|db|development",
    re.IGNORECASE,
)

# Side-face descriptive notes
_SFR_RE = re.compile(
    r"S\.?F\.?R\.?|SIDE\.?\s*FACE|EACH\s*FACE|SIDEFACE",
    re.IGNORECASE,
)

# Stirrup-like with @ but unparsed
_STIRRUPISH_RE = re.compile(r"\d*\s*L?-?\s*Y\s*\d+.*@", re.IGNORECASE)


def is_ocr_corrupted(raw_text: str) -> bool:
    return bool(_OCR_RE.search(raw_text or ""))


def is_development_note(raw_text: str) -> bool:
    t = (raw_text or "").strip()
    if not t:
        return False
    # Exact short Ld forms
    if re.fullmatch(r"Ld(\+[\w\d+]+)?", t, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"Ld\+10bd\+10db", t, flags=re.IGNORECASE):
        return True
    return bool(re.fullmatch(r"Ld\+.*", t, flags=re.IGNORECASE))


def is_sfr_descriptive_note(raw_text: str) -> bool:
    t = (raw_text or "").strip()
    if not t:
        return False
    return bool(_SFR_RE.search(t)) and not _STIRRUPISH_RE.search(t)


def ocr_normalization_hint(raw_text: str) -> Optional[str]:
    """HINT only — never rewrite source text."""
    if not is_ocr_corrupted(raw_text):
        return None
    if _STIRRUPISH_RE.search(raw_text or ""):
        return "possible_spacing_token_corruption"
    return "possible_ocr_token_corruption"


def classify_intent_reasons(intent: dict) -> Tuple[List[str], str]:
    """
    Return (reason_codes, human_explanation).
    Does not decide candidate vs deferred — selector does that.
    """
    raw = intent.get("raw_text") or ""
    status = intent.get("quantity_status") or ""
    reasons: List[str] = []

    if status in ("EXPLICIT", "SPACING_BASED", "COMPOSITE"):
        reasons.append(REASON_VISION_NOT_REQUIRED)
        return reasons, "Deterministic QuantityIntent already resolved"

    if is_development_note(raw):
        reasons.append(REASON_DEFER_ENGINEERING_RULE)
        reasons.append(REASON_NON_QUANTITY_NOTE)
        return reasons, "Development-length / engineering note — not a Vision quantity case"

    if is_sfr_descriptive_note(raw):
        reasons.append(REASON_SEMANTIC_CONTEXT_REQUIRED)
        reasons.append(REASON_NON_QUANTITY_NOTE)
        return reasons, "Descriptive side-face reinforcement note"

    if is_ocr_corrupted(raw):
        reasons.append(REASON_OCR_CORRUPTION)
        if _STIRRUPISH_RE.search(raw):
            reasons.append(REASON_STIRRUP_PATTERN_UNPARSED)
        reasons.append(REASON_UNRESOLVED_QUANTITY)
        return reasons, "OCR-corrupted reinforcement notation remains unresolved"

    if status == "UNRESOLVED" or intent.get("provenance", {}).get("ambiguous"):
        if intent.get("provenance", {}).get("ambiguous") or "AMBIGUOUS" in str(
            intent.get("provenance", {}).get("parse_note") or ""
        ):
            reasons.append(REASON_AMBIGUOUS_QUANTITY)
        reasons.append(REASON_UNRESOLVED_QUANTITY)
        if _STIRRUPISH_RE.search(raw):
            reasons.append(REASON_STIRRUP_PATTERN_UNPARSED)
        return reasons, "Unresolved quantity expression"

    reasons.append(REASON_VISION_NOT_REQUIRED)
    return reasons, "No Vision selection trigger"
