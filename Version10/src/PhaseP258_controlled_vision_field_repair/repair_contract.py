"""VisionFieldRepairCandidate — auditable, never a production object."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_WRITE


def build_repair_candidate(
    *,
    candidate_id: str,
    beam_id: str,
    annotation_id: str,
    annotation_text: str,
    field_name: str,
    deterministic_value: Any,
    deterministic_status: str,
    vision_value: Any,
    vision_status: str,
    trigger_reason: List[str],
    validation_status: str,
    validation_rules_passed: bool,
    ground_truth_value: Any,
    ground_truth_status: str,
    promotion_class: str,
    promotion_decision: str,
    source_model: Optional[str],
    prompt_version: str,
    schema_version: str,
    evidence_fingerprint: Optional[str],
    reason: str,
) -> Dict[str, Any]:
    return {
        "object_kind": "VisionFieldRepairCandidate",
        "production_write": PRODUCTION_WRITE,
        "production_mutation": False,
        "promotion_level_max": "CONTROLLED_RECOMPUTE",
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "candidate_id": candidate_id,
        "beam_id": beam_id,
        "annotation_id": annotation_id,
        "annotation_text": annotation_text,
        "field_name": field_name,
        "deterministic_value": deterministic_value,
        "deterministic_status": deterministic_status,
        "vision_value": vision_value,
        "vision_status": vision_status,
        "trigger_reason": list(trigger_reason or []),
        "validation_status": validation_status,
        "validation_rules_passed": bool(validation_rules_passed),
        "ground_truth_value": ground_truth_value,
        "ground_truth_status": ground_truth_status,
        "promotion_class": promotion_class,
        "promotion_decision": promotion_decision,
        "source": "VISION" if promotion_decision == "CONTROLLED_RECOMPUTE" else "DETERMINISTIC",
        "original_value": deterministic_value,
        "promoted_value": vision_value if promotion_decision == "CONTROLLED_RECOMPUTE" else deterministic_value,
        "reason": reason,
        "source_model": source_model,
        "prompt_version": prompt_version,
        "schema_version": schema_version,
        "evidence_fingerprint": evidence_fingerprint,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


__all__ = ["build_repair_candidate"]
