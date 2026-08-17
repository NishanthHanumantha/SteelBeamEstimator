"""P2.6 pilot recovery metrics. No steel / BBS / Excel accuracy."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from .config import (
    DET_ALREADY,
    DET_MISSING,
    GT_AMBIGUOUS,
    GT_DUPLICATE,
    GT_MATCH,
    GT_TRUE_RECOVERY,
    GT_UNSUPPORTED,
    INPUT_USD_PER_MTOK,
    OUTPUT_USD_PER_MTOK,
)


def _rate(n: int, d: int) -> Optional[float]:
    if d <= 0:
        return None
    return round(n / d, 6)


def _tokens(usage: Dict[str, Any]) -> Dict[str, int]:
    inp = int((usage or {}).get("input_tokens") or (usage or {}).get("estimated_input_tokens") or 0)
    out = int((usage or {}).get("output_tokens") or (usage or {}).get("estimated_output_tokens") or 0)
    return {"input_tokens": inp, "output_tokens": out}


def compute_metrics(
    *,
    observations: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    missed_gt_on_pilot: int,
) -> Dict[str, Any]:
    api_calls = sum(1 for o in observations if o.get("live_call"))
    cache_hits = sum(1 for o in observations if o.get("cache_hit"))
    cache_misses = sum(1 for o in observations if not o.get("cache_hit"))
    inp = out = 0
    for o in observations:
        tok = _tokens(o.get("usage") or {})
        inp += tok["input_tokens"]
        out += tok["output_tokens"]
    cost = (inp / 1_000_000.0) * INPUT_USD_PER_MTOK + (out / 1_000_000.0) * OUTPUT_USD_PER_MTOK

    n = len(candidates)
    det = Counter(str(c.get("deterministic_match_status") or "") for c in candidates)
    gt = Counter(str(c.get("gt_match_status") or "") for c in candidates)
    types = Counter(str(c.get("candidate_type") or "UNKNOWN") for c in candidates)
    rec_types = Counter(
        str(c.get("candidate_type") or "UNKNOWN")
        for c in candidates
        if c.get("gt_match_status") == GT_TRUE_RECOVERY
    )
    rec_dia = Counter(
        str(c.get("diameter_mm"))
        for c in candidates
        if c.get("gt_match_status") == GT_TRUE_RECOVERY and c.get("diameter_mm") is not None
    )
    ocr_rec = sum(
        1
        for c in candidates
        if c.get("gt_match_status") == GT_TRUE_RECOVERY
        and "\\X" in str(c.get("annotation_text") or "")
    )
    gt_supported = sum(1 for c in candidates if c.get("gt_supported"))
    true_rec = gt.get(GT_TRUE_RECOVERY, 0)
    unsupported = gt.get(GT_UNSUPPORTED, 0)
    ambiguous = gt.get(GT_AMBIGUOUS, 0)
    duplicates = gt.get(GT_DUPLICATE, 0) + det.get(DET_ALREADY, 0) * 0
    # Duplicate rate uses already-detected deterministic status (required definition).
    already = det.get(DET_ALREADY, 0)

    return {
        "pilot_beams_inspected": len(observations),
        "vision_api_calls": api_calls,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "vision_candidates": n,
        "already_detected": already,
        "potentially_missing": det.get(DET_MISSING, 0),
        "conflicting": det.get("CONFLICTING", 0),
        "det_unknown": det.get("UNKNOWN", 0),
        "gt_matches": gt.get(GT_MATCH, 0),
        "true_recoveries": true_rec,
        "unsupported": unsupported,
        "ambiguous": ambiguous,
        "duplicates_gt_status": duplicates,
        "gt_supported_candidates": gt_supported,
        "missed_gt_bars_on_pilot_beams": missed_gt_on_pilot,
        "TRUE_RECOVERY_RATE": _rate(true_rec, missed_gt_on_pilot),
        "VISION_CANDIDATE_PRECISION": _rate(gt_supported, n),
        "UNSUPPORTED_RATE": _rate(unsupported, n),
        "DUPLICATE_RATE": _rate(already, n),
        "AMBIGUOUS_RATE": _rate(ambiguous, n),
        "candidate_type_counts": dict(types),
        "true_recovery_by_type": dict(rec_types),
        "true_recovery_by_diameter": dict(rec_dia),
        "true_recovery_ocr_corrupted_text": ocr_rec,
        "input_tokens": inp,
        "output_tokens": out,
        "estimated_usd": round(cost, 4),
        "gt_status_counts": dict(gt),
        "det_status_counts": dict(det),
    }


def classify_pilot(metrics: Dict[str, Any]) -> Dict[str, str]:
    """Evidence-based recommendation. Not production promotion."""
    true_rec = int(metrics.get("true_recoveries") or 0)
    prec = metrics.get("VISION_CANDIDATE_PRECISION")
    uns = metrics.get("UNSUPPORTED_RATE")
    dup = metrics.get("DUPLICATE_RATE")
    prec_ok = prec is not None and prec >= 0.25
    uns_ok = uns is None or uns <= 0.50
    dup_high = dup is not None and dup >= 0.70

    if true_rec >= 3 and prec_ok and uns_ok and not dup_high:
        strength = "STRONG"
        decision = "PROCEED_TO_LARGER_EXPERIMENT"
    elif true_rec >= 1 and (not prec_ok or not uns_ok or dup_high):
        strength = "PROMISING"
        decision = "REFINE_P2.6_PILOT"
    elif true_rec >= 1:
        strength = "PROMISING"
        decision = "PROCEED_TO_LARGER_EXPERIMENT"
    elif true_rec == 0 and int(metrics.get("potentially_missing") or 0) > 0:
        strength = "WEAK"
        decision = "REFINE_P2.6_PILOT"
    else:
        strength = "NEGATIVE"
        decision = "STOP_NEGATIVE"
    return {
        "strength": strength,
        "decision": decision,
        "note": (
            "Pilot classification only. Not PRODUCTION_READY. "
            "Deterministic production remains sole authority."
        ),
    }


__all__ = ["classify_pilot", "compute_metrics"]
