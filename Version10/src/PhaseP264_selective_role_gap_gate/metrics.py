"""P2.6.4 gated-replay metrics. Not a new Vision benchmark."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP263_longitudinal_aware_gate.metrics import compute_metrics as p263_compute_metrics

from .config import (
    COVER_LAYER,
    DECISION_CALL,
    DECISION_SKIP,
    P262_BASELINE,
    P263_BASELINE,
    ROLE_GAP_EXPLAINED,
    ROLE_GAP_REQUIRED,
)


def compute_metrics(
    *,
    decisions: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
    false_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    m = p263_compute_metrics(
        decisions=decisions,
        baseline_candidates=baseline_candidates,
        gated_candidates=gated_candidates,
        false_skips=false_skips,
        false_calls=false_calls,
    )
    m["label"] = (
        "Gated replay using frozen P2.6.1 Vision responses. "
        "P2.6.4 selective role-gap gate. Not a new Vision benchmark."
    )
    gap = [d for d in decisions if d.get("longitudinal_coverage") == COVER_LAYER]
    gap_call = [d for d in gap if d.get("decision") == DECISION_CALL]
    gap_skip = [d for d in gap if d.get("decision") == DECISION_SKIP]
    explained = [d for d in gap if d.get("role_gap_status") == ROLE_GAP_EXPLAINED]
    required = [d for d in gap if d.get("role_gap_status") == ROLE_GAP_REQUIRED]
    m["p263_baseline"] = dict(P263_BASELINE)
    m["p262_baseline"] = dict(P262_BASELINE)
    m["ROLE_COVERAGE_GAP_BEAMS"] = len(gap)
    m["ROLE_COVERAGE_GAP_CALLS"] = len(gap_call)
    m["ROLE_COVERAGE_GAP_SKIPS"] = len(gap_skip)
    m["ROLE_GAP_EXPLAINED_BEAMS"] = len(explained)
    m["ROLE_GAP_REQUIRED_BEAMS"] = len(required)
    m["ROLE_COVERAGE_GAP_CALLS_P263"] = int(P263_BASELINE["ROLE_COVERAGE_GAP_BEAMS"])
    long_m = m.get("longitudinal") or {}
    long_m["role_coverage_gap_calls"] = len(gap_call)
    long_m["role_coverage_gap_skips"] = len(gap_skip)
    long_m["role_gap_explained"] = len(explained)
    m["longitudinal"] = long_m
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
    p263_per100 = float(P263_BASELINE["TRUE_RECOVERIES_PER_100_VISION_CALLS_GATED"])
    p263_dup = float(P263_BASELINE["DUPLICATE_RATE_GATED"])
    p263_prec = float(P263_BASELINE["GATED_PRECISION"])
    p263_uns = float(P263_BASELINE["GATED_UNSUPPORTED_RATE"])

    ret_ok = ret is not None and ret >= 0.90
    long_ok = long_ret is not None and long_ret >= 0.75
    prec_ok = prec_g is not None and prec_g + 1e-9 >= 0.73913
    uns_ok = uns_g is not None and uns_g <= 0.062802 + 1e-9
    prec_vs_p263 = prec_g is not None and prec_g + 1e-9 >= p263_prec
    uns_vs_p263 = uns_g is not None and uns_g <= p263_uns + 1e-9
    dup_ok = dup_g is not None and dup_g <= p263_dup + 1e-9
    red_ok = red is not None and red >= 0.46
    per100_ok = per100 is not None and per100 + 1e-9 >= p263_per100
    safety = firewall_ok and leakage_ok and fingerprints_ok
    lost = int(metrics.get("RECOVERIES_LOST") or 0)
    lost_ok = lost <= 1

    ready = (
        safety
        and stir_ok
        and ret_ok
        and prec_ok
        and uns_ok
        and dup_ok
        and long_ok
        and lost_ok
    )
    if not safety or stir < 18:
        decision = "REFINE_LONGITUDINAL_GATE"
        strength = "UNSAFE" if not safety else "STIRRUP_REGRESSION"
    elif ready:
        decision = "READY_FOR_ENGINEERING_RECOMPUTE_PILOT"
        strength = "STRONG"
    else:
        decision = "REFINE_LONGITUDINAL_GATE"
        improved = (prec_vs_p263 or uns_vs_p263 or per100_ok) and stir_ok and (ret or 0) >= 0.90
        strength = "PROMISING" if improved else "WEAK"
    return {
        "strength": strength,
        "decision": decision,
        "note": (
            "Gated-replay classification only. Not PRODUCTION_READY. "
            f"stirrup_ok={stir_ok} retention_ok={ret_ok} long_ret_ok={long_ok} "
            f"precision_ok={prec_ok} unsupported_ok={uns_ok} duplicate_ok={dup_ok} "
            f"call_reduction_ok={red_ok} per100_ok={per100_ok} "
            f"prec_vs_p263={prec_vs_p263} uns_vs_p263={uns_vs_p263}"
        ),
    }


__all__ = ["classify_gate", "compute_metrics"]
