"""Promotion gate: whitelist + completeness + P2.5.6 validation. Field-level, not whole-candidate."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP256_controlled_field_level_vision_experiment.field_validator import (
    validate_vision_field,
    vision_present,
)

from .config import (
    DEC_BLOCK,
    DEC_INELIGIBLE,
    DEC_PROMOTE,
    DET_CONFIRMED,
    DET_PARTIAL,
    DET_UNKNOWN,
    FORBIDDEN_FIELDS,
    LEVEL_BLOCKED,
    LEVEL_CONTROLLED_RECOMPUTE,
    LEVEL_PRODUCTION_INELIGIBLE,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    WHITELIST_FIELDS,
)
from .det_status import classify_deterministic_status
from .promotion_rules import is_whitelisted, load_promotion_rules
from .repair_contract import build_repair_candidate

_FIELD_TO_TW = {
    "diameter": "diameter",
    "legs": "legs",
    "spacing": "spacing",
    "reinforcement_role": "reinforcement_role",
    "semantic_type": "semantic_type",
}


def _gt_wrong(tw_field: Dict[str, Any]) -> bool:
    return bool(tw_field.get("scored")) and tw_field.get("vision_eval") == "WRONG"


def evaluate_field_promotion(
    *,
    audit: Dict[str, Any],
    field: str,
    rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rules = rules or load_promotion_rules()
    cand_id = audit.get("candidate_id")
    beam_id = audit.get("beam_id")
    ann_id = audit.get("annotation_id")
    text = str(audit.get("annotation_text") or "")
    det = audit.get("deterministic_result") or {}
    vis = audit.get("vision_result") or {}
    tw = (audit.get("three_way") or {}).get(field) or {}
    det_type = det.get("semantic_type") or audit.get("deterministic_type")
    triggers = list(audit.get("shadow_trigger_reason") or [])

    det_val = tw.get("deterministic_value")
    vis_val = tw.get("vision_value")
    if field == "diameter":
        det_val = det.get("diameter_value_mm") if det_val is None else det_val
        vis_val = vis.get("diameter_mm") if vis_val is None else vis_val
    elif field == "legs":
        det_val = det.get("leg_count") if det_val is None else det_val
        vis_val = vis.get("legs") if vis_val is None else vis_val
    elif field == "spacing":
        det_val = list(det.get("spacing_values_mm") or det_val or [])
        vis_val = list(vis.get("spacing_mm") or vis_val or [])

    det_status = classify_deterministic_status(
        field=field,
        deterministic_value=det_val,
        annotation_text=text,
        deterministic_type=det_type,
    )
    vis_known = vision_present(vis_val, field=field)
    vis_ok = False
    vis_err: List[str] = ["VISION_MISSING"]
    if vis_known:
        checked = validate_vision_field(
            field=field,
            value=vis_val,
            annotation_text=text,
            effective_type=str(det_type or vis.get("semantic_type") or ""),
        )
        vis_ok = bool(checked.get("ok"))
        vis_err = list(checked.get("errors") or [])

    reason = "OK"
    decision = DEC_INELIGIBLE
    level = LEVEL_PRODUCTION_INELIGIBLE

    if audit.get("invoke_claude") is False or not vis:
        reason = "NO_VISION_RESULT"
        decision = DEC_BLOCK
        level = LEVEL_BLOCKED
    elif field in FORBIDDEN_FIELDS or field == "zone":
        reason = "FORBIDDEN_FIELD"
    elif not is_whitelisted(semantic_type=str(det_type or ""), field=field, rules=rules):
        reason = "NOT_WHITELISTED"
    elif field in WHITELIST_FIELDS and det_type != "STIRRUP":
        # Stirrup numeric repairs require deterministic type already STIRRUP (B58).
        reason = "TYPE_NOT_STIRRUP"
        decision = DEC_BLOCK
        level = LEVEL_BLOCKED
    elif det_status == DET_CONFIRMED:
        reason = "CONFIRMED_FIELD_CANNOT_BE_OVERRIDDEN"
        decision = DEC_BLOCK
        level = LEVEL_BLOCKED
    elif not vis_known:
        reason = "VISION_VALUE_MISSING"
        decision = DEC_BLOCK
        level = LEVEL_BLOCKED
    elif not vis_ok:
        reason = vis_err[0] if vis_err else "VISION_INVALID"
        decision = DEC_BLOCK
        level = LEVEL_BLOCKED
    elif _gt_wrong(tw):
        reason = "VISION_WRONG_VS_GROUND_TRUTH"
        decision = DEC_BLOCK
        level = LEVEL_BLOCKED
    elif det_status in (DET_UNKNOWN, DET_PARTIAL):
        reason = "DETERMINISTIC_PARTIAL_VISION_VALID" if det_status == DET_PARTIAL else "DETERMINISTIC_UNKNOWN_VISION_VALID"
        decision = DEC_PROMOTE
        level = LEVEL_CONTROLLED_RECOMPUTE
    else:
        reason = "NO_REPAIR_PATH"
        decision = DEC_BLOCK
        level = LEVEL_BLOCKED

    gt_status = "NOT_SCORED"
    if tw.get("scored"):
        gt_status = str(tw.get("vision_eval") or "SCORED")

    return build_repair_candidate(
        candidate_id=str(cand_id),
        beam_id=str(beam_id),
        annotation_id=str(ann_id),
        annotation_text=text,
        field_name=field,
        deterministic_value=det_val,
        deterministic_status=det_status,
        vision_value=vis_val,
        vision_status="VALID" if vis_ok else "INVALID",
        trigger_reason=triggers,
        validation_status="PASS" if vis_ok else "FAIL",
        validation_rules_passed=bool(vis_ok),
        ground_truth_value=tw.get("ground_truth"),
        ground_truth_status=gt_status,
        promotion_class=level,
        promotion_decision=decision,
        source_model=audit.get("model"),
        prompt_version=str(audit.get("prompt_version") or PROMPT_VERSION),
        schema_version=str(audit.get("schema_version") or SCHEMA_VERSION),
        evidence_fingerprint=audit.get("evidence_fingerprint"),
        reason=reason,
    )


def evaluate_audit(audit: Dict[str, Any], rules: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    rules = rules or load_promotion_rules()
    out = []
    for field in ("diameter", "legs", "spacing", "reinforcement_role", "semantic_type", "quantity", "zone"):
        out.append(evaluate_field_promotion(audit=audit, field=field, rules=rules))
    return out


__all__ = ["evaluate_audit", "evaluate_field_promotion"]
