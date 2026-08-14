"""Offline P2.5.11 comparison. Workbook totals are evaluation-only."""
from __future__ import annotations

from typing import Any, Dict, List

from PhaseP258_controlled_vision_field_repair.metrics import error_reduction_pct
from PhaseP259_beam_safe_arbitration.comparison import strategy_row

from .config import (
    DEC_ALLOW,
    DEC_HOLD,
    DEC_REJECT,
    MODEL_VERSION,
    PHASE_ID,
    STRATEGY_P2510,
    STRATEGY_P2511,
    STRATEGY_UNKNOWN_ONLY,
)


def _ids(rows: List[Dict[str, Any]]) -> set:
    return {str(r.get("beam_id")) for r in rows}


def transition_matrix(p2510_decisions: List[Dict[str, Any]], p2511_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    a = {str(d.get("beam_id")): d.get("decision") for d in p2510_decisions}
    b = {str(d.get("beam_id")): d.get("decision") for d in p2511_decisions}
    ids = sorted(set(a) | set(b))
    counts = {
        "P2510_ALLOW_TO_P2511_ALLOW": [],
        "P2510_HOLD_TO_P2511_ALLOW": [],
        "P2510_HOLD_TO_P2511_HOLD": [],
        "P2510_ALLOW_TO_P2511_HOLD": [],
        "P2510_REJECT_TO_P2511_REJECT": [],
        "OTHER": [],
    }
    for bid in ids:
        left = a.get(bid)
        right = b.get(bid)
        if left == DEC_ALLOW and right == DEC_ALLOW:
            counts["P2510_ALLOW_TO_P2511_ALLOW"].append(bid)
        elif left == DEC_HOLD and right == DEC_ALLOW:
            counts["P2510_HOLD_TO_P2511_ALLOW"].append(bid)
        elif left == DEC_HOLD and right == DEC_HOLD:
            counts["P2510_HOLD_TO_P2511_HOLD"].append(bid)
        elif left == DEC_ALLOW and right == DEC_HOLD:
            counts["P2510_ALLOW_TO_P2511_HOLD"].append(bid)
        elif left == DEC_REJECT and right == DEC_REJECT:
            counts["P2510_REJECT_TO_P2511_REJECT"].append(bid)
        else:
            counts["OTHER"].append({"beam_id": bid, "p2510": left, "p2511": right})
    return {
        "counts": {k: len(v) if k != "OTHER" else len(v) for k, v in counts.items()},
        "beams": counts,
    }


def gate_counts(decisions: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {DEC_ALLOW: 0, DEC_HOLD: 0, DEC_REJECT: 0}
    for d in decisions:
        dec = d.get("decision")
        if dec in out:
            out[dec] += 1
    return out


def compare_strategies(
    *,
    baseline_bench: Dict[str, Any],
    unknown_result: Dict[str, Any],
    p2510_result: Dict[str, Any],
    p2511_result: Dict[str, Any],
    production_mutations: int,
    p2510_decisions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    unknown_row = strategy_row(
        strategy=STRATEGY_UNKNOWN_ONLY,
        baseline_bench=baseline_bench,
        shadow_bench=unknown_result.get("shadow_bench") or {},
        books=unknown_result.get("books") or {},
        candidates=unknown_result.get("candidates") or [],
        overlay=unknown_result.get("overlay") or [],
        production_mutations=production_mutations,
    )
    p2510_row = strategy_row(
        strategy=STRATEGY_P2510,
        baseline_bench=baseline_bench,
        shadow_bench=p2510_result.get("shadow_bench") or {},
        books=p2510_result.get("books") or {},
        candidates=p2510_result.get("allowed") or p2510_result.get("candidates") or [],
        overlay=p2510_result.get("overlay") or [],
        production_mutations=production_mutations,
    )
    p2511_row = strategy_row(
        strategy=STRATEGY_P2511,
        baseline_bench=baseline_bench,
        shadow_bench=p2511_result.get("shadow_bench") or {},
        books=p2511_result.get("books") or {},
        candidates=p2511_result.get("allowed") or [],
        overlay=p2511_result.get("overlay") or [],
        production_mutations=production_mutations,
    )
    p2511_decs = (p2511_result.get("gate") or {}).get("decisions") or []
    trans = transition_matrix(p2510_decisions, p2511_decs)
    u_imp = (unknown_row.get("beam_impact") or {}).get("unique_model_detected") or {}
    g_imp = (p2511_row.get("beam_impact") or {}).get("unique_model_detected") or {}
    t10 = (p2510_row.get("beam_impact") or {}).get("unique_model_detected") or {}
    u_improved = _ids(u_imp.get("improved") or [])
    u_worsened = _ids(u_imp.get("worsened") or [])
    g_improved = _ids(g_imp.get("improved") or [])
    g_worsened = _ids(g_imp.get("worsened") or [])
    t10_improved = _ids(t10.get("improved") or [])
    counts = gate_counts(p2511_decs)
    return {
        "model_version": MODEL_VERSION,
        "phase_id": PHASE_ID,
        "unknown_only": unknown_row,
        "p2510_gated": p2510_row,
        "p2511_enriched": p2511_row,
        "gate_counts": counts,
        "transition": trans,
        "worsenings_prevented": sorted(u_worsened - g_worsened),
        "worsenings_remaining": sorted(g_worsened),
        "improvements_retained_vs_unknown": sorted(u_improved & g_improved),
        "improvements_recovered_vs_p2510": sorted(g_improved - t10_improved),
        "holds_promoted": trans["beams"]["P2510_HOLD_TO_P2511_ALLOW"],
        "unique_model_detected": g_imp.get("beam_count"),
        "metrics": {
            "deterministic_steel": unknown_row.get("baseline_steel"),
            "p259_steel": unknown_row.get("vision_shadow_steel"),
            "p2510_steel": p2510_row.get("vision_shadow_steel"),
            "p2511_steel": p2511_row.get("vision_shadow_steel"),
            "estimator_steel": unknown_row.get("estimator_steel"),
            "deterministic_accuracy": unknown_row.get("baseline_accuracy"),
            "p259_accuracy": unknown_row.get("steel_accuracy"),
            "p2510_accuracy": p2510_row.get("steel_accuracy"),
            "p2511_accuracy": p2511_row.get("steel_accuracy"),
            "absolute_error_p2511": p2511_row.get("absolute_error"),
            "error_reduction_vs_det": error_reduction_pct(
                unknown_row.get("baseline_absolute_error"), p2511_row.get("absolute_error")
            ),
        },
    }


def recommend(comparison: Dict[str, Any], *, leakage_ok: bool, prod_mut: int, worsenings: int) -> Dict[str, Any]:
    if prod_mut or not leakage_ok:
        return {"class": "FAIL", "rationale": "Safety firewall failed."}
    if worsenings > 0:
        return {
            "class": "FAIL",
            "rationale": (
                f"{worsenings} unique-model worsenings were reintroduced. "
                "P2.5.11 must keep the known unsafe insertions blocked."
            ),
        }
    holds = comparison.get("holds_promoted") or []
    if holds:
        return {
            "class": "RESEARCH_ONLY",
            "rationale": (
                f"Promoted {len(holds)} P2.5.10 HOLDs with drawing evidence and "
                "kept unique-model worsenings at 0. Shadow-only; not a production promotion."
            ),
        }
    return {
        "class": "RESEARCH_ONLY",
        "rationale": (
            "Evidence hierarchy is in place and known unsafe OCR insertions remain HOLD. "
            "Fifth Set P2.5.10 HOLDs were OCR-truncated uniforms, so none were promoted. "
            "Shadow-only; not a production promotion."
        ),
    }


__all__ = ["compare_strategies", "recommend", "transition_matrix"]
