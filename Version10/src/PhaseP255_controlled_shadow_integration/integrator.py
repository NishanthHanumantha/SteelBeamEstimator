"""Single-candidate shadow integration after deterministic snapshot + Vision observe."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP254_semantic_reinforcement_vision_benchmark.benchmark_evaluator import (
    evaluate_against_ground_truth,
)

from .arbitrator import (
    apply_gt_overlay,
    classify_operational,
    collect_important_conflicts,
    promotion_eligible_flag,
    vision_status_label,
)
from .eligibility import eligibility_reasons
from .hypothetical_impact import hypothetical_impact
from .safety_gates import apply_safety_gates
from .shadow_contract import build_shadow_integration_result


def integrate_one(
    *,
    candidate: Dict[str, Any],
    deterministic: Dict[str, Any],
    vision_obs: Dict[str, Any],
    ground_truth: Optional[Dict[str, Any]] = None,
    eligibility_mode: str = "CONFIGURED_FULL_SHADOW",
) -> Dict[str, Any]:
    """
    Compare immutable deterministic snapshot with Vision. Never mutates production.
    Ground truth is used only for VISION_WRONG overlay / quality metrics.
    """
    validation = vision_obs.get("validation") or {"valid": False, "errors": [], "warnings": []}
    vision = vision_obs.get("validated_interpretation")
    validation_ok = bool(validation.get("valid")) and vision is not None
    api_ok = bool(vision_obs.get("api_ok"))

    safety = apply_safety_gates(
        annotation_text=str(candidate.get("raw_text") or deterministic.get("raw_text") or ""),
        deterministic=deterministic,
        vision=vision,
        validation=validation,
    )

    conflict_fields, conflict_details = collect_important_conflicts(
        deterministic=deterministic,
        vision=vision if validation_ok else None,
    )
    for extra in safety.get("flags") or []:
        if extra in (
            "TYPE_CHANGE_VS_DETERMINISTIC",
            "ROLE_CHANGE_VS_DETERMINISTIC",
            "SIDE_FACE_FROM_STIRRUP_SYNTAX",
        ):
            if extra == "TYPE_CHANGE_VS_DETERMINISTIC" and "type" not in conflict_fields:
                conflict_fields.append("type")
            if extra == "ROLE_CHANGE_VS_DETERMINISTIC" and "role" not in conflict_fields:
                conflict_fields.append("role")

    operational = classify_operational(
        deterministic=deterministic,
        vision=vision if validation_ok else None,
        validation_ok=validation_ok,
        conflict_fields=conflict_fields,
    )

    gt = ground_truth or {"available": False}
    evaluation = None
    if gt.get("available"):
        evaluation = evaluate_against_ground_truth(
            validated=vision if validation_ok else None,
            validation_ok=validation_ok,
            ground_truth=gt,
            api_ok=api_ok,
            evidence_weak=(candidate.get("p2523_completeness") not in (None, "PASS"))
            or (candidate.get("semantic_class") == "SIDE_FACE"),
        )

    comparison_class, action = apply_gt_overlay(
        operational_class=operational,
        evaluation=evaluation,
    )
    promo = promotion_eligible_flag(
        comparison_class=comparison_class,
        operational_class=operational,
        validation_ok=validation_ok,
        safety=safety,
    )
    hypo = hypothetical_impact(
        deterministic=deterministic,
        vision=vision if validation_ok else None,
        conflict_fields=conflict_fields,
        comparison_class=comparison_class,
    )
    reasons = eligibility_reasons(
        candidate=candidate,
        deterministic=deterministic,
        mode=eligibility_mode,
    )
    v_status = vision_status_label(vision, validation_ok, api_ok)
    shadow = build_shadow_integration_result(
        candidate=candidate,
        deterministic=deterministic,
        vision=vision,
        vision_status=v_status,
        validation=validation,
        operational_class=operational,
        comparison_class=comparison_class,
        arbitration_action=action,
        conflict_fields=conflict_fields,
        conflict_details=conflict_details,
        safety=safety,
        evaluation=evaluation,
        promotion_eligible=promo,
        shadow_trigger_reason=reasons,
        vision_source=str(vision_obs.get("vision_source") or ""),
        hypothetical=hypo,
        evidence_fingerprint=vision_obs.get("evidence_fingerprint"),
        prompt_fingerprint=vision_obs.get("prompt_fingerprint"),
    )
    return {
        "shadow": shadow,
        "deterministic": deterministic,
        "vision_obs": vision_obs,
        "operational_class": operational,
        "comparison_class": comparison_class,
        "arbitration_action": action,
        "conflict_fields": conflict_fields,
        "promotion_eligible": promo,
        "hypothetical": hypo,
        "safety": safety,
        "evaluation": evaluation,
        "shadow_trigger_reason": reasons,
        "production_write": False,
    }


__all__ = ["integrate_one"]
