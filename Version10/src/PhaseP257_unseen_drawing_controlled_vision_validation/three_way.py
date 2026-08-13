"""Three-way field evaluation: ground truth vs deterministic vs Vision."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP254_semantic_reinforcement_vision_benchmark.baseline_comparator import (
    roles_compatible,
    types_compatible,
)
from PhaseP256_controlled_field_level_vision_experiment.config import FIELDS
from PhaseP256_controlled_field_level_vision_experiment.field_arbitrator import (
    extract_det_value,
    extract_vis_value,
    values_equivalent,
)
from PhaseP256_controlled_field_level_vision_experiment.field_validator import (
    det_present,
    vision_present,
)

from .config import (
    EVAL_EXACT,
    EVAL_NOT_SCORED,
    EVAL_UNRESOLVED,
    EVAL_WRONG,
    INC_ADDS_CORRECT,
    INC_CONFIRMS,
    INC_CONFLICTS_CORRECT_DET,
    INC_CORRECTS_WRONG_DET,
    INC_NONE,
    INC_NOT_SCORED,
    INC_WRONG_ON_CORRECT_DET,
)

_GT_KEY = {
    "semantic_type": "semantic_type",
    "reinforcement_role": "role",
    "diameter": "diameter_mm",
    "quantity": "quantity",
    "legs": "legs",
    "spacing": "spacing_mm",
    "beam_association": "beam_association",
    "zone": "zone",
}
_AVAIL = {
    "semantic_type": "semantic_type",
    "reinforcement_role": "role",
    "diameter": "diameter_mm",
    "quantity": "quantity",
    "legs": "legs",
    "spacing": "spacing_mm",
    "beam_association": "beam_association",
    "zone": "zone",
}


def _gt_value(gt: Dict[str, Any], field: str) -> Any:
    return gt.get(_GT_KEY[field])


def _gt_available(gt: Dict[str, Any], field: str) -> bool:
    if not gt.get("available"):
        return False
    return _AVAIL[field] in (gt.get("fields_available") or [])


def _match(field: str, pred: Any, gt_val: Any) -> bool:
    if field == "semantic_type":
        return types_compatible(pred, gt_val) or pred == gt_val
    if field == "reinforcement_role":
        return pred == gt_val or roles_compatible(pred, gt_val)
    return values_equivalent(field, pred, gt_val)


def _eval_side(known: bool, pred: Any, field: str, gt_val: Any, scored: bool) -> str:
    if not scored:
        return EVAL_NOT_SCORED
    if not known:
        return EVAL_UNRESOLVED
    return EVAL_EXACT if _match(field, pred, gt_val) else EVAL_WRONG


def evaluate_field(
    *,
    field: str,
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    ground_truth: Dict[str, Any],
    accepted_shadow: bool,
) -> Dict[str, Any]:
    # Zone is diagnostic only and never enters promotion / incremental KPIs.
    scored = _gt_available(ground_truth, field) and field != "zone"
    diagnostic = field == "zone" and _gt_available(ground_truth, field)
    gt_val = _gt_value(ground_truth, field)
    d_val = extract_det_value(deterministic, field)
    v_val = extract_vis_value(vision, field)
    d_known = det_present(d_val, field=field)
    v_known = vision_present(v_val, field=field)
    d_eval = _eval_side(d_known, d_val, field, gt_val, scored or diagnostic)
    v_eval = _eval_side(v_known, v_val, field, gt_val, scored or diagnostic)
    if field == "zone":
        d_eval = EVAL_NOT_SCORED if not diagnostic else d_eval
        v_eval = EVAL_NOT_SCORED if not diagnostic else v_eval
        if diagnostic:
            # Keep diagnostic labels but force NOT_SCORED for promotion accounting.
            pass

    inc = INC_NOT_SCORED
    dangerous = False
    adds = False
    would_change = v_known and not values_equivalent(field, d_val, v_val)
    if scored:
        if d_eval == EVAL_EXACT and v_eval == EVAL_EXACT:
            inc = INC_CONFIRMS
        elif d_eval == EVAL_EXACT and v_eval == EVAL_WRONG:
            inc = INC_WRONG_ON_CORRECT_DET
            dangerous = bool(would_change)
        elif d_eval == EVAL_EXACT and v_eval == EVAL_UNRESOLVED:
            inc = INC_NONE
        elif d_eval in (EVAL_UNRESOLVED, EVAL_WRONG) and v_eval == EVAL_EXACT:
            inc = INC_ADDS_CORRECT if d_eval == EVAL_UNRESOLVED else INC_CORRECTS_WRONG_DET
            adds = True
        elif d_eval == EVAL_EXACT and would_change:
            inc = INC_CONFLICTS_CORRECT_DET
            dangerous = True
        else:
            inc = INC_NONE

    hypo = d_val
    hypo_source = "DETERMINISTIC"
    if scored and d_eval != EVAL_EXACT and v_eval == EVAL_EXACT and accepted_shadow:
        hypo = v_val
        hypo_source = "VISION_SHADOW_CANDIDATE"
    hypo_eval = EVAL_NOT_SCORED
    if scored:
        hypo_eval = EVAL_EXACT if hypo_source == "VISION_SHADOW_CANDIDATE" else d_eval

    return {
        "field": field,
        "scored": scored,
        "ground_truth": gt_val if (scored or diagnostic) else None,
        "deterministic_value": d_val,
        "vision_value": v_val,
        "deterministic_eval": EVAL_NOT_SCORED if field == "zone" else d_eval,
        "vision_eval": EVAL_NOT_SCORED if field == "zone" else v_eval,
        "zone_diagnostic_det": d_eval if field == "zone" and diagnostic else None,
        "zone_diagnostic_vis": v_eval if field == "zone" and diagnostic else None,
        "incremental": INC_NOT_SCORED if field == "zone" else inc,
        "dangerous_candidate": False if field == "zone" else dangerous,
        "vision_better": False if field == "zone" else adds,
        "vision_worse": bool(scored and d_eval == EVAL_EXACT and v_eval == EVAL_WRONG),
        "both_correct": bool(scored and d_eval == EVAL_EXACT and v_eval == EVAL_EXACT),
        "both_wrong": bool(scored and d_eval == EVAL_WRONG and v_eval == EVAL_WRONG),
        "deterministic_unknown_vision_correct": bool(
            scored and d_eval == EVAL_UNRESOLVED and v_eval == EVAL_EXACT
        ),
        "hypothetical_value": hypo,
        "hypothetical_source": hypo_source,
        "hypothetical_eval": EVAL_NOT_SCORED if field == "zone" else hypo_eval,
        "production_change": "NONE",
        "zone_promotable": False,
    }


def evaluate_candidate(
    *,
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    ground_truth: Dict[str, Any],
    accepted_shadow_fields: list,
) -> Dict[str, Any]:
    accepted = set(accepted_shadow_fields or [])
    fields = {}
    for f in FIELDS:
        fields[f] = evaluate_field(
            field=f,
            deterministic=deterministic,
            vision=vision,
            ground_truth=ground_truth,
            accepted_shadow=f in accepted,
        )
    return fields


__all__ = ["evaluate_candidate", "evaluate_field"]
