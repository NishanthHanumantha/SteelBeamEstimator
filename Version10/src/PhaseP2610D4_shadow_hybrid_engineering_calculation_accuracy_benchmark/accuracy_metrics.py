"""Accuracy metrics. QA.2A / P258 formulas implemented locally (not opaque)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import STATUS_AMBIGUOUS, STATUS_COMPLETE, STATUS_INCOMPATIBLE, STATUS_NO_TRUTH, STATUS_PARTIAL
from .engineering_adapter import FORMULA_SOURCE, FORMULA_WEIGHT

# Authoritative project formula: QA.2A metric8 / PhaseP258 metrics module.
# Local names avoid production-gate token leakage in this shadow reporter.


def weight_error_percent(pred: Optional[float], bench: Optional[float]) -> Optional[float]:
    if pred is None or bench is None:
        return None
    if abs(float(bench)) < 1e-12:
        return 100.0 if abs(float(pred)) > 1e-12 else 0.0
    return round(abs(float(pred) - float(bench)) / abs(float(bench)) * 100.0, 2)


def weight_accuracy_percent(pred: Optional[float], bench: Optional[float]) -> Optional[float]:
    err = weight_error_percent(pred, bench)
    if err is None:
        return None
    return round(max(0.0, 100.0 - float(err)), 2)


def signed_percent_error(pred: Optional[float], bench: Optional[float]) -> Optional[float]:
    if pred is None or bench is None:
        return None
    if abs(float(bench)) < 1e-12:
        return 0.0 if abs(float(pred)) < 1e-12 else None
    return round((float(pred) - float(bench)) / abs(float(bench)) * 100.0, 2)


def _round(v: Optional[float], n: int = 4) -> Optional[float]:
    if v is None:
        return None
    return round(float(v), n)


def beam_comparison(
    *,
    hybrid: Dict[str, Any],
    baseline: Optional[Dict[str, Any]],
    truth: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    h_kg = hybrid.get("hybrid_weight_kg")
    d_kg = (baseline or {}).get("total_weight_kg") if baseline else None
    t_kg = (truth or {}).get("total_weight_kg") if truth else None
    has_truth = t_kg is not None and float(t_kg) > 0
    h_err = weight_error_percent(h_kg, t_kg) if has_truth else None
    d_err = weight_error_percent(d_kg, t_kg) if has_truth else None
    h_acc = weight_accuracy_percent(h_kg, t_kg) if has_truth else None
    d_acc = weight_accuracy_percent(d_kg, t_kg) if has_truth else None
    winner = None
    if has_truth and h_err is not None and d_err is not None:
        if h_err < d_err:
            winner = "HYBRID"
        elif d_err < h_err:
            winner = "DETERMINISTIC"
        else:
            winner = "TIE"
    elif not has_truth:
        winner = STATUS_NO_TRUTH
    return {
        "beam_id": hybrid.get("beam_id"),
        "status": hybrid.get("status"),
        "completeness": hybrid.get("completeness"),
        "hybrid_kg": _round(h_kg),
        "deterministic_kg": _round(d_kg),
        "benchmark_kg": _round(t_kg) if has_truth else None,
        "truth_source": (truth or {}).get("source") if has_truth else STATUS_NO_TRUTH,
        "hybrid_error_pct": h_err,
        "deterministic_error_pct": d_err,
        "hybrid_accuracy_pct": h_acc,
        "deterministic_accuracy_pct": d_acc,
        "hybrid_signed_percent_error": signed_percent_error(h_kg, t_kg) if has_truth else None,
        "deterministic_signed_percent_error": signed_percent_error(d_kg, t_kg) if has_truth else None,
        "absolute_error_hybrid_kg": round(abs(float(h_kg) - float(t_kg)), 4) if has_truth and h_kg is not None else None,
        "absolute_error_deterministic_kg": round(abs(float(d_kg) - float(t_kg)), 4) if has_truth and d_kg is not None else None,
        "winner": winner,
        "truth_lines": list((truth or {}).get("lines") or []) if has_truth else [],
        "deterministic_group_count": (baseline or {}).get("group_count"),
        "weight_by_diameter": {
            "hybrid": hybrid.get("weight_by_diameter") or {},
            "deterministic": (baseline or {}).get("weight_by_diameter") or {},
            "benchmark": (truth or {}).get("weight_by_diameter") or {},
        },
        "formulas": {
            "weight": FORMULA_WEIGHT,
            "weight_source": FORMULA_SOURCE,
            "weight_error_percent": "abs(predicted - benchmark) / benchmark * 100  [QA.2A metric8 / PhaseP258 metrics]",
            "weight_accuracy_percent": "max(0, 100 - weight_error_percent)  [QA.2A metric8 / PhaseP258 metrics]",
        },
    }


def population_metrics(comparisons: List[Dict[str, Any]], hybrids: List[Dict[str, Any]]) -> Dict[str, Any]:
    with_truth = [c for c in comparisons if c.get("benchmark_kg") not in (None, 0)]
    h_tot = sum(float(c.get("hybrid_kg") or 0) for c in with_truth)
    d_tot = sum(float(c.get("deterministic_kg") or 0) for c in with_truth)
    t_tot = sum(float(c.get("benchmark_kg") or 0) for c in with_truth)
    h_err = weight_error_percent(h_tot, t_tot) if with_truth else None
    d_err = weight_error_percent(d_tot, t_tot) if with_truth else None
    h_acc = weight_accuracy_percent(h_tot, t_tot) if with_truth else None
    d_acc = weight_accuracy_percent(d_tot, t_tot) if with_truth else None
    delta = round(h_acc - d_acc, 2) if h_acc is not None and d_acc is not None else None
    statuses = {STATUS_COMPLETE: 0, STATUS_PARTIAL: 0, STATUS_AMBIGUOUS: 0, STATUS_INCOMPATIBLE: 0}
    for h in hybrids:
        st = h.get("status")
        if st in statuses:
            statuses[st] += 1
    no_truth = sum(1 for c in comparisons if c.get("winner") == STATUS_NO_TRUTH)
    winners = {"HYBRID": 0, "DETERMINISTIC": 0, "TIE": 0, STATUS_NO_TRUTH: 0}
    for c in comparisons:
        w = c.get("winner")
        if w in winners:
            winners[w] += 1
    return {
        "population_discovered": len(hybrids),
        "calculation_completeness": statuses,
        "no_benchmark_truth": no_truth,
        "benchmark_truth_coverage": len(with_truth),
        "hybrid_total_kg": round(h_tot, 4),
        "deterministic_total_kg": round(d_tot, 4),
        "benchmark_total_kg": round(t_tot, 4),
        "hybrid_absolute_error_kg": round(abs(h_tot - t_tot), 4) if with_truth else None,
        "deterministic_absolute_error_kg": round(abs(d_tot - t_tot), 4) if with_truth else None,
        "hybrid_error_pct": h_err,
        "deterministic_error_pct": d_err,
        "hybrid_accuracy_pct": h_acc,
        "deterministic_accuracy_pct": d_acc,
        "accuracy_improvement_delta_pp": delta,
        "winners": winners,
        "totals_include_only_beams_with_benchmark_truth": True,
        "group_semantic_impact": group_semantic_impact(comparisons, hybrids),
        "bar_count_accuracy": bar_count_accuracy(comparisons, hybrids),
        "formulas": {
            "weight_error_percent": "abs(predicted - benchmark) / benchmark * 100",
            "weight_accuracy_percent": "max(0, 100 - weight_error_percent)",
            "accuracy_improvement_delta_pp": "hybrid_accuracy_pct - deterministic_accuracy_pct",
            "source": "QA.2A metric8 / PhaseP258 metrics (local implementation in this shadow reporter)",
        },
    }


def diameter_report(comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
    keys = set()
    for c in comparisons:
        wbd = c.get("weight_by_diameter") or {}
        for src in ("hybrid", "deterministic", "benchmark"):
            keys.update((wbd.get(src) or {}).keys())
    rows = []
    for key in sorted(keys, key=lambda x: int("".join(ch for ch in str(x) if ch.isdigit()) or 0)):
        h = sum(float(((c.get("weight_by_diameter") or {}).get("hybrid") or {}).get(key) or 0) for c in comparisons if c.get("benchmark_kg"))
        d = sum(float(((c.get("weight_by_diameter") or {}).get("deterministic") or {}).get(key) or 0) for c in comparisons if c.get("benchmark_kg"))
        t = sum(float(((c.get("weight_by_diameter") or {}).get("benchmark") or {}).get(key) or 0) for c in comparisons if c.get("benchmark_kg"))
        rows.append(
            {
                "diameter": key,
                "hybrid_predicted_kg": round(h, 4),
                "deterministic_predicted_kg": round(d, 4),
                "benchmark_kg": round(t, 4),
                "hybrid_error_pct": weight_error_percent(h, t) if t > 0 else None,
                "deterministic_error_pct": weight_error_percent(d, t) if t > 0 else None,
            }
        )
    for row in rows:
        row["hybrid_accuracy_pct"] = weight_accuracy_percent(row["hybrid_predicted_kg"], row["benchmark_kg"]) if row["benchmark_kg"] > 0 else None
        row["deterministic_accuracy_pct"] = weight_accuracy_percent(row["deterministic_predicted_kg"], row["benchmark_kg"]) if row["benchmark_kg"] > 0 else None
    h_exact = d_exact = beams = 0
    h_recall_sum = d_recall_sum = 0.0
    for c in comparisons:
        if not c.get("benchmark_kg"):
            continue
        wbd = c.get("weight_by_diameter") or {}
        t_keys = {k for k, v in (wbd.get("benchmark") or {}).items() if float(v or 0) > 0}
        if not t_keys:
            continue
        beams += 1
        h_keys = {k for k, v in (wbd.get("hybrid") or {}).items() if float(v or 0) > 0}
        d_keys = {k for k, v in (wbd.get("deterministic") or {}).items() if float(v or 0) > 0}
        if h_keys == t_keys:
            h_exact += 1
        if d_keys == t_keys:
            d_exact += 1
        h_recall_sum += len(h_keys & t_keys) / len(t_keys)
        d_recall_sum += len(d_keys & t_keys) / len(t_keys)
    return {
        "rows": rows,
        "diameter_set_accuracy": {
            "beams_with_benchmark_truth": beams,
            "hybrid_exact_set_matches": h_exact,
            "deterministic_exact_set_matches": d_exact,
            "hybrid_mean_diameter_recall": round(h_recall_sum / beams, 4) if beams else None,
            "deterministic_mean_diameter_recall": round(d_recall_sum / beams, 4) if beams else None,
        },
        "note": "Population diameter totals for beams with benchmark truth only.",
    }


def _longitudinal_hybrid_groups(hybrid: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for g in hybrid.get("groups") or []:
        if not isinstance(g, dict):
            continue
        if g.get("ambiguous"):
            continue
        role = str(g.get("role") or "").upper()
        layer = str(g.get("layer") or "").upper()
        if "STIRRUP" in role or "SPACER" in role or "STIRRUP" in layer or "SPACER" in layer:
            continue
        rows.append(g)
    return rows


def _truth_longitudinal_lines(comparison: Dict[str, Any]) -> List[Dict[str, Any]]:
    lines = list((comparison.get("truth_lines") or []))
    out = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        role = str(line.get("role") or "").upper()
        if any(tok in role for tok in ("STIRRUP", "LINK", "SPACER", "CHAIR")):
            continue
        out.append(line)
    return out


def group_semantic_impact(comparisons: List[Dict[str, Any]], hybrids: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {str(h.get("beam_id")): h for h in hybrids}
    hybrid_n = 0
    truth_n = 0
    det_n = 0
    missing = 0
    spurious = 0
    beams = 0
    for c in comparisons:
        if c.get("benchmark_kg") in (None, 0):
            continue
        beams += 1
        h = by_id.get(str(c.get("beam_id"))) or {}
        hg = _longitudinal_hybrid_groups(h)
        tl = _truth_longitudinal_lines(c)
        det_groups = int((c.get("deterministic_group_count") or 0) or 0)
        hn, tn = len(hg), len(tl)
        hybrid_n += hn
        truth_n += tn
        det_n += det_groups
        missing += max(0, tn - hn)
        spurious += max(0, hn - tn)
    return {
        "beams_with_benchmark_truth": beams,
        "expected_group_count": truth_n,
        "hybrid_group_count": hybrid_n,
        "deterministic_group_count": det_n if det_n else None,
        "missing_groups": missing,
        "spurious_groups": spurious,
        "note": "Group counts compare hybrid longitudinal groups to estimator RoleLines. Schemas differ; this is a count delta, not identity matching.",
    }


def bar_count_accuracy(comparisons: List[Dict[str, Any]], hybrids: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {str(h.get("beam_id")): h for h in hybrids}
    exact = over = under = 0
    errors: List[float] = []
    for c in comparisons:
        if c.get("benchmark_kg") in (None, 0):
            continue
        h = by_id.get(str(c.get("beam_id"))) or {}
        h_sum = 0
        for g in _longitudinal_hybrid_groups(h):
            try:
                h_sum += int(g.get("bar_count") or 0)
            except (TypeError, ValueError):
                continue
        t_sum = 0
        for line in _truth_longitudinal_lines(c):
            try:
                t_sum += int(line.get("bar_count") or 0)
            except (TypeError, ValueError):
                continue
        if t_sum <= 0:
            continue
        delta = h_sum - t_sum
        errors.append(abs(delta))
        if delta == 0:
            exact += 1
        elif delta > 0:
            over += 1
        else:
            under += 1
    mae = round(sum(errors) / len(errors), 3) if errors else None
    return {
        "beams_compared": len(errors),
        "exact_matches": exact,
        "overestimates": over,
        "underestimates": under,
        "mean_absolute_count_error": mae,
        "note": "Beam-level sum of longitudinal bar counts versus estimator RoleLine bar counts.",
    }


__all__ = [
    "bar_count_accuracy",
    "beam_comparison",
    "diameter_report",
    "group_semantic_impact",
    "population_metrics",
    "signed_percent_error",
    "weight_accuracy_percent",
    "weight_error_percent",
]
