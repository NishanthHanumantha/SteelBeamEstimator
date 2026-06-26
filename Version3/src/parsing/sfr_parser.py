"""Phase D.4 — side face reinforcement parsing."""

import re
from typing import Any, Dict, Optional

from src.parsing.annotation_parsers import ParseError

_SFR_BAR_TOKEN = re.compile(r"(\d+)-?Y(\d+)", re.IGNORECASE)
_SFR_SEMANTIC_ONLY = re.compile(
    r"S\.?\s*F\.?\s*R\.?",
    re.IGNORECASE,
)


def parse_sfr_text(clean_text: str) -> Dict[str, Any]:
    text = clean_text.strip()
    tokens = _SFR_BAR_TOKEN.findall(text)
    semantic = _semantic_class(text)

    if tokens:
        quantity, diameter_mm = int(tokens[0][0]), int(tokens[0][1])
        if quantity <= 0 or diameter_mm <= 0:
            raise ParseError(f"SFR invalid values: qty={quantity}, dia={diameter_mm}")
        return {
            "engineering_type": "SIDE_FACE_REINFORCEMENT",
            "quantity": quantity,
            "diameter_mm": diameter_mm,
            "semantic_class": semantic or "BAR_SPECIFIED",
        }

    if _SFR_SEMANTIC_ONLY.search(text):
        return {
            "engineering_type": "SIDE_FACE_REINFORCEMENT",
            "quantity": None,
            "diameter_mm": None,
            "semantic_class": semantic or "SEMANTIC_NOTE",
        }

    upper = text.upper()
    if "SIDE FACE" in upper or "SIDE.FACE" in upper:
        return {
            "engineering_type": "SIDE_FACE_REINFORCEMENT",
            "quantity": None,
            "diameter_mm": None,
            "semantic_class": semantic or "SIDE_FACE_NOTE",
        }

    raise ParseError(f"SFR pattern mismatch: {text}")


def _semantic_class(text: str) -> Optional[str]:
    upper = text.upper()
    if "ON BOTH FACE" in upper or "ON BOTH FACES" in upper:
        return "ON_BOTH_FACE"
    if "SIDE FACE" in upper or "FACE REINF" in upper:
        return "SIDE_FACE_NOTE"
    return None
