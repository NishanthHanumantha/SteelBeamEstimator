"""Baseline vs Vision-assisted vs estimator comparison."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import MODEL_VERSION, PHASE_ID
from .metrics import (
    absolute_error_pct,
    error_reduction_pct,
    steel_accuracy_pct,
)

_EPS_KG = 0.05


def _beam_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(b["beam_id"]): b for b in (payload.get("beams") or [])}


def beam_improvement(
    *,
    estimator: Dict[str, Any],
    baseline: Dict[str, Any],
    shadow: Dict[str, Any],
) -> Dict[str, Any]:
    est = _beam_map(estimator)
    base = _beam_map(baseline)
    vis = _beam_map(shadow)
    ids = sorted(set(est) | set(base) | set(vis))
    improved: List[Dict[str, Any]] = []
    worsened: List[Dict[str, Any]] = []
    unchanged: List[str] = []
    newly_resolved: List[str] = []
    still_unresolved: List[str] = []
    for bid in ids:
        e = float((est.get(bid) or {}).get("steel_kg") or 0.0)
        b = float((base.get(bid) or {}).get("steel_kg") or 0.0)
        s = float((vis.get(bid) or {}).get("steel_kg") or 0.0)
        b_err = abs(b - e)
        s_err = abs(s - e)
        row = {
            "beam_id": bid,
            "baseline_steel": round(b, 3),
            "shadow_steel": round(s, 3),
            "ground_truth_steel": round(e, 3),
            "baseline_error": round(b_err, 3),
            "shadow_error": round(s_err, 3),
            "improvement": round(b_err - s_err, 3),
        }
        if s_err + _EPS_KG < b_err:
            improved.append(row)
        elif b_err + _EPS_KG < s_err:
            worsened.append({**row, "reason": "SHADOW_STEEL_FARTHER_FROM_ESTIMATOR"})
        else:
            unchanged.append(bid)
        if b_err > 0.5 and s_err <= 0.5:
            newly_resolved.append(bid)
        elif s_err > 0.5:
            still_unresolved.append(bid)
    return {
        "beams_improved": len(improved),
        "beams_worsened": len(worsened),
        "beams_unchanged": len(unchanged),
        "beams_newly_resolved": len(newly_resolved),
        "beams_still_unresolved": len(still_unresolved),
        "improved": improved,
        "worsened": worsened,
        "unchanged_ids": unchanged,
        "newly_resolved_ids": newly_resolved,
        "still_unresolved_ids": still_unresolved,
    }


def stirrup_impact(
    *,
    estimator: Dict[str, Any],
    baseline: Dict[str, Any],
    shadow: Dict[str, Any],
) -> Dict[str, Any]:
    e_kg = float(estimator.get("stirrup_kg") or 0.0)
    b_kg = float(baseline.get("stirrup_kg") or 0.0)
    s_kg = float(shadow.get("stirrup_kg") or 0.0)
    e_q = float(estimator.get("stirrup_qty") or 0.0)
    b_q = float(baseline.get("stirrup_qty") or 0.0)
    s_q = float(shadow.get("stirrup_qty") or 0.0)
    b_acc = steel_accuracy_pct(b_kg, e_kg)
    s_acc = steel_accuracy_pct(s_kg, e_kg)
    b_err = absolute_error_pct(b_kg, e_kg)
    s_err = absolute_error_pct(s_kg, e_kg)
    return {
        "baseline_stirrup_quantity": b_q,
        "shadow_stirrup_quantity": s_q,
        "ground_truth_stirrup_quantity": e_q,
        "baseline_stirrup_steel": round(b_kg, 3),
        "shadow_stirrup_steel": round(s_kg, 3),
        "ground_truth_stirrup_steel": round(e_kg, 3),
        "stirrup_accuracy_before": b_acc,
        "stirrup_accuracy_after": s_acc,
        "stirrup_error_before": b_err,
        "stirrup_error_after": s_err,
        "improvement_pp": None
        if b_acc is None or s_acc is None
        else round(s_acc - b_acc, 2),
    }


def build_comparison(
    *,
    baseline_bench: Dict[str, Any],
    shadow_bench: Dict[str, Any],
    books: Dict[str, Any],
    overlay_provenance: List[Dict[str, Any]],
) -> Dict[str, Any]:
    bs = baseline_bench.get("drawing_summary") or {}
    ss = shadow_bench.get("drawing_summary") or {}
    est_kg = bs.get("estimator_kg") or ss.get("estimator_kg")
    b_kg = bs.get("model_kg")
    s_kg = ss.get("model_kg")
    b_acc = bs.get("steel_accuracy_pct")
    if b_acc is None:
        b_acc = steel_accuracy_pct(b_kg, est_kg)
    s_acc = ss.get("steel_accuracy_pct")
    if s_acc is None:
        s_acc = steel_accuracy_pct(s_kg, est_kg)
    b_err = absolute_error_pct(b_kg, est_kg)
    s_err = absolute_error_pct(s_kg, est_kg)
    improvement = None if b_acc is None or s_acc is None else round(float(s_acc) - float(b_acc), 2)
    beams = beam_improvement(
        estimator=books.get("estimator") or {},
        baseline=books.get("baseline") or {},
        shadow=books.get("shadow") or {},
    )
    stirrup = stirrup_impact(
        estimator=books.get("estimator") or {},
        baseline=books.get("baseline") or {},
        shadow=books.get("shadow") or {},
    )
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "drawing_set": "Fifth Set Drawings",
        "baseline_steel_kg": b_kg,
        "vision_assisted_steel_kg": s_kg,
        "estimator_steel_kg": est_kg,
        "baseline_accuracy": b_acc,
        "vision_assisted_accuracy": s_acc,
        "STEEL_ACCURACY_IMPROVEMENT": improvement,
        "absolute_steel_error_baseline": b_err,
        "absolute_steel_error_vision": s_err,
        "error_reduction_percent": error_reduction_pct(b_err, s_err),
        "total_steel_error_kg_baseline": None
        if b_kg is None or est_kg is None
        else round(float(b_kg) - float(est_kg), 3),
        "total_steel_error_kg_vision": None
        if s_kg is None or est_kg is None
        else round(float(s_kg) - float(est_kg), 3),
        "BEAM_COUNT_ACCURACY": {
            "baseline": bs.get("beam_detection_pct"),
            "vision_assisted": ss.get("beam_detection_pct"),
        },
        "REINFORCEMENT_FIELD_ACCURACY": {
            "baseline_bar_accuracy_pct": bs.get("bar_accuracy_pct"),
            "vision_assisted_bar_accuracy_pct": ss.get("bar_accuracy_pct"),
        },
        "STIRRUP_ACCURACY": stirrup,
        "beam_impact": beams,
        "overlay_actions": overlay_provenance,
        "drawing_table": [
            {
                "drawing_set": "Fifth Set Drawings",
                "baseline_steel": b_kg,
                "vision_assisted_steel": s_kg,
                "estimator_steel": est_kg,
                "baseline_accuracy": b_acc,
                "vision_accuracy": s_acc,
                "improvement": improvement,
            }
        ],
    }


__all__ = ["beam_improvement", "build_comparison", "stirrup_impact"]
