"""P2.6.2 gated-replay metrics. Not a new Vision benchmark."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from .config import (
    DECISION_CALL,
    DECISION_HOLD,
    DECISION_SKIP,
    DET_ALREADY,
    STRATA,
    TYPE_GROUPS,
)

GT_TRUE_RECOVERY = "TRUE_RECOVERY"
GT_UNSUPPORTED = "UNSUPPORTED"
GT_AMBIGUOUS = "AMBIGUOUS"


def _rate(n: int, d: int) -> Optional[float]:
    if d <= 0:
        return None
    return round(n / d, 6)


def _type_group(raw: Any) -> str:
    t = str(raw or "UNKNOWN").strip().upper()
    if t in ("OTHER_REINFORCEMENT", "OTHER"):
        return "OTHER"
    if t in TYPE_GROUPS:
        return t
    if t == "UNKNOWN":
        return "OTHER"
    return "OTHER"


def _cand_slice(cands: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(cands)
    already = sum(1 for c in cands if c.get("deterministic_match_status") == DET_ALREADY)
    true_rec = sum(1 for c in cands if c.get("gt_match_status") == GT_TRUE_RECOVERY)
    unsupported = sum(1 for c in cands if c.get("gt_match_status") == GT_UNSUPPORTED)
    ambiguous = sum(1 for c in cands if c.get("gt_match_status") == GT_AMBIGUOUS)
    supported = sum(1 for c in cands if c.get("gt_supported"))
    return {
        "candidates": n,
        "duplicates": already,
        "true_recoveries": true_rec,
        "unsupported": unsupported,
        "ambiguous": ambiguous,
        "precision": _rate(supported, n),
        "duplicate_rate": _rate(already, n),
        "unsupported_rate": _rate(unsupported, n),
        "ambiguous_rate": _rate(ambiguous, n),
    }


def compute_metrics(
    *,
    decisions: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
    false_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total = len(decisions)
    n_call = sum(1 for d in decisions if d.get("decision") == DECISION_CALL)
    n_skip = sum(1 for d in decisions if d.get("decision") == DECISION_SKIP)
    n_hold = sum(1 for d in decisions if d.get("decision") == DECISION_HOLD)
    base = _cand_slice(baseline_candidates)
    gated = _cand_slice(gated_candidates)
    base_rec = int(base["true_recoveries"])
    gated_rec = int(gated["true_recoveries"])
    lost = max(0, base_rec - gated_rec)
    retained = gated_rec
    call_reduction = _rate(total - n_call, total)
    rec_per_call_base = _rate(base_rec, total)
    rec_per_call_gated = _rate(gated_rec, n_call)
    per_100_base = round(100.0 * base_rec / total, 4) if total else None
    per_100_gated = round(100.0 * gated_rec / n_call, 4) if n_call else None

    by_stratum: Dict[str, Any] = {}
    for stratum in STRATA:
        dsub = [d for d in decisions if d.get("eval_stratum") == stratum]
        bsub = [c for c in baseline_candidates if c.get("stratum") == stratum]
        gsub = [c for c in gated_candidates if c.get("stratum") == stratum]
        bs = _cand_slice(bsub)
        gs = _cand_slice(gsub)
        n_c = sum(1 for d in dsub if d.get("decision") == DECISION_CALL)
        by_stratum[stratum] = {
            "beams": len(dsub),
            "call": n_c,
            "skip": sum(1 for d in dsub if d.get("decision") == DECISION_SKIP),
            "hold": sum(1 for d in dsub if d.get("decision") == DECISION_HOLD),
            "call_rate": _rate(n_c, len(dsub)),
            "calls_saved": len(dsub) - n_c,
            "baseline": bs,
            "gated": gs,
            "recoveries_retained": gs["true_recoveries"],
            "recoveries_lost": max(0, int(bs["true_recoveries"]) - int(gs["true_recoveries"])),
        }

    by_type: Dict[str, Any] = {}
    for group in TYPE_GROUPS:
        bsub = [c for c in baseline_candidates if _type_group(c.get("candidate_type")) == group]
        gsub = [c for c in gated_candidates if _type_group(c.get("candidate_type")) == group]
        bs = _cand_slice(bsub)
        gs = _cand_slice(gsub)
        by_type[group] = {
            "baseline_candidates": bs["candidates"],
            "gated_candidates": gs["candidates"],
            "baseline_duplicates": bs["duplicates"],
            "gated_duplicates": gs["duplicates"],
            "baseline_true_recoveries": bs["true_recoveries"],
            "gated_true_recoveries": gs["true_recoveries"],
            "retained_recoveries": gs["true_recoveries"],
            "lost_recoveries": max(0, int(bs["true_recoveries"]) - int(gs["true_recoveries"])),
        }

    call_reasons: Counter = Counter()
    skip_reasons: Counter = Counter()
    for d in decisions:
        for r in d.get("reason_codes") or []:
            if d.get("decision") == DECISION_CALL:
                call_reasons[str(r)] += 1
            elif d.get("decision") == DECISION_SKIP:
                skip_reasons[str(r)] += 1

    return {
        "label": "Gated replay using frozen P2.6.1 Vision responses. Not a new Vision benchmark.",
        "TOTAL_BEAMS": total,
        "CALL_BEAMS": n_call,
        "SKIP_BEAMS": n_skip,
        "HOLD_BEAMS": n_hold,
        "CALL_RATE": _rate(n_call, total),
        "CALL_REDUCTION": call_reduction,
        "TOTAL_BASELINE_VISION_CANDIDATES": base["candidates"],
        "GATED_VISION_CANDIDATES": gated["candidates"],
        "DUPLICATES_BASELINE": base["duplicates"],
        "DUPLICATES_GATED": gated["duplicates"],
        "DUPLICATE_RATE_BASELINE": base["duplicate_rate"],
        "DUPLICATE_RATE_GATED": gated["duplicate_rate"],
        "BASELINE_PRECISION": base["precision"],
        "GATED_PRECISION": gated["precision"],
        "BASELINE_UNSUPPORTED_RATE": base["unsupported_rate"],
        "GATED_UNSUPPORTED_RATE": gated["unsupported_rate"],
        "BASELINE_AMBIGUOUS_RATE": base["ambiguous_rate"],
        "GATED_AMBIGUOUS_RATE": gated["ambiguous_rate"],
        "BASELINE_TRUE_RECOVERIES": base_rec,
        "GATED_TRUE_RECOVERIES": gated_rec,
        "RECOVERIES_RETAINED": retained,
        "RECOVERIES_LOST": lost,
        "RECOVERY_RETENTION_RATE": _rate(retained, base_rec),
        "FALSE_SKIPS": len(false_skips),
        "FALSE_CALLS": len(false_calls),
        "FALSE_CALL_RATE": _rate(len(false_calls), n_call),
        "RECOVERY_RETENTION_PER_VISION_CALL": rec_per_call_gated,
        "TRUE_RECOVERIES_PER_100_VISION_CALLS_BASELINE": per_100_base,
        "TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED": per_100_gated,
        "TRUE_RECOVERIES_PER_CALL_BASELINE": rec_per_call_base,
        "by_stratum": by_stratum,
        "by_candidate_type": by_type,
        "call_reason_counts": dict(call_reasons),
        "skip_reason_counts": dict(skip_reasons),
        "baseline": base,
        "gated": gated,
        "hypothetical_baseline_calls": total,
        "gated_calls": n_call,
        "calls_saved": total - n_call,
        "replay_cost_usd": 0.0,
    }


def classify_gate(metrics: Dict[str, Any], *, firewall_ok: bool, review_high: bool) -> Dict[str, str]:
    red = metrics.get("CALL_REDUCTION")
    ret = metrics.get("RECOVERY_RETENTION_RATE")
    prec_b = metrics.get("BASELINE_PRECISION")
    prec_g = metrics.get("GATED_PRECISION")
    uns_b = metrics.get("BASELINE_UNSUPPORTED_RATE")
    uns_g = metrics.get("GATED_UNSUPPORTED_RATE")
    dup_g = metrics.get("DUPLICATE_RATE_GATED")
    lost = int(metrics.get("RECOVERIES_LOST") or 0)
    retained = int(metrics.get("RECOVERIES_RETAINED") or 0)

    red_ok = red is not None and red > 0.30
    ret_ok = ret is not None and ret >= 0.80
    prec_ok = prec_g is None or prec_b is None or prec_g + 1e-9 >= prec_b
    uns_ok = uns_g is None or uns_b is None or uns_g <= uns_b + 1e-9
    dup_ok = dup_g is not None and dup_g < 0.6570
    too_much_lost = retained == 0 or (ret is not None and ret < 0.50)

    if not firewall_ok or too_much_lost:
        decision = "STOP_NEGATIVE"
        strength = "NEGATIVE"
    elif review_high or not (red_ok and ret_ok and prec_ok and uns_ok and dup_ok):
        decision = "REFINE_SELECTIVE_GATE"
        strength = "PROMISING" if retained > 0 else "WEAK"
    else:
        decision = "PROCEED_TO_ENGINEERING_RECOMPUTE_PILOT"
        strength = "STRONG"
    return {
        "strength": strength,
        "decision": decision,
        "note": (
            "Gated-replay classification only. Not PRODUCTION_READY. "
            f"call_reduction_ok={red_ok} retention_ok={ret_ok} "
            f"precision_ok={prec_ok} unsupported_ok={uns_ok} duplicate_ok={dup_ok} "
            f"lost={lost}"
        ),
    }


__all__ = ["classify_gate", "compute_metrics"]
