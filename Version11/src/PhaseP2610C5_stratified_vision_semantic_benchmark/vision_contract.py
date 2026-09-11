"""Fail-closed C.5 Vision schema. Physical groups first. No production fields from Claude."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP253_claude_vision_interpretation_pilot.response_schema import extract_json_object

from .config import (
    ALLOWED_LAYERS,
    ALLOWED_LENGTH,
    ALLOWED_ROLE_HYPOTHESES,
    ALLOWED_SCOPES,
    FORBIDDEN_CLAUDE_FIELDS,
    PRODUCTION_ACTION,
    SCHEMA_VERSION,
    SHADOW_ONLY,
)
from .normalize import map_layer, parse_bar_count

SEMANTIC_UNUSABLE = "SEMANTIC_UNUSABLE"
RESPONSE_OK = "OK"
LAYER_ALIASES = {"SIDE": "SIDE_FACE", "SPACER": "OTHER", "STIRRUP": "OTHER"}
ALLOWED_LAYER_INPUT = ALLOWED_LAYERS + tuple(LAYER_ALIASES.keys()) + (
    "SUPPORT_TOP_ZONE",
    "SUPPORT_BOTTOM_ZONE",
)


def _norm(v: Any) -> str:
    return str(v or "").strip().upper()


def _layer(v: Any) -> str:
    raw = _norm(v)
    raw = LAYER_ALIASES.get(raw, raw)
    mapped = map_layer(raw)
    return mapped if mapped in ALLOWED_LAYERS else raw


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
    groups = obj.get("groups")
    if groups is None:
        groups = obj.get("reinforcement_groups")
    if groups is None:
        groups = []
    if not isinstance(groups, list):
        errors.append("groups_not_list")
        groups = []
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            errors.append(f"group_{i}_not_object")
            continue
        raw_layer = _norm(g.get("layer"))
        layer = _layer(g.get("layer"))
        role = _norm(g.get("role_hypothesis") or g.get("role") or "UNKNOWN")
        scope = _norm(g.get("support_scope") or "UNKNOWN")
        length = _norm(g.get("relative_length_evidence") or "UNKNOWN")
        span = _norm(g.get("span_relationship") or "UNKNOWN")
        if raw_layer and raw_layer not in ALLOWED_LAYER_INPUT:
            errors.append(f"unknown_layer:{raw_layer}")
        elif layer and layer not in ALLOWED_LAYERS:
            errors.append(f"unknown_layer:{layer}")
        if role and role not in ALLOWED_ROLE_HYPOTHESES:
            errors.append(f"unknown_role_hypothesis:{role}")
        if scope and scope not in ALLOWED_SCOPES:
            errors.append(f"unknown_support_scope:{scope}")
        if length and length not in ALLOWED_LENGTH:
            errors.append(f"unknown_relative_length:{length}")
        if span and span not in ALLOWED_SCOPES:
            errors.append(f"unknown_span_relationship:{span}")
        if (g.get("spec") in (None, "")) and (g.get("specification") in (None, "")):
            errors.append(f"group_{i}_missing_spec")
    stirrups = obj.get("stirrups")
    if stirrups is None:
        stirrups = []
    if not isinstance(stirrups, list):
        errors.append("stirrups_not_list")
    return len(errors) == 0, errors


def normalize_valid_payload(obj: Dict[str, Any], *, requested_beam_id: str) -> Dict[str, Any]:
    raw_groups = obj.get("groups")
    if raw_groups is None:
        raw_groups = obj.get("reinforcement_groups") or []
    groups = []
    for i, g in enumerate(raw_groups or []):
        if not isinstance(g, dict):
            continue
        spec = str(g.get("spec") or g.get("specification") or "").strip()
        gid = str(g.get("physical_group_id") or f"G{i+1}")
        groups.append(
            {
                "physical_group_id": gid,
                "layer": _layer(g.get("layer")) or "UNKNOWN",
                "spec": spec,
                "bar_count": g.get("bar_count") if g.get("bar_count") not in (None, "") else parse_bar_count(spec),
                "role_hypothesis": _norm(g.get("role_hypothesis") or g.get("role") or "UNKNOWN") or "UNKNOWN",
                "role_confidence": g.get("role_confidence"),
                "support_scope": _norm(g.get("support_scope") or "UNKNOWN") or "UNKNOWN",
                "relative_length_evidence": _norm(g.get("relative_length_evidence") or "UNKNOWN") or "UNKNOWN",
                "span_relationship": _norm(g.get("span_relationship") or "UNKNOWN") or "UNKNOWN",
                "confidence": g.get("confidence"),
                "evidence": g.get("evidence"),
            }
        )
    stirrups = []
    for s in obj.get("stirrups") or []:
        if isinstance(s, dict):
            stirrups.append(
                {
                    "spec": str(s.get("spec") or s.get("specification") or "").strip(),
                    "confidence": s.get("confidence"),
                    "evidence": s.get("evidence"),
                }
            )
    identified = obj.get("target_identified")
    if identified is None:
        identified = obj.get("target_beam_identified")
    conf = obj.get("association_confidence")
    if conf is None:
        conf = obj.get("target_association_confidence")
    neighbour = obj.get("neighbour_evidence_detected")
    if neighbour is None:
        neighbour = obj.get("neighbor_evidence_detected")
    return {
        "target_beam_id": requested_beam_id,
        "target_identified": bool(identified),
        "association_confidence": conf,
        "groups": groups,
        "stirrups": stirrups,
        "ambiguities": list(obj.get("ambiguities") or obj.get("uncertainties") or []),
        "neighbour_evidence_detected": bool(neighbour),
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
        rec["call_status"] = "SCHEMA_INVALID"
        return rec
    out = normalize_valid_payload(obj, requested_beam_id=requested_beam_id)
    out["call_status"] = "OK"
    return out


def unusable(reason: str, *, call_status: str = "SEMANTIC_UNUSABLE") -> Dict[str, Any]:
    return {
        "usable": False,
        "unusable_reason": reason,
        "response_status": SEMANTIC_UNUSABLE,
        "call_status": call_status,
        "groups": [],
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
