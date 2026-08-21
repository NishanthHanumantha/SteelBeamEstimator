"""Deterministic visual completeness gate. Evidence only. No beam-ID rules. No Vision."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    CRITICAL_STATUSES,
    STATUS_LIMITED,
    STATUS_NOT_READY,
    STATUS_READY,
    STATUS_REVIEW,
    STILL_CRITICAL_SELECTION,
)
from .evidence_model import SelectedRender
from .target_anchor_validator import validate_target_anchor


def _integrity_fail(img: SelectedRender) -> List[str]:
    codes: List[str] = []
    integ = img.integrity or {}
    if integ.get("file_missing") or not img.path:
        codes.append(f"{img.crop_type.upper()}_FILE_MISSING")
    if integ.get("sha_mismatch"):
        codes.append(f"{img.crop_type.upper()}_SHA_MISMATCH")
    if img.critical_failure or img.primary_status in CRITICAL_STATUSES:
        codes.append(f"{img.crop_type.upper()}_CRITICAL_{img.primary_status or 'FAILURE'}")
    if img.selection_status in STILL_CRITICAL_SELECTION:
        codes.append(f"{img.crop_type.upper()}_{img.selection_status}")
    return codes


def _limitation_flags(img: SelectedRender) -> List[str]:
    codes: List[str] = []
    flags = set(img.quality_flags or [])
    if img.primary_status == "BORDER_CLIPPING_SUSPECT" or "BORDER_CLIPPING_SUSPECT" in flags:
        codes.append(f"{img.crop_type.upper()}_CLIP")
    if "HORIZONTAL_TRUNCATION_SUSPECT" in flags:
        codes.append(f"{img.crop_type.upper()}_HORIZONTAL_TRUNCATION")
    if "VERTICAL_TRUNCATION_SUSPECT" in flags:
        codes.append(f"{img.crop_type.upper()}_VERTICAL_TRUNCATION")
    if img.empty_sides:
        codes.append(f"{img.crop_type.upper()}_EMPTY_SIDES")
    if img.primary_status == "LOW_CONTEXT_QUALITY":
        codes.append(f"{img.crop_type.upper()}_LOW_CONTEXT_QUALITY")
    return codes


def evaluate_completeness(context: SelectedRender, detail: SelectedRender) -> Dict[str, Any]:
    """Classify selected context+detail for Vision eligibility. Independent of beam identity."""
    reasons: List[str] = []
    reasons.extend(_integrity_fail(context))
    reasons.extend(_integrity_fail(detail))
    anchor = validate_target_anchor(context, detail)
    reasons.extend(anchor.get("reason_codes") or [])

    critical = bool(_integrity_fail(context) or _integrity_fail(detail) or not anchor.get("identity_ok") or not anchor.get("geometry_ok"))
    if critical:
        status = STATUS_NOT_READY
        reasons.append("CRITICAL_VISUAL_FAILURE")
    elif anchor.get("association_ambiguous"):
        status = STATUS_REVIEW
        reasons.append("AMBIGUOUS_TARGET_ASSOCIATION")
    elif (not context.usable_status) or (not detail.usable_status):
        status = STATUS_REVIEW
        reasons.append("SELECTED_NOT_VISUALLY_USABLE")
    else:
        limits = _limitation_flags(context) + _limitation_flags(detail)
        reasons.extend(limits)
        if limits:
            status = STATUS_LIMITED
            reasons.append("MINOR_CLIP_OR_SLIVER")
        else:
            status = STATUS_READY
            reasons.append("SUFFICIENT_TARGET_EVIDENCE")

    return {
        "status": status,
        "reason_codes": list(dict.fromkeys(reasons)),
        "image_exists": {
            "context": bool((context.integrity or {}).get("exists") or context.path),
            "detail": bool((detail.integrity or {}).get("exists") or detail.path),
        },
        "image_visually_usable": {
            "context": bool(context.usable_status) and not context.critical_failure,
            "detail": bool(detail.usable_status) and not detail.critical_failure,
        },
        "sufficient_for_target_interpretation": status in (STATUS_READY, STATUS_LIMITED),
        "anchor": anchor,
        "context_source_phase": context.source_phase,
        "detail_source_phase": detail.source_phase,
    }


__all__ = ["evaluate_completeness"]
