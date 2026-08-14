"""Engineering KPIs for P2.5.8. Reuses QA.2A steel accuracy definition."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import DEC_BLOCK, DEC_PROMOTE, MODEL_VERSION, PHASE_ID


def steel_accuracy_pct(model_kg: Optional[float], estimator_kg: Optional[float]) -> Optional[float]:
    """QA.2A metric8: max(0, 100 - |model-estimator|/estimator * 100)."""
    if model_kg is None or estimator_kg is None:
        return None
    if abs(float(estimator_kg)) < 1e-12:
        return 0.0 if abs(float(model_kg)) > 1e-12 else 100.0
    diff_pct = abs(float(model_kg) - float(estimator_kg)) / abs(float(estimator_kg)) * 100.0
    return round(max(0.0, 100.0 - diff_pct), 2)


def absolute_error_pct(model_kg: Optional[float], estimator_kg: Optional[float]) -> Optional[float]:
    if model_kg is None or estimator_kg is None:
        return None
    if abs(float(estimator_kg)) < 1e-12:
        return 100.0 if abs(float(model_kg)) > 1e-12 else 0.0
    return round(abs(float(model_kg) - float(estimator_kg)) / abs(float(estimator_kg)) * 100.0, 2)


def error_reduction_pct(baseline_err: Optional[float], vision_err: Optional[float]) -> Optional[float]:
    if baseline_err is None or vision_err is None:
        return None
    if abs(float(baseline_err)) < 1e-12:
        return 0.0
    return round((float(baseline_err) - float(vision_err)) / abs(float(baseline_err)) * 100.0, 2)


def classify_decision(
    *,
    recompute_ok: bool,
    accuracy_improvement_pp: Optional[float],
    worsened_beams: int,
    dangerous_overrides: int,
    production_mutations: int,
) -> Tuple[str, str]:
    if not recompute_ok:
        return "BLOCKED", "BLOCKED — architecture correction required"
    if production_mutations or dangerous_overrides:
        return "NEGATIVE", "NEGATIVE — tighten validation / revert promotion class"
    if worsened_beams > 0:
        return "NEGATIVE", "NEGATIVE — tighten validation / revert promotion class"
    if accuracy_improvement_pp is not None and accuracy_improvement_pp >= 1.0:
        return "POSITIVE", "POSITIVE — P2.5.9 multi-set controlled validation"
    return "NEUTRAL", "NEUTRAL — improve trigger/promotion rules"


def promotion_safety(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    promoted = [c for c in candidates if c.get("promotion_decision") == DEC_PROMOTE]
    blocked = [c for c in candidates if c.get("promotion_decision") == DEC_BLOCK]
    ineligible = [
        c
        for c in candidates
        if c.get("promotion_decision") not in (DEC_PROMOTE, DEC_BLOCK)
    ]
    by_field: Dict[str, Dict[str, int]] = {}
    for c in candidates:
        f = str(c.get("field_name") or "")
        rec = by_field.setdefault(f, {"promoted": 0, "blocked": 0, "ineligible": 0})
        if c.get("promotion_decision") == DEC_PROMOTE:
            rec["promoted"] += 1
        elif c.get("promotion_decision") == DEC_BLOCK:
            rec["blocked"] += 1
        else:
            rec["ineligible"] += 1
    reasons: Dict[str, int] = {}
    for c in candidates:
        r = str(c.get("reason") or "UNKNOWN")
        reasons[r] = reasons.get(r, 0) + 1
    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "vision_candidates": len({c.get("candidate_id") for c in candidates}),
        "eligible_repair_candidates": len(
            {c.get("candidate_id") for c in promoted}
        ),
        "promoted_shadow_fields": len(promoted),
        "blocked_fields": len(blocked),
        "ineligible_fields": len(ineligible),
        "conflicts": sum(
            1
            for c in candidates
            if "CONFLICT" in str(c.get("reason") or "")
            or c.get("reason") == "CONFIRMED_FIELD_CANNOT_BE_OVERRIDDEN"
        ),
        "validation_failures": sum(
            1 for c in candidates if c.get("validation_status") == "FAIL" and c.get("vision_status") == "INVALID"
        ),
        "by_field": by_field,
        "reasons": reasons,
        "production_mutation": 0,
    }


def field_known_counts(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for field in ("diameter", "legs", "spacing", "reinforcement_role"):
        rows = [c for c in candidates if c.get("field_name") == field]
        before = 0
        after = 0
        for c in rows:
            det_s = c.get("deterministic_status") or ""
            if det_s == "DETERMINISTIC_CONFIRMED":
                before += 1
            if c.get("promotion_decision") == DEC_PROMOTE or det_s == "DETERMINISTIC_CONFIRMED":
                after += 1
        out[field] = {
            "before_confirmed_or_known": before,
            "after_confirmed_or_repaired": after,
            "promoted": sum(1 for c in rows if c.get("promotion_decision") == DEC_PROMOTE),
        }
    return out


__all__ = [
    "absolute_error_pct",
    "classify_decision",
    "error_reduction_pct",
    "field_known_counts",
    "promotion_safety",
    "steel_accuracy_pct",
]
