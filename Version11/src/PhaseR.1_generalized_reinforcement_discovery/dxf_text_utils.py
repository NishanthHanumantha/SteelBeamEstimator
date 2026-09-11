"""Shared DXF TEXT/MTEXT/DIMENSION parsing helpers for Phase R.1."""

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


def is_dimension_entity(entity) -> bool:
    """True for DIMENSION and specialized dimension subtypes."""
    try:
        return "DIMENSION" in entity.dxftype()
    except Exception:
        return False


def entity_position(entity) -> Optional[Tuple[float, float]]:
    # DIMENSION: prefer text_midpoint / defpoint. Many dim subtypes expose a
    # spurious insert at (0,0) which must not win over real geometry.
    if is_dimension_entity(entity):
        for attr in ("text_midpoint", "defpoint"):
            try:
                if entity.dxf.hasattr(attr):
                    p = getattr(entity.dxf, attr)
                    return (float(p[0]), float(p[1]))
            except Exception:
                continue
        return None
    try:
        pt = entity.dxf.insert
        return (float(pt.x), float(pt.y))
    except Exception:
        return None


def entity_raw_text(entity) -> str:
    dtype = entity.dxftype()
    if dtype == "TEXT":
        return entity.dxf.text or ""
    if dtype == "MTEXT":
        try:
            return entity.plain_mtext()
        except Exception:
            return entity.text or ""
    if is_dimension_entity(entity):
        # Text override only — "<>" means "use measured value" (not stirrup text)
        try:
            text = str(entity.dxf.text or "")
        except Exception:
            return ""
        stripped = text.strip()
        if not stripped or stripped == "<>":
            return ""
        return text
    return ""
