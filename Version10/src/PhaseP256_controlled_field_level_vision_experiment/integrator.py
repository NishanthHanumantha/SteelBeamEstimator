"""Compose P2.5.5 snapshot/observer with P2.5.6 field-level arbitration."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PhaseP255_controlled_shadow_integration.integrator import integrate_one

from .field_arbitrator import candidate_decision, compare_fields, summarize_fields
from .field_contract import build_field_level_result


def evaluate_one(
    *,
    candidate: Dict[str, Any],
    deterministic: Dict[str, Any],
    vision_obs: Dict[str, Any],
    ground_truth: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    p255 = integrate_one(
        candidate=candidate,
        deterministic=deterministic,
        vision_obs=vision_obs,
        ground_truth=ground_truth,
    )
    validation = vision_obs.get("validation") or {"valid": False, "errors": [], "warnings": []}
    vision = vision_obs.get("validated_interpretation")
    schema_valid = bool(validation.get("valid")) and vision is not None
    text = str(candidate.get("raw_text") or deterministic.get("raw_text") or "")
    comparisons = compare_fields(
        deterministic=deterministic,
        vision=vision if schema_valid else None,
        annotation_text=text,
        schema_valid=schema_valid,
    )
    summary = summarize_fields(comparisons)
    decision = candidate_decision(summary)
    result = build_field_level_result(
        candidate=candidate,
        deterministic=deterministic,
        vision=vision if schema_valid else None,
        field_comparisons=comparisons,
        summary=summary,
        final_shadow_decision=decision,
        vision_source=str(vision_obs.get("vision_source") or ""),
        p255_operational_class=p255.get("operational_class"),
        evidence_fingerprint=vision_obs.get("evidence_fingerprint"),
        prompt_fingerprint=vision_obs.get("prompt_fingerprint"),
        shadow_trigger_reason=p255.get("shadow_trigger_reason"),
    )
    return {
        "field_result": result,
        "p255": p255,
        "deterministic": deterministic,
        "vision_obs": vision_obs,
        "field_comparisons": comparisons,
        "accepted_shadow_fields": summary.get("accepted_shadow_fields") or [],
        "rejected_shadow_fields": summary.get("rejected_shadow_fields") or [],
        "conflict_fields": summary.get("conflict_fields") or [],
        "final_shadow_decision": decision,
        "production_write": False,
    }


__all__ = ["evaluate_one"]
