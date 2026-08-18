"""P2.6.5 observed vs hypothetical metrics. Evaluation only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP264_selective_role_gap_gate.metrics import compute_metrics as p264_compute_metrics

from .config import (
    COVER_FULL,
    COVER_LAYER,
    DECISION_CALL,
    DECISION_SKIP,
    P261_BASELINE,
    P262_BASELINE,
    P263_BASELINE,
    P264_BASELINE,
    STATUS_AMBIGUOUS,
    STATUS_CALL,
    STATUS_INSUFFICIENT,
    STATUS_SKIP,
)


def _status_counts(decisions: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {
        STATUS_CALL: 0,
        STATUS_SKIP: 0,
        STATUS_AMBIGUOUS: 0,
        STATUS_INSUFFICIENT: 0,
    }
    for d in decisions:
        s = str(d.get("context_status") or "")
        if s in out:
            out[s] += 1
    return out


def compute_metrics(
    *,
    decisions: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
    false_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    m = p264_compute_metrics(
        decisions=decisions,
        baseline_candidates=baseline_candidates,
        gated_candidates=gated_candidates,
        false_skips=false_skips,
        false_calls=false_calls,
    )
    m["label"] = (
        "Observed P2.6.5 shadow uses frozen P2.6.4 routing. "
        "Not a new Vision benchmark. Not production behaviour."
    )
    m["p261_baseline"] = dict(P261_BASELINE)
    m["p262_baseline"] = dict(P262_BASELINE)
    m["p263_baseline"] = dict(P263_BASELINE)
    m["p264_baseline"] = dict(P264_BASELINE)
    gap = [d for d in decisions if d.get("longitudinal_coverage") == COVER_LAYER]
    full = [d for d in decisions if d.get("longitudinal_coverage") == COVER_FULL]
    m["ROLE_COVERAGE_GAP_BEAMS"] = len(gap)
    m["FULLY_COVERED_BEAMS"] = len(full)
    m["context_status_counts"] = _status_counts(decisions)
    m["role_gap_context_status_counts"] = _status_counts(gap)
    m["CONTEXT_SUPPORTS_SKIP"] = m["context_status_counts"].get(STATUS_SKIP, 0)
    m["CONTEXT_SUPPORTS_CALL"] = m["context_status_counts"].get(STATUS_CALL, 0)
    m["CONTEXT_AMBIGUOUS"] = m["context_status_counts"].get(STATUS_AMBIGUOUS, 0)
    m["CONTEXT_INSUFFICIENT"] = m["context_status_counts"].get(STATUS_INSUFFICIENT, 0)
    return m


def classify_gate(
    metrics: Dict[str, Any],
    *,
    firewall_ok: bool,
    leakage_ok: bool,
    fingerprints_ok: bool,
    hypothetical: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    stir = int(metrics.get("STIRRUP_GATED_TRUE_RECOVERIES") or 0)
    hypo = hypothetical or {}
    hypo_lost = int(hypo.get("RECOVERIES_LOST") or metrics.get("RECOVERIES_LOST") or 0)
    hypo_fs = int(hypo.get("FALSE_SKIPS") or 99)
    hypo_prec = hypo.get("GATED_PRECISION")
    hypo_uns = hypo.get("GATED_UNSUPPORTED_RATE")
    skip_n = int(metrics.get("CONTEXT_SUPPORTS_SKIP") or 0)
    call_n = int(metrics.get("CONTEXT_SUPPORTS_CALL") or 0)
    amb_n = int(metrics.get("CONTEXT_AMBIGUOUS") or 0)
    safety = firewall_ok and leakage_ok and fingerprints_ok
    stir_ok = stir == 18
    long_ret = metrics.get("LONGITUDINAL_RECOVERY_RETENTION")
    long_ok = long_ret is not None and long_ret >= 0.75
    ret = metrics.get("RECOVERY_RETENTION_RATE")
    ret_ok = ret is not None and ret >= 0.90
    separable = skip_n >= 3 and call_n >= 3 and hypo_lost <= 1 and hypo_fs <= 1
    prec_ok = hypo_prec is not None and hypo_prec + 1e-9 >= 0.73913
    uns_ok = hypo_uns is not None and hypo_uns <= 0.062802 + 1e-9
    ready = (
        safety
        and stir_ok
        and ret_ok
        and long_ok
        and separable
        and prec_ok
        and uns_ok
        and hypo_lost <= 1
        and hypo_fs <= 1
    )
    if not safety or not stir_ok:
        decision = "REFINE_LONGITUDINAL_GATE"
        strength = "UNSAFE" if not safety else "STIRRUP_REGRESSION"
    elif ready:
        decision = "READY_FOR_ENGINEERING_RECOMPUTE_PILOT"
        strength = "STRONG"
    else:
        decision = "REFINE_LONGITUDINAL_GATE"
        strength = "PROMISING" if skip_n or call_n else "INSUFFICIENT_EVIDENCE"
    return {
        "strength": strength,
        "decision": decision,
        "note": (
            "Observed routing is P2.6.4. Hypothetical overlay is not production. "
            f"stirrup_ok={stir_ok} retention_ok={ret_ok} long_ok={long_ok} "
            f"separable={separable} prec_ok={prec_ok} uns_ok={uns_ok} "
            f"context skip/call/amb={skip_n}/{call_n}/{amb_n} "
            f"hypo_lost={hypo_lost} hypo_false_skips={hypo_fs}"
        ),
    }


__all__ = ["classify_gate", "compute_metrics"]
