"""P2.6.1 stratified recovery metrics. No steel / BBS / Excel accuracy."""
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
    STRATA,
)

TYPE_GROUPS = (
    "STIRRUP",
    "LONGITUDINAL_REINFORCEMENT",
    "SIDE_FACE_REINFORCEMENT",
    "SPACER",
    "OTHER",
    "UNKNOWN",
)


def _rate(n: int, d: int) -> Optional[float]:
    if d <= 0:
        return None
    return round(n / d, 6)


def _tokens(usage: Dict[str, Any]) -> Dict[str, int]:
    inp = int((usage or {}).get("input_tokens") or (usage or {}).get("estimated_input_tokens") or 0)
    out = int((usage or {}).get("output_tokens") or (usage or {}).get("estimated_output_tokens") or 0)
    return {"input_tokens": inp, "output_tokens": out}


def _type_group(raw: Any) -> str:
    t = str(raw or "UNKNOWN").strip().upper()
    if t in ("OTHER_REINFORCEMENT", "OTHER"):
        return "OTHER"
    if t in TYPE_GROUPS:
        return t
    return "UNKNOWN"


def _slice_metrics(candidates: List[Dict[str, Any]], missed_gt: int) -> Dict[str, Any]:
    n = len(candidates)
    det = Counter(str(c.get("deterministic_match_status") or "") for c in candidates)
    gt = Counter(str(c.get("gt_match_status") or "") for c in candidates)
    true_rec = gt.get(GT_TRUE_RECOVERY, 0)
    unsupported = gt.get(GT_UNSUPPORTED, 0)
    ambiguous = gt.get(GT_AMBIGUOUS, 0)
    already = det.get(DET_ALREADY, 0)
    gt_supported = sum(1 for c in candidates if c.get("gt_supported"))
    strict_rec = sum(1 for c in candidates if c.get("strict_true_recovery"))
    return {
        "candidates": n,
        "already_detected": already,
        "potentially_missing": det.get(DET_MISSING, 0),
        "conflicting": det.get("CONFLICTING", 0),
        "true_recoveries": true_rec,
        "strict_true_recoveries": strict_rec,
        "unsupported": unsupported,
        "ambiguous": ambiguous,
        "gt_supported_candidates": gt_supported,
        "missed_gt_bars": missed_gt,
        "TRUE_RECOVERY_RATE": _rate(true_rec, missed_gt),
        "STRICT_TRUE_RECOVERY_RATE": _rate(strict_rec, missed_gt),
        "VISION_CANDIDATE_PRECISION": _rate(gt_supported, n),
        "UNSUPPORTED_RATE": _rate(unsupported, n),
        "DUPLICATE_RATE": _rate(already, n),
        "AMBIGUOUS_RATE": _rate(ambiguous, n),
        "gt_status_counts": dict(gt),
        "det_status_counts": dict(det),
    }


