"""Strict Claude JSON contract. Fail closed. No production fields."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP253_claude_vision_interpretation_pilot.response_schema import extract_json_object

from .config import (
    ALLOWED_LAYERS,
    ALLOWED_ROLES,
    ALLOWED_SCOPES,
    FORBIDDEN_CLAUDE_FIELDS,
    PRODUCTION_ACTION,
    SCHEMA_VERSION,
    SHADOW_ONLY,
)

SEMANTIC_UNUSABLE = "SEMANTIC_UNUSABLE"
RESPONSE_OK = "OK"


def _norm(v: Any) -> str:
    return str(v or "").strip().upper()


def validate_claude_payload(obj: Dict[str, Any], *, requested_beam_id: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(obj, dict):
        return False, ["json_not_object"]
    for key in obj.keys():
        if str(key) in FORBIDDEN_CLAUDE_FIELDS or str(key).lower() in {x.lower() for x in FORBIDDEN_CLAUDE_FIELDS}:
            errors.append(f"forbidden_field:{key}")
    tid = obj.get("target_beam_id")
    if not tid:
        errors.append("missing_target_beam_id")
    elif str(tid) != str(requested_beam_id):
        errors.append("target_beam_id_mismatch")
    groups = obj.get("reinforcement_groups")
    if groups is None:
        groups = []
    if not isinstance(groups, list):
        errors.append("reinforcement_groups_not_list")
        groups = []
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            errors.append(f"group_{i}_not_object")
            continue
        layer = _norm(g.get("layer"))
        role = _norm(g.get("role"))
        scope = _norm(g.get("support_scope") or "UNKNOWN")
        if layer and layer not in ALLOWED_LAYERS:
            errors.append(f"unknown_layer:{layer}")
        if role and role not in ALLOWED_ROLES:
            errors.append(f"unknown_role:{role}")
        if scope and scope not in ALLOWED_SCOPES:
            errors.append(f"unknown_support_scope:{scope}")
        if g.get("spec") in (None, ""):
            errors.append(f"group_{i}_missing_spec")
    stirrups = obj.get("stirrups")
    if stirrups is None:
        stirrups = []
    if not isinstance(stirrups, list):
        errors.append("stirrups_not_list")
    return len(errors) == 0, errors


def normalize_valid_payload(obj: Dict[str, Any], *, requested_beam_id: str) -> Dict[str, Any]:
    groups = []
    for g in obj.get("reinforcement_groups") or []:
        if not isinstance(g, dict):
            continue
        groups.append(
            {
                "layer": _norm(g.get("layer")) or "UNKNOWN",
                "role": _norm(g.get("role")) or "UNKNOWN",
                "spec": str(g.get("spec") or "").strip(),
                "support_scope": _norm(g.get("support_scope") or "UNKNOWN") or "UNKNOWN",
                "confidence": g.get("confidence"),
                "evidence": g.get("evidence"),
            }
        )
    stirrups = []
    for s in obj.get("stirrups") or []:
        if isinstance(s, dict):
            stirrups.append({"spec": str(s.get("spec") or "").strip(), "confidence": s.get("confidence")})
    visual = obj.get("visual_assessment") if isinstance(obj.get("visual_assessment"), dict) else {}
    return {
        "target_beam_id": requested_beam_id,
        "target_beam_identified": bool(obj.get("target_beam_identified")),
        "target_association_confidence": obj.get("target_association_confidence"),
        "visual_assessment": visual,
        "reinforcement_groups": groups,
        "stirrups": stirrups,
        "uncertainties": list(obj.get("uncertainties") or []),
        "neighbor_evidence_detected": bool(obj.get("neighbor_evidence_detected")),
        "response_status": str(obj.get("response_status") or RESPONSE_OK),
        "schema_version": SCHEMA_VERSION,
        "production_action": PRODUCTION_ACTION,
        "shadow_only": SHADOW_ONLY,
        "usable": True,
        "unusable_reason": None,
    }


def parse_and_validate(raw_text: Optional[str], *, requested_beam_id: str) -> Dict[str, Any]:
    if not raw_text or not str(raw_text).strip():
        return unusable("empty_response")
    obj, err = extract_json_object(raw_text)
    if err or obj is None:
        return unusable(err or "json_parse_error")
    ok, errors = validate_claude_payload(obj, requested_beam_id=requested_beam_id)
    if not ok:
        rec = unusable(";".join(errors))
        rec["raw_object_keys"] = sorted(obj.keys())
        return rec
    return normalize_valid_payload(obj, requested_beam_id=requested_beam_id)


def unusable(reason: str) -> Dict[str, Any]:
    return {
        "usable": False,
        "unusable_reason": reason,
        "response_status": SEMANTIC_UNUSABLE,
        "reinforcement_groups": [],
        "stirrups": [],
        "production_action": PRODUCTION_ACTION,
        "shadow_only": SHADOW_ONLY,
        "schema_version": SCHEMA_VERSION,
    }


__all__ = [
    "SEMANTIC_UNUSABLE",
    "normalize_valid_payload",
    "parse_and_validate",
    "unusable",
    "validate_claude_payload",
]
