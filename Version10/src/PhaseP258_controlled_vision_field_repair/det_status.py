"""Classify deterministic field completeness from parser evidence, never from Vision."""
from __future__ import annotations

import re
from typing import Any, List, Optional

from .config import DET_CONFIRMED, DET_PARTIAL, DET_UNKNOWN


def _spacing_tokens(text: str) -> List[str]:
    if "@" not in (text or ""):
        return []
    return re.findall(r"\d+", (text or "").split("@", 1)[1])


def classify_deterministic_status(
    *,
    field: str,
    deterministic_value: Any,
    annotation_text: str,
    deterministic_type: Optional[str] = None,
) -> str:
    text = annotation_text or ""
    if field == "spacing":
        vals = list(deterministic_value or [])
        if not vals:
            return DET_UNKNOWN
        toks = _spacing_tokens(text)
        if toks and len(toks) > len(vals):
            return DET_PARTIAL
        return DET_CONFIRMED
    if field in ("diameter", "legs", "quantity"):
        if deterministic_value in (None, "", []):
            return DET_UNKNOWN
        return DET_CONFIRMED
    if field in ("semantic_type", "reinforcement_role", "beam_association"):
        if deterministic_value in (None, "", "UNKNOWN", "UNCERTAIN"):
            return DET_UNKNOWN
        return DET_CONFIRMED
    if deterministic_value in (None, "", "UNKNOWN", []):
        return DET_UNKNOWN
    return DET_CONFIRMED


__all__ = ["classify_deterministic_status"]
