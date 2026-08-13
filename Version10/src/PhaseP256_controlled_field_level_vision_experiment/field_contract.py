"""FieldLevelShadowResult — audit artefact. Not a production reinforcement object."""
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


def build_field_level_result(
    *,
    candidate: Dict[str, Any],
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    field_comparisons: Dict[str, Any],
    summary: Dict[str, Any],
    final_shadow_decision: str,
    vision_source: str,
    p255_operational_class: Optional[str] = None,
    evidence_fingerprint: Optional[str] = None,
    prompt_fingerprint: Optional[str] = None,
    shadow_trigger_reason: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "object_kind": SHADOW_OBJECT_KIND,
        "production_write": PRODUCTION_WRITE,
        "production_mutation": False,
        "engineering_authority": "DETERMINISTIC_ENGINE",
        "claude_authority": "SHADOW_OBSERVER",
        "zone_promotable": ZONE_PROMOTABLE,
        "zone_candidate_allowed": False,
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "annotation_text": candidate.get("raw_text"),
        "deterministic_result": deterministic.get("deterministic_result"),
        "vision_result": vision,
        "field_comparisons": field_comparisons,
        "accepted_shadow_fields": summary.get("accepted_shadow_fields") or [],
        "accepted_shadow_field_details": summary.get("accepted_shadow_field_details") or [],
        "rejected_shadow_fields": summary.get("rejected_shadow_fields") or [],
        "rejected_shadow_field_details": summary.get("rejected_shadow_field_details") or [],
        "conflict_fields": summary.get("conflict_fields") or [],
        "conflict_field_details": summary.get("conflict_field_details") or [],
        "final_shadow_decision": final_shadow_decision,
        "p255_operational_class": p255_operational_class,
        "vision_source": vision_source,
        "shadow_trigger_reason": list(shadow_trigger_reason or []),
        "evidence_fingerprint": evidence_fingerprint,
        "prompt_fingerprint": prompt_fingerprint,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def assert_field_result_not_production(obj: Dict[str, Any]) -> bool:
    return (
        obj.get("object_kind") == SHADOW_OBJECT_KIND
        and obj.get("production_write") is False
        and obj.get("production_mutation") is False
        and obj.get("zone_promotable") is False
        and obj.get("zone_candidate_allowed") is False
        and obj.get("engineering_authority") == "DETERMINISTIC_ENGINE"
        and "zone" not in (obj.get("accepted_shadow_fields") or [])
    )


__all__ = ["assert_field_result_not_production", "build_field_level_result"]
