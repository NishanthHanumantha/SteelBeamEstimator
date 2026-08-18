"""Offline evaluation against P2.6.6 reference classes. Never sent to Claude."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP266_semantic_longitudinal_resolver.control_cases import (
    DUPLICATE_CONTROLS,
    FALSE_SKIP_CONTROLS,
    SEPARABILITY_TRIPLE,
    TRUE_RECOVERY_CONTROLS,
)

from .config import (
    COVER_FULL,
    DECISION_SKIP,
    SEM_AMBIGUOUS,
    SEM_DISTINCT,
    SEM_DUPLICATE,
    SEM_UNSUPPORTED,
)
from .repeatability import compute_repeatability, critical_repeatability


def _primary_decision(rec: Dict[str, Any]) -> Optional[str]:
    obs = rec.get("primary") or {}
    if not obs.get("ok"):
        return None
    return (obs.get("payload") or {}).get("decision")


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def evaluate_accuracy(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = {(r.get("set_key"), r.get("beam_id")): r for r in records}

    def _rows(keys: Tuple[Tuple[str, str], ...]) -> List[Dict[str, Any]]:
        return [by[k] for k in keys if k in by]

    tr_rows = _rows(TRUE_RECOVERY_CONTROLS)
    dup_rows = _rows(DUPLICATE_CONTROLS)

    def _cls(rec: Dict[str, Any]) -> Optional[str]:
        return _primary_decision(rec)

    tr_distinct = sum(1 for r in tr_rows if _cls(r) == SEM_DISTINCT)
    tr_dup = sum(1 for r in tr_rows if _cls(r) == SEM_DUPLICATE)
    dup_dup = sum(1 for r in dup_rows if _cls(r) == SEM_DUPLICATE)
    dup_distinct = sum(1 for r in dup_rows if _cls(r) == SEM_DISTINCT)
    pred_distinct = [r for r in (tr_rows + dup_rows) if _cls(r) == SEM_DISTINCT]
    pred_dup = [r for r in (tr_rows + dup_rows) if _cls(r) == SEM_DUPLICATE]
    distinct_precision = (tr_distinct / len(pred_distinct)) if pred_distinct else None
    distinct_recall = (tr_distinct / len(tr_rows)) if tr_rows else None
    duplicate_precision = (dup_dup / len(pred_dup)) if pred_dup else None
    duplicate_recall = (dup_dup / len(dup_rows)) if dup_rows else None
    labeled = [r for r in (tr_rows + dup_rows) if _cls(r) in (SEM_DISTINCT, SEM_DUPLICATE)]
    correct = sum(
        1
        for r in labeled
        if (r.get("family") == "TRUE_RECOVERY_CONTROL" and _cls(r) == SEM_DISTINCT)
        or (r.get("family") == "DUPLICATE_CONTROL" and _cls(r) == SEM_DUPLICATE)
    )
    # family may be missing on live records; use key membership
    tr_keys = set(TRUE_RECOVERY_CONTROLS)
    dup_keys = set(DUPLICATE_CONTROLS)
    correct = 0
    for r in labeled:
        key = (r.get("set_key"), r.get("beam_id"))
        d = _cls(r)
        if key in tr_keys and d == SEM_DISTINCT:
            correct += 1
        elif key in dup_keys and d == SEM_DUPLICATE:
            correct += 1
    semantic_precision = (correct / len(labeled)) if labeled else None

    n = len(records)
    counts = {SEM_DISTINCT: 0, SEM_DUPLICATE: 0, SEM_AMBIGUOUS: 0, SEM_UNSUPPORTED: 0}
    valid = 0
    for r in records:
        d = _cls(r)
        if d is None:
            continue
        valid += 1
        if d in counts:
            counts[d] += 1
    recovery_retention = 1.0 if tr_dup == 0 else max(0.0, 1.0 - (tr_dup / max(len(tr_rows), 1)))
    return {
        "true_recovery_recall": (tr_distinct / len(tr_rows)) if tr_rows else None,
        "distinct_precision": distinct_precision,
        "distinct_recall": distinct_recall,
        "duplicate_precision": duplicate_precision,
        "duplicate_recall": duplicate_recall,
        "semantic_precision": semantic_precision,
        "false_DISTINCT": dup_distinct,
        "false_DUPLICATE": tr_dup,
        "ambiguous_rate": (counts[SEM_AMBIGUOUS] / n) if n else 0.0,
        "unsupported_rate": (counts[SEM_UNSUPPORTED] / n) if n else 0.0,
        "recovery_retention": recovery_retention,
        "valid_primary": valid,
        "DISTINCT": counts[SEM_DISTINCT],
        "DUPLICATE": counts[SEM_DUPLICATE],
        "AMBIGUOUS": counts[SEM_AMBIGUOUS],
        "UNSUPPORTED": counts[SEM_UNSUPPORTED],
        "true_recovery_n": len(tr_rows),
        "duplicate_control_n": len(dup_rows),
        "true_recovery_classified_duplicate": tr_dup,
    }


def evaluate_critical(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    by = {(r.get("set_key"), r.get("beam_id")): r for r in records}
    out = {}
    for set_key, beam_id in SEPARABILITY_TRIPLE:
        rec = by.get((set_key, beam_id)) or {}
        prim = _primary_decision(rec)
        rep = None
        rpt = rec.get("repeat") or {}
        if rpt.get("ok"):
            rep = (rpt.get("payload") or {}).get("decision")
        out[f"{set_key}/{beam_id}"] = {
            "primary": prim,
            "repeat": rep,
            "p266_reference": rec.get("p266_reference"),
            "p265_context": rec.get("p265_context_status"),
            "observed_decision": rec.get("observed_decision"),
        }
    b128 = (out.get("Fifth/B128") or {}).get("primary")
    b141 = (out.get("Fourth/B141") or {}).get("primary")
    b23 = (out.get("Fourth/B23") or {}).get("primary")
    strong_split = b128 == SEM_DISTINCT and b141 in (SEM_DUPLICATE, SEM_AMBIGUOUS) and b23 in (
        SEM_DUPLICATE,
        SEM_AMBIGUOUS,
    )
    dangerous = b128 == SEM_DUPLICATE
    return {
        "cases": out,
        "strong_split": strong_split,
        "b128_duplicate_failure": dangerous,
    }


def classify_phase(
    *,
    accuracy: Dict[str, Any],
    repeat: Dict[str, Any],
    critical: Dict[str, Any],
    live_ok: bool,
    fingerprints_ok: bool,
    production_mutation: int,
    successful_primary: int,
    successful_repeat: int,
) -> Dict[str, str]:
    if (not live_ok) or production_mutation or (not fingerprints_ok) or successful_primary == 0:
        return {
            "decision": "LIVE_BENCHMARK_FAILED",
            "strength": "FAILED",
            "note": "Live benchmark did not execute safely or produced no valid primary results.",
        }
    false_dup = _as_int(accuracy.get("false_DUPLICATE"), 99)
    false_dist = _as_int(accuracy.get("false_DISTINCT"), 99)
    rep_rate = accuracy.get("true_recovery_recall")
    repeat_rate = repeat.get("semantic_repeatability_rate")
    dangerous_flip = int(repeat.get("DISTINCT_to_DUPLICATE") or 0) + int(repeat.get("DUPLICATE_to_DISTINCT") or 0)
    strong = (
        bool(critical.get("strong_split"))
        and not bool(critical.get("b128_duplicate_failure"))
        and false_dup == 0
        and false_dist <= 1
        and (rep_rate is None or rep_rate >= 0.99)
        and (repeat_rate is not None and repeat_rate >= 0.80)
        and dangerous_flip == 0
        and successful_primary >= 20
        and successful_repeat >= 20
    )
    if strong:
        return {
            "decision": "LIVE_SEMANTIC_VALIDATED",
            "strength": "STRONG",
            "note": "Live Claude reproduced the P2.6.6 split with recovery protection and repeatability. NOT production routing.",
        }
    if critical.get("b128_duplicate_failure") or false_dup > 0:
        return {
            "decision": "LIVE_BENCHMARK_FAILED",
            "strength": "UNSAFE_TRUE_RECOVERY",
            "note": "True-recovery protection failed under live Vision (DUPLICATE on a recovery control).",
        }
    if critical.get("strong_split"):
        return {
            "decision": "REFINE_SEMANTIC_ARBITRATION",
            "strength": "PARTIAL",
            "note": "Semantic split appeared on primary, but repeatability or residual errors block routing use.",
        }
    return {
        "decision": "REFINE_SEMANTIC_ARBITRATION",
        "strength": "INSUFFICIENT",
        "note": "Live Claude did not reliably reproduce the P2.6.6 DISTINCT vs DUPLICATE split.",
    }


def attach_eval_fields(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tr = set(TRUE_RECOVERY_CONTROLS)
    dup = set(DUPLICATE_CONTROLS)
    fs = set(FALSE_SKIP_CONTROLS)
    out = []
    for rec in records:
        row = dict(rec)
        key = (rec.get("set_key"), rec.get("beam_id"))
        if key in tr:
            row["family"] = "TRUE_RECOVERY_CONTROL"
            row["criticality"] = "HIGH"
        elif key in dup:
            row["family"] = "DUPLICATE_CONTROL"
            row["criticality"] = "HIGH" if key in set(SEPARABILITY_TRIPLE) else "MEDIUM"
        elif key in fs:
            row["family"] = "FALSE_SKIP_CONTROL"
            row["criticality"] = "DIAGNOSTIC"
        else:
            row["family"] = (
                "FULLY_COVERED_DIAGNOSTIC"
                if rec.get("longitudinal_coverage") == COVER_FULL
                else "ROLE_COVERAGE_GAP"
            )
            row["criticality"] = "DIAGNOSTIC" if rec.get("longitudinal_coverage") == COVER_FULL else "MEDIUM"
        out.append(row)
    return out


def fully_covered_untouched(records: List[Dict[str, Any]]) -> bool:
    for rec in records:
        if rec.get("longitudinal_coverage") != COVER_FULL:
            continue
        if rec.get("observed_decision") != DECISION_SKIP:
            return False
        if rec.get("production_routing_changed"):
            return False
    return True


__all__ = [
    "DUPLICATE_CONTROLS",
    "FALSE_SKIP_CONTROLS",
    "SEPARABILITY_TRIPLE",
    "TRUE_RECOVERY_CONTROLS",
    "attach_eval_fields",
    "classify_phase",
    "compute_repeatability",
    "critical_repeatability",
    "evaluate_accuracy",
    "evaluate_critical",
    "fully_covered_untouched",
]
