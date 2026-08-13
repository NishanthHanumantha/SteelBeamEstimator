"""ShadowIntegrationResult — audit artefact. Not a production reinforcement object."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import (
    MODEL_VERSION,
    PHASE_ID,
    PRODUCTION_WRITE,
    SHADOW_OBJECT_KIND,
    ZONE_PROMOTABLE,
)


def build_shadow_integration_result(
    *,
    candidate: Dict[str, Any],
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    vision_status: str,
    validation: Dict[str, Any],
    operational_class: str,
    comparison_class: str,
    arbitration_action: str,
    conflict_fields: List[str],
    conflict_details: Dict[str, Any],
    safety: Dict[str, Any],
    evaluation: Optional[Dict[str, Any]],
    promotion_eligible: bool,
    shadow_trigger_reason: List[str],
    vision_source: str,
    hypothetical: Dict[str, Any],
    evidence_fingerprint: Optional[str] = None,
    prompt_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    vis = vision or {}
    return {
        "object_kind": SHADOW_OBJECT_KIND,
        "production_write": PRODUCTION_WRITE,
        "engineering_authority": "DETERMINISTIC_ENGINE",
        "claude_authority": "SHADOW_OBSERVER",
        "zone_promotable": ZONE_PROMOTABLE,
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "annotation_text": candidate.get("raw_text"),
        "deterministic_result": deterministic.get("deterministic_result"),
        "deterministic_status": deterministic.get("deterministic_status"),
        "deterministic_type": deterministic.get("deterministic_type"),
        "deterministic_role": deterministic.get("deterministic_role"),
        "deterministic_diameter": deterministic.get("deterministic_diameter"),
        "deterministic_quantity": deterministic.get("deterministic_quantity"),
        "deterministic_legs": deterministic.get("deterministic_legs"),
        "deterministic_spacing": deterministic.get("deterministic_spacing"),
        "deterministic_association": deterministic.get("deterministic_association"),
        "deterministic_zone": deterministic.get("deterministic_zone"),
        "vision_result": vision,
        "vision_status": vision_status,
        "vision_type": vis.get("semantic_type"),
        "vision_role": vis.get("role"),
        "vision_diameter": vis.get("diameter_mm"),
        "vision_quantity": vis.get("quantity"),
        "vision_legs": vis.get("legs"),
        "vision_spacing": vis.get("spacing_mm"),
        "vision_association": vis.get("beam_association"),
        "vision_zone": vis.get("zone"),
        "vision_confidence": vis.get("confidence"),
        "vision_evidence_basis": vis.get("evidence_basis"),
        "vision_source": vision_source,
        "comparison_class": comparison_class,
        "operational_class": operational_class,
        "arbitration_action": arbitration_action,
        "conflict_flags": {"fields": conflict_fields, "details": conflict_details},
        "validation_result": {
            "valid": validation.get("valid"),
            "errors": validation.get("errors") or [],
            "warnings": validation.get("warnings") or [],
        },
        "safety": safety,
        "promotion_eligible": bool(promotion_eligible),
        "final_shadow_decision": arbitration_action,
        "shadow_trigger_reason": list(shadow_trigger_reason or []),
        "evaluation": evaluation,
        "hypothetical_impact": hypothetical,
        "evidence_fingerprint": evidence_fingerprint,
        "prompt_fingerprint": prompt_fingerprint,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def assert_shadow_not_production(obj: Dict[str, Any]) -> bool:
    return (
        obj.get("object_kind") == SHADOW_OBJECT_KIND
        and obj.get("production_write") is False
        and obj.get("engineering_authority") == "DETERMINISTIC_ENGINE"
        and obj.get("zone_promotable") is False
        and obj.get("promotion_eligible") in (True, False)
    )


__all__ = ["assert_shadow_not_production", "build_shadow_integration_result"]
