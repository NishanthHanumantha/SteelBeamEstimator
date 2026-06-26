"""Phase D.4 — stirrup annotation parsing."""

import re
from typing import Any, Dict

from src.parsing.annotation_parsers import ParseError
from src.parsing.spacing_parser import spacing_mode

_STIRRUP_PATTERN = re.compile(
    r"^(\d+)L-Y(\d+)@(\d+(?:/\d+)*)C/C$",
    re.IGNORECASE,
)


def parse_stirrup_text(clean_text: str) -> Dict[str, Any]:
    text = clean_text.strip()
    match = _STIRRUP_PATTERN.match(text)
    if not match:
        raise ParseError(f"STIRRUP pattern mismatch: {text}")
    leg_count = int(match.group(1))
    diameter_mm = int(match.group(2))
    spacing_mm = [int(s) for s in match.group(3).split("/")]
    if leg_count <= 0 or diameter_mm <= 0:
        raise ParseError(f"STIRRUP invalid leg/dia: {leg_count}/{diameter_mm}")
    if any(s <= 0 for s in spacing_mm):
        raise ParseError(f"STIRRUP invalid spacing: {spacing_mm}")
    return {
        "engineering_type": "STIRRUP",
        "leg_count": leg_count,
        "diameter_mm": diameter_mm,
        "spacing_mm": spacing_mm,
        "spacing_mode": spacing_mode(spacing_mm),
    }
