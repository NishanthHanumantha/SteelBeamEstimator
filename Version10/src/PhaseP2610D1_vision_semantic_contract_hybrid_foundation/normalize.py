"""Spec/count/diameter parsing. Normalize representation; do not repair Vision values."""
from __future__ import annotations

import re
from typing import Any, Optional, Tuple

from .config import SUPPORTED_DIAMETERS

_SPACE_HYPHEN = re.compile(r"[\s\-]")
_DXF_AT_X = re.compile(r"@\\*X", re.I)
_DIA_RE = re.compile(r"Y\s*(\d+)", re.I)
_COUNT_RE = re.compile(r"^(\d+)\s*[LY]", re.I)
_LEGS_RE = re.compile(r"(\d+)\s*L", re.I)


def normalize_spec(spec: Any) -> str:
    s = str(spec or "").upper().strip()
    s = s.replace("–", "-").replace("—", "-")
    s = _DXF_AT_X.sub("@", s)
    s = s.replace("\\", "")
    s = _SPACE_HYPHEN.sub("", s)
    return s


def map_layer(raw: Any) -> str:
    layer = str(raw or "UNKNOWN").upper().strip()
    if layer in ("SIDE", "SIDE_FACE"):
        return "SIDE_FACE"
    if layer in ("SUPPORT_TOP_ZONE", "SUPPORT_BOTTOM_ZONE"):
        return "OTHER"
    if layer == "SPACER":
        return "SPACER"
    if layer in ("TOP", "BOTTOM", "STIRRUP", "OTHER", "UNKNOWN"):
        return layer
    return "UNKNOWN"


def parse_diameter(spec: Any, explicit: Any = None) -> Optional[int]:
    if explicit not in (None, "", "UNKNOWN"):
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    s = str(spec or "").upper()
    m = _DIA_RE.search(s)
    if not m:
        return None
    return int(m.group(1))


def parse_bar_count(spec: Any, explicit: Any = None) -> Optional[int]:
    if explicit not in (None, "", "UNKNOWN"):
        try:
            n = int(explicit)
            return n if n > 0 else None
        except (TypeError, ValueError):
            pass
    s = str(spec or "").upper().strip()
    if _LEGS_RE.search(s) and "@" in s:
        return None
    compact = s.replace("-", "").replace(" ", "")
    m = _COUNT_RE.match(compact)
    if not m:
        m = re.match(r"^(\d+)", compact)
    if not m:
        return None
    n = int(m.group(1))
    return n if n > 0 else None


def parse_legs(spec: Any) -> Optional[int]:
    m = _LEGS_RE.search(str(spec or "").upper())
    return int(m.group(1)) if m else None


def diameter_supported(dia: Any) -> bool:
    try:
        return int(dia) in SUPPORTED_DIAMETERS
    except (TypeError, ValueError):
        return False


def physical_key(g: dict) -> Tuple[str, str, str]:
    layer = map_layer(g.get("layer") or g.get("physical_layer"))
    role = str(g.get("role") or g.get("role_hypothesis") or g.get("reinforcement_role") or "UNKNOWN").upper()
    spec = normalize_spec(g.get("spec") or g.get("specification"))
    return (layer, role, spec)


__all__ = [
    "diameter_supported",
    "map_layer",
    "normalize_spec",
    "parse_bar_count",
    "parse_diameter",
    "parse_legs",
    "physical_key",
]
