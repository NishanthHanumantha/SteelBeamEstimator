"""Baseline classification from B.1 artefacts + cheap PNG quality. No beam-ID crop rules."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP2610B2_render_quality_directional_recovery.quality import (
    STATUS_BLACK,
    STATUS_EMPTY,
    STATUS_LOW_INFO,
    STATUS_MISSING,
)

from .config import CLASS_FROZEN, CLASS_REVIEW, CLASS_TARGET, CRUSH_COVERAGE_MAX

_BLANK = {STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING}
_TRUNC = {"HORIZONTAL_TRUNCATION", "VERTICAL_TRUNCATION", "EMPTY_OR_NEAR_EMPTY_CROP", "RENDER_FAILURE", "MISSING_GEOMETRY"}


def classify_beam(
    *,
    b1: Dict[str, Any],
    ctx_quality: Dict[str, Any],
    det_quality: Dict[str, Any],
    b2: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    reasons: List[str] = []
    failures = [str(x) for x in (b1.get("failure_categories") or [])]
    complete = (b1.get("completeness_status") == "PASS") or bool(b1.get("p2610b_complete_flag"))
    ctx_status = str(ctx_quality.get("primary_status") or STATUS_MISSING)
    det_status = str(det_quality.get("primary_status") or STATUS_MISSING)

    if not complete or any(f in _TRUNC for f in failures):
        reasons.append("B1_INCOMPLETE_OR_TRUNCATION")
    if ctx_status in _BLANK:
        reasons.append("BASELINE_CONTEXT_BLANK_CLASS")
    if det_status in _BLANK:
        reasons.append("BASELINE_DETAIL_BLANK_CLASS")
    if ctx_quality.get("empty_sides"):
        reasons.append("UNUSED_CANVAS_CRUSH")
    covx = float(ctx_quality.get("coverage_x") or 1.0)
    covy = float(ctx_quality.get("coverage_y") or 1.0)
    dark = float(ctx_quality.get("dark_ratio") or 0.0)
    if covx < CRUSH_COVERAGE_MAX and covy < 0.58:
        reasons.append("LOW_TARGET_OCCUPANCY")
    if dark >= 0.50 and covx < 0.58:
        reasons.append("UNUSED_CANVAS_CRUSH")
    if b2 is not None and b2.get("final_vision_usable") is False:
        reasons.append("B2_NOT_USABLE")
    if b2 is not None and (
        str(b2.get("context_status") or "") in _BLANK or str(b2.get("detail_status") or "") in _BLANK
    ):
        reasons.append("B2_BLANK_CLASS")

    ctx_png = b1.get("context_crop_path")
    det_png = b1.get("detail_crop_path")
    if not ctx_png or not det_png:
        reasons.append("BASELINE_PNG_MISSING")

    if reasons:
        return {"classification": CLASS_TARGET, "reasons": reasons, "b1_complete": complete}
    return {"classification": CLASS_FROZEN, "reasons": ["B1_COMPLETE_AND_RENDER_OK"], "b1_complete": complete}


__all__ = ["classify_beam"]
