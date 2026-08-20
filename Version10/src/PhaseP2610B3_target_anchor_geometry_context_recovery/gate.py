"""Deterministic completeness gate. PNG existence is not success. No beam-ID rules."""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from PhaseP2610B2_render_quality_directional_recovery.geometry import area, as_extent, intersect
from PhaseP2610B2_render_quality_directional_recovery.quality import STATUS_BLACK, STATUS_EMPTY, STATUS_LOW_INFO, STATUS_MISSING

from .anchor import endpoints_inside
from .config import ENDPOINT_TOL_MM, MAX_OCCUPANCY, MIN_OCCUPANCY, MIN_TARGET_COVERAGE, REPLACE_SCORE_MARGIN

_BLANK = {STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING}


def evaluate_candidate(
    *,
    extent: Sequence[float],
    anchor: Dict[str, Any],
    quality: Dict[str, Any],
) -> Dict[str, Any]:
    core = as_extent(anchor["core"])
    crop = as_extent(extent)
    hit = intersect(core, crop)
    cov = (area(hit) / area(core)) if hit and area(core) > 1.0 else 0.0
    occ = (area(hit) / area(crop)) if hit and area(crop) > 1.0 else 0.0
    start_ok, end_ok = endpoints_inside(core, crop, tol=ENDPOINT_TOL_MM)
    blank = str(quality.get("primary_status") or "") in _BLANK
    finite = all(abs(v) < 1e12 for v in crop) and crop[2] > crop[0] + 50 and crop[3] > crop[1] + 50
    ar = (crop[2] - crop[0]) / max(crop[3] - crop[1], 1.0)
    justified = ar >= 0.25 and ar <= 8.0
    flags = []
    if blank:
        flags.append("BLANK_OR_LOW_INFO")
    if cov < MIN_TARGET_COVERAGE:
        flags.append("TARGET_CORE_MISSED")
    if not start_ok or not end_ok:
        flags.append("TARGET_ENDPOINT_TRUNCATION")
    if occ < MIN_OCCUPANCY:
        flags.append("LOW_TARGET_OCCUPANCY")
    if occ > MAX_OCCUPANCY and cov < 0.95:
        flags.append("CONTEXT_TOO_TIGHT")
    if not finite or not justified:
        flags.append("CROP_SANITY_FAIL")
    score = 0.0
    if not blank and finite and justified:
        score += 3.0 * cov
        score += 1.4 if start_ok and end_ok else 0.0
        score += 0.8 if MIN_OCCUPANCY <= occ <= MAX_OCCUPANCY else 0.15
        score -= 0.15 * max(0.0, occ - 0.55)
        if quality.get("visually_usable"):
            score += 0.4
    return {
        "target_coverage": round(cov, 4),
        "target_occupancy": round(occ, 4),
        "start_inside": start_ok,
        "end_inside": end_ok,
        "endpoints_complete": bool(start_ok and end_ok),
        "blank": blank,
        "sane": bool(finite and justified),
        "flags": flags,
        "score": round(score, 4),
        "acceptable": (not blank) and finite and justified and cov >= 0.55,
    }


def should_replace(baseline: Dict[str, Any], candidate: Dict[str, Any], *, margin: float = REPLACE_SCORE_MARGIN) -> bool:
    if not candidate.get("acceptable"):
        return False
    if not baseline.get("acceptable") and candidate.get("acceptable"):
        return True
    return float(candidate.get("score") or 0.0) > float(baseline.get("score") or 0.0) + margin


__all__ = ["evaluate_candidate", "should_replace"]
