"""Offline P2.5.10 comparison. Workbook totals are evaluation-only."""
from __future__ import annotations

from typing import Any, Dict, List, Set

from PhaseP258_controlled_vision_field_repair.metrics import (
    absolute_error_pct,
    error_reduction_pct,
    steel_accuracy_pct,
)
from PhaseP259_beam_safe_arbitration.comparison import strategy_row, unique_beam_impact

from .config import (
    CLS_CREATES_NEW,
    CLS_NO_NEW,
    CLS_SUPPLEMENT,
    DEC_ALLOW,
    DEC_HOLD,
    DEC_REJECT,
    MODEL_VERSION,
    PHASE_ID,
    STRATEGY_GATED,
    STRATEGY_UNKNOWN_ONLY,
)


def gate_counts(decisions: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {
        "ALLOW": 0,
        "HOLD": 0,
        "REJECT": 0,
        CLS_NO_NEW: 0,
        CLS_SUPPLEMENT: 0,
        CLS_CREATES_NEW: 0,
        "new_zone": 0,
        "new_piece": 0,
        "new_steel": 0,
    }
    for d in decisions:
        dec = d.get("decision")
        if dec == DEC_ALLOW:
            out["ALLOW"] += 1
        elif dec == DEC_HOLD:
            out["HOLD"] += 1
        elif dec == DEC_REJECT:
            out["REJECT"] += 1
        cls = d.get("classification")
        if cls in out:
            out[cls] += 1
        ins = d.get("insertion") or {}
        if ins.get("new_zone"):
            out["new_zone"] += 1
        if ins.get("new_piece"):
            out["new_piece"] += 1
        if ins.get("new_steel"):
            out["new_steel"] += 1
    return out


def _ids(rows: List[Dict[str, Any]]) -> Set[str]:
    return {str(r.get("beam_id")) for r in rows}


def compare_unknown_vs_gated(
    *,
    baseline_bench: Dict[str, Any],
    unknown_result: Dict[str, Any],
    gated_result: Dict[str, Any],
    production_mutations: int,
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
    gated_row = strategy_row(
        strategy=STRATEGY_GATED,
        baseline_bench=baseline_bench,
        shadow_bench=gated_result.get("shadow_bench") or {},
        books=gated_result.get("books") or {},
        candidates=gated_result.get("allowed") or gated_result.get("candidates") or [],
        overlay=gated_result.get("overlay") or [],
        production_mutations=production_mutations,
    )
    u_imp = (unknown_row.get("beam_impact") or {}).get("unique_model_detected") or {}
    g_imp = (gated_row.get("beam_impact") or {}).get("unique_model_detected") or {}
    u_improved = _ids(u_imp.get("improved") or [])
    u_worsened = _ids(u_imp.get("worsened") or [])
    g_improved = _ids(g_imp.get("improved") or [])
    g_worsened = _ids(g_imp.get("worsened") or [])
    counts = gate_counts((gated_result.get("gate") or {}).get("decisions") or [])
    unknown_acc = unknown_row.get("steel_accuracy")
    gated_acc = gated_row.get("steel_accuracy")
    det_acc = unknown_row.get("baseline_accuracy")
    return {
        "model_version": MODEL_VERSION,
        "phase_id": PHASE_ID,
        "unknown_only": unknown_row,
        "gated": gated_row,
        "gate_counts": counts,
        "worsenings_prevented": sorted(u_worsened - g_worsened),
        "worsenings_remaining": sorted(g_worsened),
        "improvements_retained": sorted(u_improved & g_improved),
        "improvements_lost": sorted(u_improved - g_improved),
        "new_improvements": sorted(g_improved - u_improved),
        "worsenings_prevented_count": len(u_worsened - g_worsened),
        "improvements_lost_count": len(u_improved - g_improved),
        "accuracy_delta_vs_unknown": None
        if unknown_acc is None or gated_acc is None
        else round(float(gated_acc) - float(unknown_acc), 2),
        "accuracy_delta_vs_deterministic": None
        if det_acc is None or gated_acc is None
        else round(float(gated_acc) - float(det_acc), 2),
        "steel_delta_vs_unknown": None
        if unknown_row.get("vision_shadow_steel") is None or gated_row.get("vision_shadow_steel") is None
        else round(float(gated_row["vision_shadow_steel"]) - float(unknown_row["vision_shadow_steel"]), 3),
        "unique_model_detected_unknown": u_imp.get("beam_count"),
        "unique_model_detected_gated": g_imp.get("beam_count"),
        "metrics": {
            "deterministic_steel": unknown_row.get("baseline_steel"),
            "p259_unknown_steel": unknown_row.get("vision_shadow_steel"),
            "p2510_gated_steel": gated_row.get("vision_shadow_steel"),
            "estimator_steel": unknown_row.get("estimator_steel"),
            "deterministic_accuracy": det_acc,
            "p259_accuracy": unknown_acc,
            "p2510_accuracy": gated_acc,
            "absolute_error_gated": gated_row.get("absolute_error"),
            "error_reduction_vs_det": error_reduction_pct(
                unknown_row.get("baseline_absolute_error"), gated_row.get("absolute_error")
            ),
        },
    }


def recommend(comparison: Dict[str, Any], *, leakage_ok: bool, prod_mut: int) -> Dict[str, Any]:
    gated = comparison.get("gated") or {}
    unknown = comparison.get("unknown_only") or {}
    g_w = int(gated.get("worsened_beams") or 0)
    u_w = int(unknown.get("worsened_beams") or 0)
    g_acc = gated.get("steel_accuracy")
    u_acc = unknown.get("steel_accuracy")
    lost = int(comparison.get("improvements_lost_count") or 0)
    prevented = int(comparison.get("worsenings_prevented_count") or 0)
    if prod_mut or not leakage_ok:
        return {
            "class": "NEITHER",
            "rationale": "Safety firewall failed; P2.5.10 remains shadow-only.",
        }
    if g_w == 0 and lost == 0 and g_acc is not None and u_acc is not None and float(g_acc) >= float(u_acc):
        return {
            "class": "PROMOTION_CANDIDATE",
            "rationale": (
                "Gated UNKNOWN-only removed unique-model worsenings without losing "
                "UNKNOWN recoveries. Still shadow-only: P2.5.10 does not authorize "
                "production promotion."
            ),
        }
    if prevented > 0:
        return {
            "class": "RESEARCH_ONLY",
            "rationale": (
                f"Gate prevented {prevented} unique-model worsenings and lost {lost} "
                "improvements. Insertion safety is not yet production-ready."
            ),
        }
    return {
        "class": "NEITHER",
        "rationale": "Gate did not establish a beam-safe insertion policy worth promoting.",
    }


__all__ = ["compare_unknown_vs_gated", "gate_counts", "recommend", "unique_beam_impact", "steel_accuracy_pct", "absolute_error_pct"]
