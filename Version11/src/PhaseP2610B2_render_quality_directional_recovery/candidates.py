"""Bounded direction-aware candidate actions. No beam-ID logic. No combinatorial search."""
from __future__ import annotations

from typing import Any, Dict, List

from .orientation import HORIZONTAL, VERTICAL
from .quality import STATUS_BLACK, STATUS_EMPTY, STATUS_LOW_INFO, STATUS_MISSING
from .recovery import (
    ACTION_BALANCED,
    ACTION_EXPAND_BOTH_X,
    ACTION_EXPAND_BOTH_Y,
    ACTION_EXPAND_BOTTOM,
    ACTION_EXPAND_LEFT,
    ACTION_EXPAND_RIGHT,
    ACTION_EXPAND_TOP,
    ACTION_SHIFT_CONTENT,
    ACTION_TRIM_EMPTY,
)


def generate_candidate_actions(
    diagnostic: Dict[str, Any],
    *,
    orientation: str,
    crop_type: str,
) -> List[str]:
    """At most three recovery actions. Baseline is never included (already rendered)."""
    primary = diagnostic.get("primary_status")
    if primary in (STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING):
        return [ACTION_SHIFT_CONTENT, ACTION_TRIM_EMPTY, ACTION_BALANCED]
    empty = list(diagnostic.get("empty_sides") or [])
    contact = dict(diagnostic.get("meaningful_border_contact") or {})
    actions: List[str] = []
    if empty:
        actions.append(ACTION_TRIM_EMPTY)
        actions.append(ACTION_SHIFT_CONTENT)
    if orientation == VERTICAL:
        if contact.get("top"):
            actions.append(ACTION_EXPAND_TOP)
        if contact.get("bottom"):
            actions.append(ACTION_EXPAND_BOTTOM)
        if contact.get("top") or contact.get("bottom"):
            actions.append(ACTION_EXPAND_BOTH_Y)
    else:
        if contact.get("left"):
            actions.append(ACTION_EXPAND_LEFT)
        if contact.get("right"):
            actions.append(ACTION_EXPAND_RIGHT)
        if contact.get("left") or contact.get("right"):
            actions.append(ACTION_EXPAND_BOTH_X)
    if not actions:
        actions.append(ACTION_BALANCED)
    out: List[str] = []
    for a in actions:
        if a not in out:
            out.append(a)
    return out[:3]
