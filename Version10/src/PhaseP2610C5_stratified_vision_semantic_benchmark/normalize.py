"""Safe spec/layer normalization for C.5 comparison. No role collapse."""
from __future__ import annotations

import re
from typing import Any, Optional, Tuple

_SPACE_HYPHEN = re.compile(r"[\s\-]")
_DXF_AT_X = re.compile(r"@\\*X", re.I)
_COUNT_RE = re.compile(r"^(\d+)\s*[LY]", re.I)


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
    if layer in ("SUPPORT_TOP_ZONE", "SUPPORT_BOTTOM_ZONE", "SPACER"):
        return "OTHER"
    if layer in ("TOP", "BOTTOM", "STIRRUP", "OTHER", "UNKNOWN"):
        return layer
    return "UNKNOWN"


def parse_bar_count(spec: Any, explicit: Any = None) -> Optional[int]:
    if explicit not in (None, "", "UNKNOWN"):
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    s = str(spec or "").upper().strip()
    if "L-" in s or s.startswith("4L") or re.match(r"\d+L", s):
        return None
    m = _COUNT_RE.match(s.replace("-", ""))
    if not m:
        m = re.match(r"^(\d+)", s)
    if not m:
        return None
    return int(m.group(1))


def physical_key(g: dict) -> Tuple[str, str]:
    layer = map_layer(g.get("layer") or g.get("physical_layer"))
    spec = normalize_spec(g.get("spec") or g.get("specification"))
    return (layer, spec)


__all__ = ["map_layer", "normalize_spec", "parse_bar_count", "physical_key"]
