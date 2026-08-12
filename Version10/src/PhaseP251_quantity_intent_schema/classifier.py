"""Classify semantic_type and reinforcement_role for QuantityIntent."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import (
    ROLE_BOTTOM_BAR,
    ROLE_SIDE_FACE,
    ROLE_STIRRUP,
    ROLE_TOP_BAR,
    ROLE_UNKNOWN,
    SEM_LONGITUDINAL_BAR,
    SEM_SIDE_FACE,
    SEM_STIRRUP,
    SEM_UNKNOWN,
)
from .parser import ParseResult


def classify_semantic_type(
    parse: ParseResult,
    *,
    chain_semantic_type: Optional[str] = None,
) -> str:
    if parse.semantic_hint == SEM_STIRRUP:
        return SEM_STIRRUP
    if parse.semantic_hint == SEM_LONGITUDINAL_BAR:
        return SEM_LONGITUDINAL_BAR
    if chain_semantic_type == "StirrupNote":
        return SEM_STIRRUP
    if chain_semantic_type == "BarCallout":
        return SEM_LONGITUDINAL_BAR
    return SEM_UNKNOWN


def classify_role(
    *,
    semantic_type: str,
    role_hint: Optional[str] = None,
    chain: Optional[Dict[str, Any]] = None,
) -> str:
    """Consume existing role when available; never guess."""
    if semantic_type == SEM_STIRRUP:
        return ROLE_STIRRUP
    hint = str(role_hint or "").upper()
    if hint in (ROLE_TOP_BAR, ROLE_BOTTOM_BAR, ROLE_SIDE_FACE, ROLE_STIRRUP):
        return hint
    if semantic_type == SEM_SIDE_FACE:
        return ROLE_SIDE_FACE
    _ = chain
    return ROLE_UNKNOWN


def confidence_for(
    *,
    parse: ParseResult,
    semantic_type: str,
    role: str,
    links_ok: bool,
) -> float:
    c = 0.4
    if parse.quantity_status in ("EXPLICIT", "SPACING_BASED", "COMPOSITE"):
        c += 0.35
    if semantic_type != SEM_UNKNOWN:
        c += 0.1
    if role != ROLE_UNKNOWN:
        c += 0.1
    if links_ok:
        c += 0.05
    if parse.ambiguous:
        c = min(c, 0.35)
    return round(min(c, 0.99), 3)
