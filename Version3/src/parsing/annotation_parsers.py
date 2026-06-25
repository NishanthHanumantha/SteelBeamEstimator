"""Regex parsers for engineering annotation types (Phase D.2)."""

import re
from typing import Any, Dict, List, Optional, Tuple

_BAR_PATTERN = re.compile(r"^(\d+)-Y(\d+)$", re.IGNORECASE)
_STIRRUP_PATTERN = re.compile(
    r"^(\d+)L-Y(\d+)@(\d+(?:/\d+)*)C/C$",
    re.IGNORECASE,
)
_ANCHORAGE_LD = re.compile(r"^Ld$", re.IGNORECASE)
_ANCHORAGE_LD_PLUS = re.compile(r"^Ld\+(\d+)db$", re.IGNORECASE)
_SFR_BAR_TOKEN = re.compile(r"(\d+)-?Y(\d+)", re.IGNORECASE)


class ParseError(Exception):
    """Raised when clean_text does not match expected engineering pattern."""


def parse_bar(clean_text: str) -> Dict[str, Any]:
    text = clean_text.strip()
    match = _BAR_PATTERN.match(text)
    if not match:
        raise ParseError(f"BAR pattern mismatch: {text}")
    quantity = int(match.group(1))
    diameter_mm = int(match.group(2))
    if quantity <= 0 or diameter_mm <= 0:
        raise ParseError(f"BAR invalid values: qty={quantity}, dia={diameter_mm}")
    return {
        "annotation_type": "BAR",
        "quantity": quantity,
        "diameter_mm": diameter_mm,
    }


def parse_stirrup(clean_text: str) -> Dict[str, Any]:
    text = clean_text.strip()
    match = _STIRRUP_PATTERN.match(text)
    if not match:
        raise ParseError(f"STIRRUP pattern mismatch: {text}")
    leg_count = int(match.group(1))
    diameter_mm = int(match.group(2))
    spacing_raw = match.group(3)
    spacing_mm = [int(s) for s in spacing_raw.split("/")]
    if leg_count <= 0 or diameter_mm <= 0:
        raise ParseError(f"STIRRUP invalid leg/dia: {leg_count}/{diameter_mm}")
    if any(s <= 0 for s in spacing_mm):
        raise ParseError(f"STIRRUP invalid spacing: {spacing_mm}")
    return {
        "annotation_type": "STIRRUP",
        "leg_count": leg_count,
        "diameter_mm": diameter_mm,
        "spacing_mm": spacing_mm,
    }


def parse_anchorage(clean_text: str) -> Dict[str, Any]:
    text = clean_text.strip()
    if _ANCHORAGE_LD.match(text):
        return {
            "annotation_type": "ANCHORAGE",
            "anchorage_type": "LD",
            "extension_db": 0,
        }
    plus_match = _ANCHORAGE_LD_PLUS.match(text)
    if plus_match:
        extension_db = int(plus_match.group(1))
        if extension_db < 0:
            raise ParseError(f"ANCHORAGE negative extension: {extension_db}")
        return {
            "annotation_type": "ANCHORAGE",
            "anchorage_type": "LD_PLUS_DB",
            "extension_db": extension_db,
        }
    raise ParseError(f"ANCHORAGE pattern mismatch: {text}")


def parse_side_face_reinf(clean_text: str) -> Dict[str, Any]:
    text = clean_text.strip()
    tokens = _SFR_BAR_TOKEN.findall(text)
    if not tokens:
        raise ParseError(f"SFR no bar token: {text}")
    quantity, diameter_mm = int(tokens[0][0]), int(tokens[0][1])
    if quantity <= 0 or diameter_mm <= 0:
        raise ParseError(f"SFR invalid values: qty={quantity}, dia={diameter_mm}")
    return {
        "annotation_type": "SIDE_FACE_REINF",
        "quantity": quantity,
        "diameter_mm": diameter_mm,
    }


def parse_annotation(
    annotation_type: str, clean_text: str
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return (parsed_fields, error_message)."""
    try:
        if annotation_type == "BAR":
            return parse_bar(clean_text), None
        if annotation_type == "STIRRUP":
            return parse_stirrup(clean_text), None
        if annotation_type == "ANCHORAGE":
            return parse_anchorage(clean_text), None
        if annotation_type == "SIDE_FACE_REINF":
            return parse_side_face_reinf(clean_text), None
        return None, f"unsupported annotation_type: {annotation_type}"
    except ParseError as exc:
        return None, str(exc)
