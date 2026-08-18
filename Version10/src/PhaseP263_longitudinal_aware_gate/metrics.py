"""P2.6.3 gated-replay metrics. Not a new Vision benchmark."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from PhaseP262_selective_vision_candidate_gate.metrics import compute_metrics as p262_compute_metrics

from .config import (
    COVER_DIA,
    COVER_FULL,
    COVER_LAYER,
    COVER_MISSING,
    COVER_MULTI,
    COVER_NONE,
    COVER_QTY,
    COVER_ROLE,
    COVER_UNASSOC,
    P262_BASELINE,
    TYPE_GROUPS,
)

GT_TRUE_RECOVERY = "TRUE_RECOVERY"


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
    return "OTHER"


def compute_metrics(
    *,
    decisions: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
    false_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    m = p262_compute_metrics(
        decisions=decisions,
        baseline_candidates=baseline_candidates,
        gated_candidates=gated_candidates,
        false_skips=false_skips,
        false_calls=false_calls,
    )
    m["label"] = (
        "Gated replay using frozen P2.6.1 Vision responses. "
        "P2.6.3 longitudinal-aware gate. Not a new Vision benchmark."
    )
    long_b = [c for c in baseline_candidates if _type_group(c.get("candidate_type")) == "LONGITUDINAL_REINFORCEMENT"]
    long_g = [c for c in gated_candidates if _type_group(c.get("candidate_type")) == "LONGITUDINAL_REINFORCEMENT"]
    stir_b = [c for c in baseline_candidates if _type_group(c.get("candidate_type")) == "STIRRUP"]
    stir_g = [c for c in gated_candidates if _type_group(c.get("candidate_type")) == "STIRRUP"]
    long_fs = [f for f in false_skips if "LONGITUDINAL" in str(f.get("candidate_class") or "").upper()]
    long_fc = [
        f
        for f in false_calls
        if "LONGITUDINAL" in str(f.get("candidate_class_hint") or f.get("reason_codes") or "").upper()
        or any("LONGITUDINAL" in str(r) or r == "MISSING_DETERMINISTIC_OBJECT" for r in (f.get("reason_codes") or []))
    ]
    cov_counts = Counter(str(d.get("longitudinal_coverage") or "") for d in decisions)
    cond_counts: Counter = Counter()
    for d in decisions:
        for c in d.get("coverage_conditions") or []:
            cond_counts[str(c)] += 1

    stir_base = sum(1 for c in stir_b if c.get("gt_match_status") == GT_TRUE_RECOVERY)
    stir_gat = sum(1 for c in stir_g if c.get("gt_match_status") == GT_TRUE_RECOVERY)
    long_base = sum(1 for c in long_b if c.get("gt_match_status") == GT_TRUE_RECOVERY)
    long_gat = sum(1 for c in long_g if c.get("gt_match_status") == GT_TRUE_RECOVERY)

    m["STIRRUP_BASELINE_TRUE_RECOVERIES"] = stir_base
    m["STIRRUP_GATED_TRUE_RECOVERIES"] = stir_gat
    m["STIRRUP_RECOVERY_RETENTION"] = _rate(stir_gat, stir_base)
    m["LONGITUDINAL_BASELINE_TRUE_RECOVERIES"] = long_base
    m["LONGITUDINAL_GATED_TRUE_RECOVERIES"] = long_gat
    m["LONGITUDINAL_RECOVERY_RETENTION"] = _rate(long_gat, long_base)
    m["LONGITUDINAL_FALSE_SKIPS"] = len(long_fs)
    m["LONGITUDINAL_FALSE_CALLS"] = len(long_fc)
    m["coverage_condition_counts"] = dict(cond_counts)
    m["longitudinal_coverage_counts"] = dict(cov_counts)
    m["p262_baseline"] = dict(P262_BASELINE)
    m["longitudinal"] = {
        "baseline_candidates": len(long_b),
        "gated_candidates": len(long_g),
        "baseline_duplicates": sum(1 for c in long_b if c.get("deterministic_match_status") == "ALREADY_DETECTED"),
        "gated_duplicates": sum(1 for c in long_g if c.get("deterministic_match_status") == "ALREADY_DETECTED"),
        "baseline_true_recoveries": long_base,
        "gated_true_recoveries": long_gat,
        "retained_recoveries": long_gat,
        "lost_recoveries": max(0, long_base - long_gat),
        "precision": _rate(sum(1 for c in long_g if c.get("gt_supported")), len(long_g)),
        "unsupported_rate": _rate(sum(1 for c in long_g if c.get("gt_match_status") == "UNSUPPORTED"), len(long_g)),
        "ambiguous_rate": _rate(sum(1 for c in long_g if c.get("gt_match_status") == "AMBIGUOUS"), len(long_g)),
        "false_skips": len(long_fs),
        "false_calls": len(long_fc),
        "by_coverage": {
            k: int(cov_counts.get(k, 0))
            for k in (
                COVER_FULL,
                COVER_QTY,
                COVER_ROLE,
                COVER_DIA,
                COVER_MULTI,
                COVER_MISSING,
                COVER_LAYER,
                COVER_UNASSOC,
                COVER_NONE,
            )
        },
    }
    n_call = int(m.get("CALL_BEAMS") or 0)
    m["TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED"] = (
        round(100.0 * int(m.get("GATED_TRUE_RECOVERIES") or 0) / n_call, 4) if n_call else None
    )
    return m


def classify_gate(
    metrics: Dict[str, Any],
    *,
    firewall_ok: bool,
    leakage_ok: bool,
    fingerprints_ok: bool,
) -> Dict[str, str]:
    stir = int(metrics.get("STIRRUP_GATED_TRUE_RECOVERIES") or 0)
    stir_ok = stir == 18
    ret = metrics.get("RECOVERY_RETENTION_RATE")
    long_ret = metrics.get("LONGITUDINAL_RECOVERY_RETENTION")
    prec_g = metrics.get("GATED_PRECISION")
    uns_g = metrics.get("GATED_UNSUPPORTED_RATE")
    dup_g = metrics.get("DUPLICATE_RATE_GATED")
    red = metrics.get("CALL_REDUCTION")
    per100 = metrics.get("TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED")
    p262_per100 = float(P262_BASELINE["TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED"])
    p262_dup = float(P262_BASELINE["DUPLICATE_RATE_GATED"])

    ret_ok = ret is not None and ret >= 0.90
    long_ok = long_ret is not None and long_ret >= 0.75
    prec_ok = prec_g is not None and prec_g + 1e-9 >= 0.73913
    uns_ok = uns_g is not None and uns_g <= 0.062802 + 1e-9
    dup_ok = dup_g is not None and dup_g <= p262_dup + 1e-9
    red_ok = red is not None and red >= 0.46
    per100_ok = per100 is not None and per100 + 1e-9 >= p262_per100
    safety = firewall_ok and leakage_ok and fingerprints_ok

    ready = (
        safety
        and stir_ok
        and ret_ok
        and prec_ok
        and uns_ok
        and dup_ok
        and long_ok
    )
    if not safety or stir != 18 and stir < 18:
        if not safety:
            decision = "REFINE_LONGITUDINAL_GATE"
            strength = "UNSAFE"
        else:
            decision = "REFINE_LONGITUDINAL_GATE"
            strength = "STIRRUP_REGRESSION"
    elif ready:
        decision = "READY_FOR_ENGINEERING_RECOMPUTE_PILOT"
        strength = "STRONG"
    else:
        decision = "REFINE_LONGITUDINAL_GATE"
        strength = "PROMISING" if (ret or 0) >= 0.80 and stir_ok else "WEAK"
    return {
        "strength": strength,
        "decision": decision,
        "note": (
            "Gated-replay classification only. Not PRODUCTION_READY. "
            f"stirrup_ok={stir_ok} retention_ok={ret_ok} long_ret_ok={long_ok} "
            f"precision_ok={prec_ok} unsupported_ok={uns_ok} duplicate_ok={dup_ok} "
            f"call_reduction_ok={red_ok} per100_ok={per100_ok}"
        ),
    }


__all__ = ["classify_gate", "compute_metrics"]
