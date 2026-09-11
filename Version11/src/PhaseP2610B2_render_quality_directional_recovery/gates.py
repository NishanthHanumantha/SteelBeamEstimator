"""Recovery-entry gates. CLIP alone does not force recovery. No beam-ID logic."""
from __future__ import annotations

from typing import Any, Dict, Tuple

from .orientation import HORIZONTAL, VERTICAL
from .quality import STATUS_BLACK, STATUS_EMPTY, STATUS_LOW_CTX, STATUS_LOW_INFO, STATUS_MISSING


def needs_recovery(
    diagnostic: Dict[str, Any],
    *,
    crop_type: str,
    orientation: str,
) -> Tuple[bool, str]:
    primary = diagnostic.get("primary_status")
    if primary in (STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING):
        return True, str(primary)
    contact = dict(diagnostic.get("meaningful_border_contact") or {})
    empty = list(diagnostic.get("empty_sides") or [])
    if empty:
        return True, "EMPTY_REGION"
    if crop_type == "detail":
        return False, "DETAIL_SCREEN_PASS"
    if orientation == HORIZONTAL and contact.get("left") and contact.get("right"):
        return True, "HORIZONTAL_TRUNCATION_SUSPECT"
    if orientation == VERTICAL and contact.get("top") and contact.get("bottom"):
        return True, "VERTICAL_TRUNCATION_SUSPECT"
    if primary == STATUS_LOW_CTX and float(diagnostic.get("coverage_x") or 1.0) < 0.40:
        return True, "TARGET_CONTEXT_WEAK"
    return False, "SCREEN_PASS"
