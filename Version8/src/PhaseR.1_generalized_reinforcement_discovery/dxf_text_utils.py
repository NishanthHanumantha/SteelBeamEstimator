"""Shared DXF TEXT/MTEXT parsing helpers for Phase R.1."""

from __future__ import annotations

import re
from typing import Optional, Tuple

_MTEXT_NOBRACE = re.compile(r"\\[A-Za-z][^;]*;|\\\\|\\P|\\p[^;]+;")
_ENG_SIGNAL = re.compile(r"[YyRrTt]\s*\d+|S\.?F\.?R|O\.?E\.?F|\bLd\b|@\s*\d", re.IGNORECASE)
_BRACE_INNER_FMT = re.compile(r"\\[A-Za-z][^;{}]*;|\\[LlOoKk]|\\\\")
_BRACE_BLOCK = re.compile(r"\{([^{}]*)\}")


def _recover_brace_inner(content: str) -> str:
    text = _BRACE_INNER_FMT.sub("", content).strip()
    return text if _ENG_SIGNAL.search(text) else ""


def strip_mtext(raw: str) -> str:
    if not raw:
        return ""
    cleaned = _BRACE_BLOCK.sub(lambda m: _recover_brace_inner(m.group(1)), raw)
    cleaned = _MTEXT_NOBRACE.sub("", cleaned)
    cleaned = re.sub(r"%%[A-Za-z]", "", cleaned)
    return cleaned.strip()


def entity_position(entity) -> Optional[Tuple[float, float]]:
    try:
        pt = entity.dxf.insert
        return (float(pt.x), float(pt.y))
    except Exception:
        return None


def entity_raw_text(entity) -> str:
    if entity.dxftype() == "TEXT":
        return entity.dxf.text or ""
    if entity.dxftype() == "MTEXT":
        try:
            return entity.plain_mtext()
        except Exception:
            return entity.text or ""
    return ""
