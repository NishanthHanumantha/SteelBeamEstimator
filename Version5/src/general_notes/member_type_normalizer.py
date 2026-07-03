"""Normalize member type labels from General Notes cover tables."""

import re
from typing import Optional

_MEMBER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("BEAM", re.compile(r"BEAM", re.IGNORECASE)),
    ("SLAB", re.compile(r"SLAB", re.IGNORECASE)),
    ("COLUMN", re.compile(r"COLUMN", re.IGNORECASE)),
    ("FOOTING", re.compile(r"FOOTING", re.IGNORECASE)),
    ("LINTEL", re.compile(r"LINTEL", re.IGNORECASE)),
    ("PLINTH_BEAM", re.compile(r"PLINTH\s*BEAM", re.IGNORECASE)),
    ("RETAINING_WALL", re.compile(r"RETAINING\s*WALL", re.IGNORECASE)),
    ("OHT", re.compile(r"OVERHEAD\s*WATER\s*TANK|OVERHEAD\s*WATER\s*TANK", re.IGNORECASE)),
    ("UGT", re.compile(r"UNDER\s*GROUND\s*WATER\s*TANK|UNDERGROUND\s*WATER\s*TANK", re.IGNORECASE)),
    ("STAIRCASE", re.compile(r"STAIR", re.IGNORECASE)),
    ("WALL", re.compile(r"\bWALL\b", re.IGNORECASE)),
    ("PEDESTAL", re.compile(r"PEDESTAL", re.IGNORECASE)),
]


def normalize_member_type(original: str) -> str:
    """Map drawing member labels to canonical engineering member types."""
    cleaned = original.strip()
    if not cleaned:
        return "UNKNOWN"

    for normalized, pattern in _MEMBER_PATTERNS:
        if pattern.search(cleaned):
            if normalized == "WALL" and "RETAINING" in cleaned.upper():
                return "RETAINING_WALL"
            if normalized == "BEAM" and "PLINTH" in cleaned.upper():
                return "PLINTH_BEAM"
            if normalized == "SLAB" and "BOTTOM" in cleaned.upper():
                return "SLAB"
            return normalized

    return cleaned.upper().replace(" ", "_")


def member_lookup_aliases(normalized: str) -> list[str]:
    """Return lookup aliases for cover cache matching."""
    aliases = [normalized]
    alias_map = {
        "BEAM": ["BEAM", "BEAM IN SUPERSTRUCTURE"],
        "SLAB": ["SLAB", "SLAB IN SUPERSTRUCTURE", "TOP SLAB", "BOTTOM SLAB"],
        "COLUMN": ["COLUMN", "COLUMNS"],
        "FOOTING": ["FOOTING"],
        "LINTEL": ["LINTEL", "LINTELS"],
        "PLINTH_BEAM": ["PLINTH BEAM", "PLINTH_BEAM"],
        "RETAINING_WALL": ["RETAINING WALL", "RETAINING_WALLS"],
        "OHT": ["OVERHEAD WATER TANK", "OHT"],
        "UGT": ["UNDER GROUND WATER TANK", "UGT"],
        "STAIRCASE": ["STAIR CASE", "STAIRCASE"],
        "WALL": ["WALL", "WALLS"],
        "PEDESTAL": ["COLUMN PEDESTAL", "PEDESTAL"],
    }
    return alias_map.get(normalized, aliases)
