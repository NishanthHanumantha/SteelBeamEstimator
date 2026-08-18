"""P2.6.6 semantic metrics. Evaluation only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP264_selective_role_gap_gate.metrics import compute_metrics as p264_compute_metrics

from .config import (
    COVER_LAYER,
    SEM_AMBIGUOUS,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNSUPPORTED,
)
from .control_cases import DUPLICATE_CONTROLS, TRUE_RECOVERY_CONTROLS, separability_report


def _class_counts(records: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {
        SEM_DISTINCT: 0,
        SEM_DUPLICATE: 0,
        SEM_AMBIGUOUS: 0,
        SEM_UNSUPPORTED: 0,
    }
    for rec in records:
        decision = str((rec.get("semantic") or {}).get("decision") or "")
        if decision in out:
            out[decision] += 1
    return out


def compute_semantic_metrics(
    *,
    target_records: List[Dict[str, Any]],
    controls: List[Dict[str, Any]],
    observed_metrics: Dict[str, Any],
    hypothetical_metrics: Optional[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
    false_calls: List[Dict[str, Any]],
    replay_summary: Dict[str, Any],
) -> Dict[str, Any]:
    counts = _class_counts(target_records)
    n = len(target_records)
    by_ctrl = {(r.get("set_key"), r.get("beam_id")): r for r in controls}
    tr_rows = [by_ctrl.get(k) or {} for k in TRUE_RECOVERY_CONTROLS]
    dup_rows = [by_ctrl.get(k) or {} for k in DUPLICATE_CONTROLS]
    tr_in_targets = [r for r in tr_rows if r.get("is_role_coverage_gap")]
    dup_in_targets = [r for r in dup_rows if r.get("is_role_coverage_gap")]

    def _cls(r: Dict[str, Any]) -> str:
        return str(r.get("semantic_class") or "")

    tr_distinct = sum(1 for r in tr_in_targets if _cls(r) == SEM_DISTINCT)
    dup_duplicate = sum(1 for r in dup_in_targets if _cls(r) == SEM_DUPLICATE)
    false_distinct = sum(1 for r in dup_in_targets if _cls(r) == SEM_DISTINCT)
    false_duplicate = sum(1 for r in tr_in_targets if _cls(r) == SEM_DUPLICATE)
    predicted_dup = [r for r in (tr_in_targets + dup_in_targets) if _cls(r) == SEM_DUPLICATE]
    dup_precision = (dup_duplicate / len(predicted_dup)) if predicted_dup else None
    dup_recall = (dup_duplicate / len(dup_in_targets)) if dup_in_targets else None
    tr_recall = (tr_distinct / len(tr_in_targets)) if tr_in_targets else None
    labeled = [r for r in (tr_in_targets + dup_in_targets) if _cls(r) in (SEM_DISTINCT, SEM_DUPLICATE)]
    correct = sum(
        1
        for r in labeled
        if (r.get("family") == "TRUE_RECOVERY_CONTROL" and _cls(r) == SEM_DISTINCT)
        or (r.get("family") == "DUPLICATE_CONTROL" and _cls(r) == SEM_DUPLICATE)
    )
    semantic_precision = (correct / len(labeled)) if labeled else None
    amb_rate = counts[SEM_AMBIGUOUS] / n if n else 0.0
    uns_rate = counts[SEM_UNSUPPORTED] / n if n else 0.0

    obs_tr = int(observed_metrics.get("GATED_TRUE_RECOVERIES") or 0)
    hypo = hypothetical_metrics or {}
    hypo_tr = int(hypo.get("GATED_TRUE_RECOVERIES") or obs_tr)
    recovery_retention = (hypo_tr / obs_tr) if obs_tr else None
    recovery_loss = max(0, obs_tr - hypo_tr)

    m: Dict[str, Any] = {
        "label": (
            "P2.6.6 semantic shadow on ROLE_COVERAGE_GAP. "
            "Observed routing remains P2.6.4/P2.6.5. Not production behaviour."
        ),
        "TARGET_BEAMS": n,
        "ROLE_COVERAGE_GAP_BEAMS": sum(
            1 for r in target_records if r.get("longitudinal_coverage") == COVER_LAYER
        ),
        "VISION_REPLAYS": int(replay_summary.get("replay_count") or n),
        "LIVE_VISION_CALLS": int(replay_summary.get("live_calls") or 0),
        "CACHE_HIT_RATE": replay_summary.get("cache_hit_rate"),
        "ESTIMATED_LIVE_CALLS_IF_DEPLOYED": n,
        "DISTINCT_REINFORCEMENT": counts[SEM_DISTINCT],
        "DUPLICATE_OR_REPEAT": counts[SEM_DUPLICATE],
        "AMBIGUOUS": counts[SEM_AMBIGUOUS],
        "UNSUPPORTED": counts[SEM_UNSUPPORTED],
        "true_recovery_recall": tr_recall,
        "duplicate_precision": dup_precision,
        "duplicate_recall": dup_recall,
        "semantic_precision": semantic_precision,
        "semantic_ambiguous_rate": amb_rate,
        "semantic_unsupported_rate": uns_rate,
        "false_DISTINCT": false_distinct,
        "false_DUPLICATE": false_duplicate,
        "FALSE_SKIPS": len(false_skips),
        "FALSE_CALLS": len(false_calls),
        "recovery_retention": recovery_retention,
        "recovery_loss": recovery_loss,
        "observed_p264": {
            "CALL_BEAMS": observed_metrics.get("CALL_BEAMS"),
            "SKIP_BEAMS": observed_metrics.get("SKIP_BEAMS"),
            "GATED_TRUE_RECOVERIES": observed_metrics.get("GATED_TRUE_RECOVERIES"),
            "FALSE_SKIPS": observed_metrics.get("FALSE_SKIPS"),
            "FALSE_CALLS": observed_metrics.get("FALSE_CALLS"),
        },
        "hypothetical": {
            "CALL_BEAMS": hypo.get("CALL_BEAMS"),
            "SKIP_BEAMS": hypo.get("SKIP_BEAMS"),
            "GATED_TRUE_RECOVERIES": hypo.get("GATED_TRUE_RECOVERIES"),
            "FALSE_SKIPS": hypo.get("FALSE_SKIPS"),
            "FALSE_CALLS": hypo.get("FALSE_CALLS"),
        },
        "separability": separability_report(controls),
        "p264_compute": observed_metrics,
    }
    return m


def _as_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def classify_gate(
    metrics: Dict[str, Any],
    *,
    firewall_ok: bool,
    leakage_ok: bool,
    fingerprints_ok: bool,
) -> Dict[str, str]:
    sep = (metrics.get("separability") or {}).get("semantic_distinguishes_b128_from_b141_b23")
    fs = _as_int(metrics.get("FALSE_SKIPS"), 99)
    false_dup = _as_int(metrics.get("false_DUPLICATE"), 99)
    live = _as_int(metrics.get("LIVE_VISION_CALLS"), 99)
    safety = firewall_ok and leakage_ok and fingerprints_ok and live == 0
    retention = metrics.get("recovery_retention")
    ret_ok = retention is None or retention >= 0.99
    hypo = metrics.get("hypothetical") or {}
    obs = metrics.get("observed_p264") or {}
    extra_skip = _as_int(hypo.get("SKIP_BEAMS"), 0) - _as_int(obs.get("SKIP_BEAMS"), 0)
    hypo_fs = _as_int(hypo.get("FALSE_SKIPS"), 99)
    obs_fs = _as_int(obs.get("FALSE_SKIPS"), 99)
    skip_safe = extra_skip > 0 and hypo_fs <= obs_fs and hypo_fs <= 1
    if not safety:
        decision = "REFINE_LONGITUDINAL_GATE"
        strength = "UNSAFE"
    elif bool(sep) and fs <= 1 and false_dup == 0 and ret_ok and skip_safe:
        decision = "READY_FOR_ENGINEERING_RECOMPUTE_PILOT"
        strength = "PROMISING_SEMANTIC_SPLIT"
    elif bool(sep) and false_dup == 0:
        decision = "REFINE_LONGITUDINAL_GATE"
        strength = "SEMANTIC_SPLIT_SKIP_NOT_JUSTIFIED"
    else:
        decision = "REFINE_LONGITUDINAL_GATE"
        strength = "PROMISING" if sep else "INSUFFICIENT_SEPARATION"
    return {
        "strength": strength,
        "decision": decision,
        "note": (
            "Observed routing is P2.6.4/P2.6.5. Hypothetical overlay is not production. "
            f"separability={sep} false_skips={fs} false_DUPLICATE={false_dup} "
            f"retention={retention} live={live} extra_skip={extra_skip} skip_safe={skip_safe}"
        ),
    }


def observed_vs_hypothetical_decisions(
    *,
    p265_decisions: List[Dict[str, Any]],
    target_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    overlay = {(r.get("set_key"), r.get("beam_id")): r for r in target_records}
    out = []
    for d in p265_decisions:
        row = dict(d)
        rec = overlay.get((d.get("set_key"), d.get("beam_id")))
        if rec:
            hypo = rec.get("hypothetical") or {}
            row["decision"] = hypo.get("hypothetical_vision_routing") or d.get("decision")
            row["hypothetical_decision"] = row["decision"]
            row["hypothetical_reason"] = hypo.get("hypothetical_reason")
        else:
            row["hypothetical_decision"] = d.get("decision")
            row["hypothetical_reason"] = "NOT_IN_SEMANTIC_TARGET"
        out.append(row)
    return out


__all__ = [
    "classify_gate",
    "compute_semantic_metrics",
    "observed_vs_hypothetical_decisions",
    "p264_compute_metrics",
]
