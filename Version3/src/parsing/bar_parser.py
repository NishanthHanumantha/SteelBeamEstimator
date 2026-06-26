"""Phase D.4 — longitudinal bar text parsing."""

import re
from typing import Any, Dict

from src.parsing.annotation_parsers import ParseError

_BAR_PATTERN = re.compile(r"^(\d+)-Y(\d+)$", re.IGNORECASE)


def parse_bar_text(clean_text: str) -> Dict[str, Any]:
    text = clean_text.strip()
    match = _BAR_PATTERN.match(text)
    if not match:
        raise ParseError(f"BAR pattern mismatch: {text}")
    quantity = int(match.group(1))
    diameter_mm = int(match.group(2))
    if quantity <= 0 or diameter_mm <= 0:
        raise ParseError(f"BAR invalid values: qty={quantity}, dia={diameter_mm}")
    return {
        "engineering_type": "LONGITUDINAL_BAR",
        "quantity": quantity,
        "diameter_mm": diameter_mm,
        "position": "UNKNOWN",
        "continuity": "UNKNOWN",
    }
