"""Offline strategy comparison. Estimator/GT allowed HERE only, never in arbitration."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from PhaseP258_controlled_vision_field_repair.metrics import (
    absolute_error_pct,
    error_reduction_pct,
    steel_accuracy_pct,
)

from .config import (
    MODEL_VERSION,
    OUT_ACCEPT_PARTIAL,
    OUT_ACCEPT_UNKNOWN,
    OUT_HOLD_PARTIAL,
    OUT_REJECT_PARTIAL,
    PHASE_ID,
    STRATEGY_P258_CURRENT,
)

_EPS_KG = 0.05


def _beam_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(b["beam_id"]): b for b in (payload.get("beams") or [])}


def classify_repair_class(rec: Dict[str, Any]) -> str:
    field = rec.get("field_name")
    det_s = rec.get("deterministic_status")
    text = str(rec.get("annotation_text") or "")
    triggers = [str(t) for t in (rec.get("trigger_reason") or [])]
    ocr = "OCR" in " ".join(triggers).upper() or "\\X" in text
    if det_s == "DETERMINISTIC_PARTIAL" and field == "spacing":
        return "PARTIAL_SPACING"
    if det_s == "DETERMINISTIC_UNKNOWN":
        if ocr:
            return "OCR_STIRRUP_RECOVERY"
        if field == "diameter":
            return "DIAMETER_RECOVERY"
        if field == "legs":
            return "LEGS_RECOVERY"
        if field == "spacing":
            return "UNKNOWN_SPACING_RECOVERY"
        return "UNKNOWN_RECOVERY"
    return "OTHER"


def unique_beam_impact(
    *,
    estimator: Dict[str, Any],
    baseline: Dict[str, Any],
    shadow: Dict[str, Any],
) -> Dict[str, Any]:
    """
    P2.5.8 counted unique beam_id strings in the UNION of estimator + baseline
    + shadow workbooks (185 IDs = 21+150+14). Fifth Set production detects 143
    beams; the estimator workbook has more IDs. P2.5.9 reports both universes
    and does not silently rewrite the P2.5.8 definition.
    """
    est = _beam_map(estimator)
    base = _beam_map(baseline)
    vis = _beam_map(shadow)
    union_ids = sorted(set(est) | set(base) | set(vis))
    model_ids = sorted(set(base) | set(vis))
    matched_ids = sorted(set(est) & set(base))

    def _score(ids: List[str]) -> Dict[str, Any]:
        improved: List[Dict[str, Any]] = []
        worsened: List[Dict[str, Any]] = []
        unchanged: List[str] = []
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
                "engineering_delta": round(s - b, 3),
                "improvement": round(b_err - s_err, 3),
            }
            if s_err + _EPS_KG < b_err:
                improved.append(row)
            elif b_err + _EPS_KG < s_err:
                worsened.append({**row, "reason": "SHADOW_STEEL_FARTHER_FROM_ESTIMATOR"})
            else:
                unchanged.append(bid)
        n = max(len(ids), 1)
        return {
            "beam_count": len(ids),
            "improved": improved,
            "worsened": worsened,
            "unchanged_ids": unchanged,
            "beams_improved": len(improved),
            "beams_worsened": len(worsened),
            "beams_unchanged": len(unchanged),
            "improvement_rate": round(len(improved) / n, 4),
            "worsening_rate": round(len(worsened) / n, 4),
        }

    union = _score(union_ids)
    model = _score(model_ids)
    matched = _score(matched_ids)
    return {
        "counting_note": (
            "P2.5.8 used unique normalized beam_id strings in the UNION of "
            "estimator + model workbooks (21+150+14=185), not the 143 detected "
            "production beams. Estimator-only IDs with 0 kg on both sides count "
            "as unchanged."
        ),
        "p258_union_universe": union,
        "unique_model_detected": model,
        "unique_matched_estimator_model": matched,
        "estimator_beam_ids": len(est),
        "baseline_model_beam_ids": len(base),
        "shadow_model_beam_ids": len(vis),
        "union_beam_ids": len(union_ids),
    }


def attach_repair_provenance(
    impact: Dict[str, Any],
    *,
    candidates: List[Dict[str, Any]],
    overlay: List[Dict[str, Any]],
) -> Dict[str, Any]:
    by_beam_cand: Dict[str, List[Dict[str, Any]]] = {}
    for c in candidates:
        by_beam_cand.setdefault(str(c.get("beam_id")), []).append(c)
    by_beam_ov: Dict[str, List[Dict[str, Any]]] = {}
    for o in overlay:
        by_beam_ov.setdefault(str(o.get("beam_id")), []).append(o)

    def _enrich(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for row in rows:
            bid = row["beam_id"]
            recs = by_beam_cand.get(bid) or []
            promoted = [c for c in recs if c.get("promotion_decision") == "CONTROLLED_RECOMPUTE"]
            row = dict(row)
            row["vision_repairs"] = [
                {
                    "field_name": c.get("field_name"),
                    "deterministic_status": c.get("deterministic_status"),
                    "deterministic_value": c.get("deterministic_value"),
                    "vision_value": c.get("vision_value"),
                    "arbitration_outcome": c.get("arbitration_outcome"),
                    "reason": c.get("reason"),
                    "reason_codes": c.get("reason_codes"),
                    "repair_class": classify_repair_class(c),
                }
                for c in promoted
            ]
            row["overlay"] = by_beam_ov.get(bid) or []
            row["arbitration_decisions"] = sorted(
                {str(c.get("arbitration_outcome")) for c in recs if c.get("field_name") in ("diameter", "legs", "spacing")}
            )
            out.append(row)
        return out

    for key in ("p258_union_universe", "unique_model_detected", "unique_matched_estimator_model"):
        block = impact.get(key) or {}
        block["improved"] = _enrich(list(block.get("improved") or []))
        block["worsened"] = _enrich(list(block.get("worsened") or []))
        impact[key] = block
    return impact


def field_strategy_counts(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    unknown_acc = 0
    partial_acc = 0
    partial_hold = 0
    partial_rej = 0
    by_class: Dict[str, int] = {}
    for c in candidates:
        oc = c.get("arbitration_outcome")
        if oc == OUT_ACCEPT_UNKNOWN or (
            c.get("promotion_decision") == "CONTROLLED_RECOMPUTE"
            and c.get("deterministic_status") == "DETERMINISTIC_UNKNOWN"
        ):
            unknown_acc += 1
        if oc in ("P258_PARTIAL_PROMOTED", OUT_ACCEPT_PARTIAL) or (
            c.get("promotion_decision") == "CONTROLLED_RECOMPUTE"
            and c.get("deterministic_status") == "DETERMINISTIC_PARTIAL"
        ):
            partial_acc += 1
        if oc == OUT_HOLD_PARTIAL:
            partial_hold += 1
        if oc == OUT_REJECT_PARTIAL:
            partial_rej += 1
        if c.get("promotion_decision") == "CONTROLLED_RECOMPUTE":
            cls = classify_repair_class(c)
            by_class[cls] = by_class.get(cls, 0) + 1
    return {
        "unknown_fields_accepted": unknown_acc,
        "partial_fields_accepted": partial_acc,
        "partial_fields_held": partial_hold,
        "partial_fields_rejected": partial_rej,
        "promoted_by_class": by_class,
        "promoted_shadow_fields": sum(
            1 for c in candidates if c.get("promotion_decision") == "CONTROLLED_RECOMPUTE"
        ),
    }


def stirrup_block(books: Dict[str, Any]) -> Dict[str, Any]:
    est = books.get("estimator") or {}
    base = books.get("baseline") or {}
    sh = books.get("shadow") or {}
    e_kg = float(est.get("stirrup_kg") or 0.0)
    b_kg = float(base.get("stirrup_kg") or 0.0)
    s_kg = float(sh.get("stirrup_kg") or 0.0)
    return {
        "baseline_stirrup_steel": round(b_kg, 3),
        "shadow_stirrup_steel": round(s_kg, 3),
        "estimator_stirrup_steel": round(e_kg, 3),
        "stirrup_accuracy_before": steel_accuracy_pct(b_kg, e_kg),
        "stirrup_accuracy_after": steel_accuracy_pct(s_kg, e_kg),
        "stirrup_improvement_pp": round(
            (steel_accuracy_pct(s_kg, e_kg) or 0) - (steel_accuracy_pct(b_kg, e_kg) or 0), 2
        ),
    }


def strategy_row(
    *,
    strategy: str,
    baseline_bench: Dict[str, Any],
    shadow_bench: Dict[str, Any],
    books: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    overlay: List[Dict[str, Any]],
    production_mutations: int,
) -> Dict[str, Any]:
    bs = baseline_bench.get("drawing_summary") or {}
    ss = shadow_bench.get("drawing_summary") or {}
    est_kg = bs.get("estimator_kg") or ss.get("estimator_kg")
    b_kg = bs.get("model_kg")
    s_kg = ss.get("model_kg")
    b_acc = bs.get("steel_accuracy_pct") or steel_accuracy_pct(b_kg, est_kg)
    s_acc = ss.get("steel_accuracy_pct") or steel_accuracy_pct(s_kg, est_kg)
    b_err = absolute_error_pct(b_kg, est_kg)
    s_err = absolute_error_pct(s_kg, est_kg)
    impact = attach_repair_provenance(
        unique_beam_impact(estimator=books.get("estimator") or {}, baseline=books.get("baseline") or {}, shadow=books.get("shadow") or {}),
        candidates=candidates,
        overlay=overlay,
    )
    model = impact["unique_model_detected"]
    counts = field_strategy_counts(candidates)
    stirrup = stirrup_block(books)
    improvement = None if b_acc is None or s_acc is None else round(float(s_acc) - float(b_acc), 2)
    return {
        "strategy": strategy,
        "baseline_steel": b_kg,
        "vision_shadow_steel": s_kg,
        "estimator_steel": est_kg,
        "steel_accuracy": s_acc,
        "baseline_accuracy": b_acc,
        "delta_vs_deterministic": improvement,
        "absolute_error": s_err,
        "baseline_absolute_error": b_err,
        "error_reduction": error_reduction_pct(b_err, s_err),
        "stirrup_steel": stirrup.get("shadow_stirrup_steel"),
        "stirrup_accuracy": stirrup.get("stirrup_accuracy_after"),
        "stirrup": stirrup,
        "improved_beams": model["beams_improved"],
        "unchanged_beams": model["beams_unchanged"],
        "worsened_beams": model["beams_worsened"],
        "improvement_count": model["beams_improved"],
        "worsening_count": model["beams_worsened"],
        "improvement_rate": model["improvement_rate"],
        "worsening_rate": model["worsening_rate"],
        "unknown_fields_accepted": counts["unknown_fields_accepted"],
        "partial_fields_accepted": counts["partial_fields_accepted"],
        "partial_fields_held": counts["partial_fields_held"],
        "partial_fields_rejected": counts["partial_fields_rejected"],
        "promoted_by_class": counts["promoted_by_class"],
        "production_mutations": production_mutations,
        "beam_impact": impact,
        "p258_union_improved": impact["p258_union_universe"]["beams_improved"],
        "p258_union_unchanged": impact["p258_union_universe"]["beams_unchanged"],
        "p258_union_worsened": impact["p258_union_universe"]["beams_worsened"],
    }


def class_analysis(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Which repair class drives improvement vs worsening (offline, model-detected)."""
    out: Dict[str, Any] = {}
    for row in rows:
        worsened = (row.get("beam_impact") or {}).get("unique_model_detected", {}).get("worsened") or []
        improved = (row.get("beam_impact") or {}).get("unique_model_detected", {}).get("improved") or []

        def _classes(items: List[Dict[str, Any]]) -> Dict[str, int]:
            c: Dict[str, int] = {}
            for it in items:
                for r in it.get("vision_repairs") or []:
                    k = r.get("repair_class") or "OTHER"
                    c[k] = c.get(k, 0) + 1
            return c

        out[row["strategy"]] = {
            "worsened_repair_classes": _classes(worsened),
            "improved_repair_classes": _classes(improved),
            "promoted_by_class": row.get("promoted_by_class"),
            "worsened_ids": [w["beam_id"] for w in worsened],
            "improved_ids": [w["beam_id"] for w in improved],
        }
    a = next((r for r in rows if r["strategy"] == STRATEGY_P258_CURRENT), None)
    b = next((r for r in rows if r["strategy"] == "P259_UNKNOWN_ONLY"), None)
    c = next((r for r in rows if r["strategy"] == "P259_CONSERVATIVE_PARTIAL"), None)
    a_w = set((out.get(STRATEGY_P258_CURRENT) or {}).get("worsened_ids") or [])
    b_w = set((out.get("P259_UNKNOWN_ONLY") or {}).get("worsened_ids") or [])
    c_w = set((out.get("P259_CONSERVATIVE_PARTIAL") or {}).get("worsened_ids") or [])
    return {
        "by_strategy": out,
        "p258_worsened_disappear_under_unknown_only": sorted(a_w - b_w),
        "p258_worsened_remaining_under_unknown_only": sorted(a_w & b_w),
        "unknown_only_vs_p258_accuracy_delta": None
        if not (a and b)
        else round(float(b.get("steel_accuracy") or 0) - float(a.get("steel_accuracy") or 0), 2),
        "conservative_vs_unknown_accuracy_delta": None
        if not (b and c)
        else round(float(c.get("steel_accuracy") or 0) - float(b.get("steel_accuracy") or 0), 2),
        "conservative_new_worsened_vs_unknown": sorted(c_w - b_w),
        "p258_improvement_pp": None if not a else a.get("delta_vs_deterministic"),
        "unknown_only_improvement_pp": None if not b else b.get("delta_vs_deterministic"),
        "conservative_improvement_pp": None if not c else c.get("delta_vs_deterministic"),
        "model_version": MODEL_VERSION,
        "phase_id": PHASE_ID,
    }


__all__ = [
    "attach_repair_provenance",
    "class_analysis",
    "classify_repair_class",
    "strategy_row",
    "unique_beam_impact",
]
