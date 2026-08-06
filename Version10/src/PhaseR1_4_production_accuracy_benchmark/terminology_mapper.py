"""
Official terminology → internal engineering role mapping.
MODEL_VERSION: 8.6.0

Synonym-driven; never hardcodes a single workbook's spelling.
"""
from __future__ import annotations

import re
from typing import List, Tuple

MODEL_VERSION = "8.6.0"

# Ordered: more specific patterns first
_ROLE_RULES: List[Tuple[str, str]] = [
    ("TOP_EXTRA", r"top\s*bars?\s*-?\s*extra"),
    ("BOTTOM_EXTRA", r"bottom\s*bars?\s*-?\s*extra"),
    ("TOP_MAIN", r"^top\s*bars?\s*$"),
    ("BOTTOM_MAIN", r"^bottom\s*bars?\s*$"),
    ("STIRRUP_HOOK", r"c\s*-?\s*hook|hook"),
    ("STIRRUP", r"stirrup|stirupp|stirupps|stirrups"),
    ("SPACER_BAR", r"spacer\s*bars?|spacer"),
    ("SIDE_FACE_REINFORCEMENT", r"\bsfr\b|side\s*face"),
]


def map_official_description(description: str) -> str:
    text = (description or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return "UNKNOWN"
    for role, pattern in _ROLE_RULES:
        if re.search(pattern, text, re.I):
            return role
    return "UNKNOWN"


def register_synonym(role: str, pattern: str) -> None:
    """Allow future synonym extension without changing call sites."""
    _ROLE_RULES.insert(0, (role, pattern))
