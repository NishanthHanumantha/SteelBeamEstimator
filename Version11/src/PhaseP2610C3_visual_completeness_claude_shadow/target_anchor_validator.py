"""Target identity / association checks from image evidence only. No beam-ID rules."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import COVERAGE_AMBIGUOUS_MAX, EMPTY_SIDES_AMBIGUOUS_MIN, CRITICAL_STATUSES
from .evidence_model import SelectedRender


def _critical(img: SelectedRender) -> bool:
    if img.critical_failure:
        return True
    if img.primary_status in CRITICAL_STATUSES:
        return True
    integ = img.integrity or {}
    if integ.get("file_missing") or integ.get("sha_mismatch"):
        return True
    return False


def validate_target_anchor(context: SelectedRender, detail: SelectedRender) -> Dict[str, Any]:
    reasons: List[str] = []
    ctx_crit = _critical(context)
    det_crit = _critical(detail)
    identity_ok = (not ctx_crit) and bool((context.integrity or {}).get("integrity_ok") or context.path)
    geometry_ok = (not det_crit) and bool((detail.integrity or {}).get("integrity_ok") or detail.path)
    if ctx_crit or not identity_ok:
        reasons.append("CONTEXT_IDENTITY_UNAVAILABLE")
    if det_crit or not geometry_ok:
        reasons.append("DETAIL_CORE_UNAVAILABLE")

    association_ambiguous = False
    if not ctx_crit and context.coverage_x < COVERAGE_AMBIGUOUS_MAX:
        association_ambiguous = True
        reasons.append("CONTEXT_INSUFFICIENT_SURROUNDINGS")
    if (
        not ctx_crit
        and not det_crit
        and len(context.empty_sides) >= EMPTY_SIDES_AMBIGUOUS_MIN
        and len(detail.empty_sides) >= EMPTY_SIDES_AMBIGUOUS_MIN
    ):
        association_ambiguous = True
        reasons.append("SPARSE_CONTENT_BOTH_CROPS")
    if association_ambiguous:
        reasons.append("TARGET_ASSOCIATION_AMBIGUOUS")

    stack = {
        "title_region": "AVAILABLE" if (not ctx_crit and context.usable_status) else ("MISSING_OR_CLIPPED" if ctx_crit else "LIMITED"),
        "stirrup_region": "CLIP_SUSPECT" if "BOTTOM_BORDER_CONTACT" in detail.quality_flags or "TOP_BORDER_CONTACT" in detail.quality_flags else "OBSERVABLE_IF_DRAWN",
        "bottom_region": "CLIP_SUSPECT" if "bottom" in detail.empty_sides else "OBSERVABLE_IF_DRAWN",
        "top_region": "CLIP_SUSPECT" if "top" in detail.empty_sides else "OBSERVABLE_IF_DRAWN",
        "dimension_extra_region": "NOT_REQUIRED",
        "note": "Absence of extras is not a failure. NOT_PRESENT_IN_DRAWING cannot be proven from PNG metrics alone.",
    }
    return {
        "identity_ok": identity_ok,
        "geometry_ok": geometry_ok,
        "association_ambiguous": association_ambiguous,
        "reason_codes": reasons,
        "stack_observability": stack,
        "mixed_source": context.source_phase != detail.source_phase,
    }


__all__ = ["validate_target_anchor"]