def compute_metrics(
    *,
    observations: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    missed_gt_overall: int,
    missed_by_stratum: Optional[Dict[str, int]] = None,
    missed_by_set: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    api_calls = sum(1 for o in observations if o.get("live_call"))
    cache_hits = sum(1 for o in observations if o.get("cache_hit"))
    cache_misses = sum(1 for o in observations if not o.get("cache_hit"))
    budget_stops = sum(1 for o in observations if o.get("budget_stop"))
    inp = out = 0
    for o in observations:
        tok = _tokens(o.get("usage") or {})
        inp += tok["input_tokens"]
        out += tok["output_tokens"]
    cost = (inp / 1_000_000.0) * INPUT_USD_PER_MTOK + (out / 1_000_000.0) * OUTPUT_USD_PER_MTOK

    overall = _slice_metrics(candidates, missed_gt_overall)
    true_rec = int(overall["true_recoveries"])
    cost_per = round(cost / true_rec, 4) if true_rec > 0 else None

    by_stratum: Dict[str, Any] = {}
    missed_by_stratum = missed_by_stratum or {}
    for stratum in STRATA:
        subset = [c for c in candidates if c.get("stratum") == stratum]
        by_stratum[stratum] = _slice_metrics(subset, int(missed_by_stratum.get(stratum) or 0))

    by_type: Dict[str, Any] = {}
    for group in TYPE_GROUPS:
        subset = [c for c in candidates if _type_group(c.get("candidate_type")) == group]
        slice_m = _slice_metrics(subset, 0)
        slice_m.pop("TRUE_RECOVERY_RATE", None)
        slice_m.pop("STRICT_TRUE_RECOVERY_RATE", None)
        slice_m.pop("missed_gt_bars", None)
        by_type[group] = slice_m

    by_set: Dict[str, Any] = {}
    missed_by_set = missed_by_set or {}
    set_names = sorted({str(c.get("source_set") or "") for c in candidates if c.get("source_set")})
    for name in set_names:
        subset = [c for c in candidates if c.get("source_set") == name]
        by_set[name] = _slice_metrics(subset, int(missed_by_set.get(name) or 0))

    known = [c for c in candidates if c.get("drawing_visibility") == "KNOWN"]
    unseen = [c for c in candidates if c.get("drawing_visibility") != "KNOWN"]
    if len(known) == 0:
        known_rate: Any = "N/A — insufficient sample"
        unseen_rate: Any = overall["TRUE_RECOVERY_RATE"] if unseen else "N/A — insufficient sample"
    else:
        known_rate = None
        unseen_rate = overall["TRUE_RECOVERY_RATE"] if unseen else "N/A — insufficient sample"
    known_vs_unseen = {
        "known_candidates": len(known),
        "unseen_candidates": len(unseen),
        "KNOWN_RECOVERY_RATE": known_rate,
        "UNSEEN_RECOVERY_RATE": unseen_rate,
        "note": "Fourth/Fifth/Sixth are QA.3.0 unseen sets. First Set (known) was not sampled.",
    }

    ocr_rec = sum(
        1
        for c in candidates
        if c.get("gt_match_status") == GT_TRUE_RECOVERY
        and "\\X" in str(c.get("annotation_text") or "")
    )
    rec_types = Counter(
        _type_group(c.get("candidate_type"))
        for c in candidates
        if c.get("gt_match_status") == GT_TRUE_RECOVERY
    )

    return {
        "BEAMS_INSPECTED": len(observations),
        "VISION_CALLS": api_calls + cache_hits,
        "vision_api_calls": api_calls,
        "live_calls": api_calls,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "budget_stops": budget_stops,
        "VISION_CANDIDATES": overall["candidates"],
        "ALREADY_DETECTED": overall["already_detected"],
        "POTENTIALLY_MISSING": overall["potentially_missing"],
        "TRUE_RECOVERIES": true_rec,
        "STRICT_TRUE_RECOVERIES": overall["strict_true_recoveries"],
        "GT_SUPPORTED": overall["gt_supported_candidates"],
        "UNSUPPORTED": overall["unsupported"],
        "AMBIGUOUS": overall["ambiguous"],
        "missed_gt_bars_on_sampled_beams": missed_gt_overall,
        "TRUE_RECOVERY_RATE": overall["TRUE_RECOVERY_RATE"],
        "STRICT_TRUE_RECOVERY_RATE": overall["STRICT_TRUE_RECOVERY_RATE"],
        "VISION_CANDIDATE_PRECISION": overall["VISION_CANDIDATE_PRECISION"],
        "UNSUPPORTED_RATE": overall["UNSUPPORTED_RATE"],
        "DUPLICATE_RATE": overall["DUPLICATE_RATE"],
        "AMBIGUOUS_RATE": overall["AMBIGUOUS_RATE"],
        "input_tokens": inp,
        "output_tokens": out,
        "estimated_usd": round(cost, 4),
        "cost_per_true_recovery": cost_per,
        "true_recovery_ocr_corrupted_text": ocr_rec,
        "true_recovery_by_type": dict(rec_types),
        "overall": overall,
        "by_stratum": by_stratum,
        "by_candidate_type": by_type,
        "by_drawing_set": by_set,
        "known_vs_unseen": known_vs_unseen,
        "gt_status_counts": overall["gt_status_counts"],
        "det_status_counts": overall["det_status_counts"],
        "gt_matches": Counter(str(c.get("gt_match_status") or "") for c in candidates).get(GT_MATCH, 0),
    }


def classify_benchmark(
    metrics: Dict[str, Any],
    *,
    firewall_ok: bool = True,
    review_blocker_or_high: bool = False,
) -> Dict[str, str]:
    """Evidence-based recommendation. Never PRODUCTION_READY."""
    true_rec = int(metrics.get("TRUE_RECOVERIES") or 0)
    prec = metrics.get("VISION_CANDIDATE_PRECISION")
    uns = metrics.get("UNSUPPORTED_RATE")
    by_stratum = metrics.get("by_stratum") or {}
    easy = by_stratum.get("EASY") or {}
    normal = by_stratum.get("NORMAL") or {}
    difficult = by_stratum.get("DIFFICULT") or {}
    easy_dup = easy.get("DUPLICATE_RATE")
    easy_uns = easy.get("UNSUPPORTED_RATE")
    normal_rec = int(normal.get("true_recoveries") or 0)
    difficult_rec = int(difficult.get("true_recoveries") or 0)
    only_difficult = true_rec > 0 and normal_rec == 0 and int(easy.get("true_recoveries") or 0) == 0

    prec_ok = prec is not None and prec >= 0.50
    uns_ok = uns is None or uns <= 0.25
    easy_dup_high = easy_dup is not None and easy_dup >= 0.70
    easy_uns_high = easy_uns is not None and easy_uns >= 0.25
    quality_poor = (prec is not None and prec < 0.25) or (uns is not None and uns >= 0.50)

    if review_blocker_or_high or not firewall_ok:
        decision = "REFINE_CANDIDATE_RECOVERY"
        strength = "BLOCKED_PENDING_FIX"
    elif true_rec == 0 or quality_poor:
        decision = "STOP_NEGATIVE"
        strength = "NEGATIVE"
    elif (
        true_rec >= 3
        and prec_ok
        and uns_ok
        and not easy_dup_high
        and not only_difficult
        and firewall_ok
        and not review_blocker_or_high
    ):
        decision = "PROCEED_TO_ENGINEERING_RECOMPUTE_PILOT"
        strength = "STRONG"
    else:
        decision = "REFINE_CANDIDATE_RECOVERY"
        strength = "PROMISING"

    return {
        "strength": strength,
        "decision": decision,
        "note": (
            "Stratified-sample classification only. Not PRODUCTION_READY. "
            "Deterministic production remains sole authority. "
            f"only_difficult_recoveries={only_difficult} "
            f"easy_duplicate_high={easy_dup_high} easy_unsupported_high={easy_uns_high}"
        ),
    }


__all__ = ["TYPE_GROUPS", "classify_benchmark", "compute_metrics"]
