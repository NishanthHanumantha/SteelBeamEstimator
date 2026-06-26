"""Phase D.4 — anchorage and hook annotation parsing."""

import re
from typing import Any, Dict

from src.parsing.annotation_parsers import ParseError

_ANCHORAGE_LD = re.compile(r"^Ld$", re.IGNORECASE)
_ANCHORAGE_LD_PLUS = re.compile(r"^Ld\+(\d+)db$", re.IGNORECASE)
_HOOK_PATTERN = re.compile(r"^Hook$", re.IGNORECASE)
_BEND_PATTERN = re.compile(r"^Bend$", re.IGNORECASE)


def parse_anchorage_text(clean_text: str) -> Dict[str, Any]:
    text = clean_text.strip()
    if _ANCHORAGE_LD.match(text):
        return {
            "engineering_type": "ANCHORAGE",
            "anchorage_type": "LD",
            "extension_db": 0,
            "hook_type": None,
        }
    plus_match = _ANCHORAGE_LD_PLUS.match(text)
    if plus_match:
        extension_db = int(plus_match.group(1))
        if extension_db < 0:
            raise ParseError(f"ANCHORAGE negative extension: {extension_db}")
        return {
            "engineering_type": "ANCHORAGE",
            "anchorage_type": "LD_PLUS_DB",
            "extension_db": extension_db,
            "hook_type": None,
        }
    if _HOOK_PATTERN.match(text):
        return {
            "engineering_type": "HOOK",
            "anchorage_type": "HOOK",
            "extension_db": 0,
            "hook_type": "HOOK",
        }
    if _BEND_PATTERN.match(text):
        return {
            "engineering_type": "ANCHORAGE",
            "anchorage_type": "BEND",
            "extension_db": 0,
            "hook_type": "BEND",
        }
    raise ParseError(f"ANCHORAGE pattern mismatch: {text}")
