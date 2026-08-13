"""Field-by-field arbitration. Deterministic wins on conflict. Vision never writes production."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP254_semantic_reinforcement_vision_benchmark.baseline_comparator import (
    roles_compatible,
    types_compatible,
)
from PhaseP255_controlled_shadow_integration.safety_gates import (
    annotation_has_explicit_quantity,
)

from .config import (
    DEC_KEEP_DET,
    DEC_KEEP_DET_CONFLICT,
    DEC_NOT_APPLICABLE,
    DEC_SHADOW_CANDIDATE,
    DEC_UNRESOLVED,
    DEC_ZONE_DIAGNOSTIC,
    FIELD_ASSOCIATION,
    FIELD_DIAMETER,
    FIELD_LEGS,
    FIELD_QUANTITY,
    FIELD_ROLE,
    FIELD_SEMANTIC_TYPE,
    FIELD_SPACING,
    FIELD_ZONE,
    FIELDS,
    ST_BOTH_AGREE,
    ST_DETERMINISTIC_ONLY,
    ST_NOT_APPLICABLE,
    ST_UNRESOLVED,
    ST_VISION_CONFLICT,
    ST_VISION_FIELD_CANDIDATE,
    ST_VISION_REJECTED,
    ST_VISION_UNRESOLVED,
    ZONE_CANDIDATE_ALLOWED,
)
from .field_validator import det_present, validate_vision_field, vision_present


def _num_eq(a: Any, b: Any, tol: float = 1e-6) -> bool:
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def _list_eq(a: Any, b: Any) -> bool:
    aa = [float(x) for x in (a or [])]
    bb = [float(x) for x in (b or [])]
    if len(aa) != len(bb):
        return False
    return all(abs(x - y) <= 1e-6 for x, y in zip(aa, bb))


def extract_det_value(deterministic: Dict[str, Any], field: str) -> Any:
    mapping = {
        FIELD_SEMANTIC_TYPE: deterministic.get("deterministic_type"),
        FIELD_ROLE: deterministic.get("deterministic_role"),
        FIELD_DIAMETER: deterministic.get("deterministic_diameter"),
        FIELD_QUANTITY: deterministic.get("deterministic_quantity"),
        FIELD_LEGS: deterministic.get("deterministic_legs"),
        FIELD_SPACING: list(deterministic.get("deterministic_spacing") or []),
        FIELD_ASSOCIATION: deterministic.get("deterministic_association"),
        FIELD_ZONE: deterministic.get("deterministic_zone"),
    }
    return mapping[field]


def extract_vis_value(vision: Optional[Dict[str, Any]], field: str) -> Any:
    if not vision:
        return None
    mapping = {
        FIELD_SEMANTIC_TYPE: vision.get("semantic_type"),
        FIELD_ROLE: vision.get("role"),
        FIELD_DIAMETER: vision.get("diameter_mm"),
        FIELD_QUANTITY: vision.get("quantity"),
        FIELD_LEGS: vision.get("legs"),
        FIELD_SPACING: list(vision.get("spacing_mm") or []),
        FIELD_ASSOCIATION: vision.get("beam_association"),
        FIELD_ZONE: vision.get("zone"),
    }
    return mapping[field]


def values_equivalent(field: str, det: Any, vis: Any) -> bool:
    if field == FIELD_SEMANTIC_TYPE:
        return types_compatible(vis, det) or vis == det
    if field == FIELD_ROLE:
        return vis == det or roles_compatible(vis, det)
    if field in (FIELD_DIAMETER, FIELD_QUANTITY, FIELD_LEGS):
        return _num_eq(det, vis)
    if field == FIELD_SPACING:
        return _list_eq(det, vis)
    return det == vis


def _effective_type(deterministic: Dict[str, Any], vision: Optional[Dict[str, Any]]) -> Optional[str]:
    d = deterministic.get("deterministic_type")
    if d not in (None, "", "UNKNOWN"):
        return d
    if vision:
        v = vision.get("semantic_type")
        if v not in (None, "", "UNKNOWN"):
            return v
    return None


def internal_contradictions(
    *,
    vision: Optional[Dict[str, Any]],
    deterministic: Dict[str, Any],
    annotation_text: str,
) -> Dict[str, List[str]]:
    """Map field → contradiction reasons. Reject only the affected Vision fields."""
    out: Dict[str, List[str]] = {f: [] for f in FIELDS}
    if not vision:
        return out
    v_type = vision.get("semantic_type")
    v_role = vision.get("role")
    v_qty = vision.get("quantity")
    v_legs = vision.get("legs")
    d_type = deterministic.get("deterministic_type")

    if v_type == "STIRRUP" and v_role not in (None, "UNKNOWN", "STIRRUP"):
        out[FIELD_ROLE].append("STIRRUP_ROLE_INCONSISTENT")
    if v_type == "LONGITUDINAL_BAR" and v_role == "STIRRUP":
        out[FIELD_ROLE].append("LONGITUDINAL_ROLE_INCONSISTENT")
    if v_type == "SIDE_FACE_REINFORCEMENT" and v_role not in (None, "UNKNOWN", "SIDE_FACE"):
        out[FIELD_ROLE].append("SIDE_FACE_ROLE_INCONSISTENT")
    if v_type == "LONGITUDINAL_BAR" and v_legs is not None:
        out[FIELD_LEGS].append("LONGITUDINAL_MUST_NOT_HAVE_STIRRUP_LEGS")
    if v_type == "STIRRUP" and v_qty is not None:
        out[FIELD_QUANTITY].append("STIRRUP_MUST_NOT_HAVE_LONGITUDINAL_QUANTITY")
    if d_type == "STIRRUP" and v_qty is not None:
        out[FIELD_QUANTITY].append("STIRRUP_QUANTITY_NOT_DERIVABLE_FROM_NOTATION")
    if d_type == "LONGITUDINAL_BAR" and v_legs is not None:
        out[FIELD_LEGS].append("LONGITUDINAL_MUST_NOT_HAVE_STIRRUP_LEGS")
    if v_type == "STIRRUP" and not annotation_has_explicit_quantity(annotation_text) and v_qty is not None:
        out[FIELD_QUANTITY].append("INVENTED_STIRRUP_QUANTITY")
    return out


def arbitrate_field(
    *,
    field: str,
    det_value: Any,
    vis_value: Any,
    vis_ok: bool,
    vis_errors: List[str],
    applicable: bool,
    contradictions: List[str],
) -> Dict[str, Any]:
    d_known = det_present(det_value, field=field)
    v_known = vision_present(vis_value, field=field)

    if field == FIELD_ZONE:
        status = ST_BOTH_AGREE if d_known and v_known and values_equivalent(field, det_value, vis_value) else (
            ST_VISION_CONFLICT if d_known and v_known else (
                ST_VISION_UNRESOLVED if d_known and not v_known else (
                    ST_UNRESOLVED if not v_known else "VISION_DIAGNOSTIC"
                )
            )
        )
        if d_known and v_known and not values_equivalent(field, det_value, vis_value):
            status = ST_VISION_CONFLICT
        elif d_known and v_known:
            status = ST_BOTH_AGREE
        elif not d_known and v_known:
            status = "VISION_DIAGNOSTIC"
        elif d_known and not v_known:
            status = ST_DETERMINISTIC_ONLY
        else:
            status = ST_UNRESOLVED
        return {
            "field": field,
            "deterministic_value": det_value,
            "vision_value": vis_value,
            "deterministic_known": d_known,
            "vision_known": v_known,
            "field_status": status,
            "field_decision": DEC_ZONE_DIAGNOSTIC,
            "accepted": False,
            "reason": "ZONE_NOT_PROMOTABLE",
            "validation_ok": vis_ok,
            "validation_errors": vis_errors,
            "zone_candidate_allowed": ZONE_CANDIDATE_ALLOWED,
            "hypothetical_change": False,
            "production_change": "NONE",
            "safe": False,
        }

    if not applicable:
        status = ST_NOT_APPLICABLE
        decision = DEC_NOT_APPLICABLE
        if v_known:
            status = ST_VISION_REJECTED
            decision = DEC_KEEP_DET
        return {
            "field": field,
            "deterministic_value": det_value,
            "vision_value": vis_value,
            "deterministic_known": d_known,
            "vision_known": v_known,
            "field_status": status,
            "field_decision": decision,
            "accepted": False,
            "reason": vis_errors[0] if vis_errors else "NOT_APPLICABLE",
            "validation_ok": False,
            "validation_errors": vis_errors,
            "hypothetical_change": False,
            "production_change": "NONE",
            "safe": True,
        }

    if contradictions:
        if d_known:
            status, decision, reason = ST_VISION_REJECTED, DEC_KEEP_DET, contradictions[0]
        else:
            status, decision, reason = ST_UNRESOLVED, DEC_UNRESOLVED, contradictions[0]
        if d_known and v_known:
            status, decision = ST_VISION_CONFLICT, DEC_KEEP_DET_CONFLICT
        return {
            "field": field,
            "deterministic_value": det_value,
            "vision_value": vis_value,
            "deterministic_known": d_known,
            "vision_known": v_known,
            "field_status": status,
            "field_decision": decision,
            "accepted": False,
            "reason": reason,
            "validation_ok": False,
            "validation_errors": vis_errors + contradictions,
            "hypothetical_change": bool(d_known and v_known),
            "production_change": "NONE",
            "safe": False,
        }

    if v_known and not vis_ok:
        if d_known:
            status, decision, reason = ST_VISION_REJECTED, DEC_KEEP_DET, vis_errors[0] if vis_errors else "VISION_INVALID"
        else:
            status, decision, reason = ST_UNRESOLVED, DEC_UNRESOLVED, vis_errors[0] if vis_errors else "VISION_INVALID"
        return {
            "field": field,
            "deterministic_value": det_value,
            "vision_value": vis_value,
            "deterministic_known": d_known,
            "vision_known": v_known,
            "field_status": status,
            "field_decision": decision,
            "accepted": False,
            "reason": reason,
            "validation_ok": False,
            "validation_errors": vis_errors,
            "hypothetical_change": False,
            "production_change": "NONE",
            "safe": True,
        }

    if not v_known:
        if d_known:
            status, decision, reason = ST_DETERMINISTIC_ONLY, DEC_KEEP_DET, "VISION_MISSING"
            # Spec RULE E uses VISION_UNRESOLVED when vision missing
            status = ST_VISION_UNRESOLVED
        else:
            status, decision, reason = ST_UNRESOLVED, DEC_UNRESOLVED, "BOTH_MISSING"
        return {
            "field": field,
            "deterministic_value": det_value,
            "vision_value": vis_value,
            "deterministic_known": d_known,
            "vision_known": False,
            "field_status": status,
            "field_decision": decision,
            "accepted": False,
            "reason": reason,
            "validation_ok": True,
            "validation_errors": [],
            "hypothetical_change": False,
            "production_change": "NONE",
            "safe": True,
        }

    # Vision known and valid
    if d_known:
        if values_equivalent(field, det_value, vis_value):
            return {
                "field": field,
                "deterministic_value": det_value,
                "vision_value": vis_value,
                "deterministic_known": True,
                "vision_known": True,
                "field_status": ST_BOTH_AGREE,
                "field_decision": DEC_KEEP_DET,
                "accepted": False,
                "reason": "EQUIVALENT_VALUES",
                "validation_ok": True,
                "validation_errors": [],
                "hypothetical_change": False,
                "production_change": "NONE",
                "safe": True,
            }
        return {
            "field": field,
            "deterministic_value": det_value,
            "vision_value": vis_value,
            "deterministic_known": True,
            "vision_known": True,
            "field_status": ST_VISION_CONFLICT,
            "field_decision": DEC_KEEP_DET_CONFLICT,
            "accepted": False,
            "reason": "DETERMINISTIC_CONFLICT",
            "validation_ok": True,
            "validation_errors": [],
            "hypothetical_change": True,
            "production_change": "NONE",
            "safe": False,
        }

    # Deterministic unknown, Vision valid → shadow candidate
    return {
        "field": field,
        "deterministic_value": det_value,
        "vision_value": vis_value,
        "deterministic_known": False,
        "vision_known": True,
        "field_status": ST_VISION_FIELD_CANDIDATE,
        "field_decision": DEC_SHADOW_CANDIDATE,
        "accepted": True,
        "reason": "DETERMINISTIC_UNKNOWN_VISION_VALID",
        "validation_ok": True,
        "validation_errors": [],
        "hypothetical_change": True,
        "production_change": "NONE",
        "safe": True,
    }


def compare_fields(
    *,
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    annotation_text: str,
    schema_valid: bool,
) -> Dict[str, Dict[str, Any]]:
    vis = vision if schema_valid else None
    effective = _effective_type(deterministic, vis)
    contr = internal_contradictions(
        vision=vis, deterministic=deterministic, annotation_text=annotation_text
    )
    out: Dict[str, Dict[str, Any]] = {}
    for field in FIELDS:
        det_v = extract_det_value(deterministic, field)
        vis_v = extract_vis_value(vis, field)
        v_known = vision_present(vis_v, field=field)
        if not schema_valid and v_known:
            validation = {"ok": False, "errors": ["INVALID_OR_MISSING_VISION_SCHEMA"], "applicable": True}
        elif v_known:
            validation = validate_vision_field(
                field=field,
                value=vis_v,
                annotation_text=annotation_text,
                effective_type=effective,
            )
        else:
            validation = {"ok": True, "errors": [], "applicable": True}

        rec = arbitrate_field(
            field=field,
            det_value=det_v,
            vis_value=vis_v,
            vis_ok=bool(validation.get("ok")),
            vis_errors=list(validation.get("errors") or []),
            applicable=bool(validation.get("applicable", True)),
            contradictions=contr.get(field) or [],
        )
        if field == FIELD_QUANTITY and effective == "STIRRUP" and not vision_present(vis_v, field=field):
            rec["field_status"] = ST_NOT_APPLICABLE
            rec["field_decision"] = DEC_NOT_APPLICABLE
            rec["reason"] = "STIRRUP_QUANTITY_NOT_DERIVABLE_FROM_NOTATION"
            rec["accepted"] = False
        if field == FIELD_LEGS and effective == "LONGITUDINAL_BAR" and not vision_present(vis_v, field=field):
            rec["field_status"] = ST_NOT_APPLICABLE
            rec["field_decision"] = DEC_NOT_APPLICABLE
            rec["reason"] = "LEGS_NOT_APPLICABLE_FOR_LONGITUDINAL"
            rec["accepted"] = False
        out[field] = rec
    return out


def summarize_fields(comparisons: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    for field, rec in comparisons.items():
        if rec.get("accepted"):
            accepted.append({
                "field": field,
                "value": rec.get("vision_value"),
                "reason": rec.get("reason"),
                "provenance": "CLAUDE_VISION_SHADOW",
            })
        if rec.get("field_status") == ST_VISION_CONFLICT:
            conflicts.append({
                "field": field,
                "reason": rec.get("reason"),
                "deterministic": rec.get("deterministic_value"),
                "vision": rec.get("vision_value"),
            })
        if rec.get("field_status") in (ST_VISION_REJECTED, ST_VISION_CONFLICT) or (
            rec.get("vision_known") and not rec.get("accepted") and rec.get("field_status") != ST_BOTH_AGREE
            and rec.get("field") != FIELD_ZONE
            and rec.get("field_status") not in (ST_VISION_UNRESOLVED, ST_NOT_APPLICABLE, ST_DETERMINISTIC_ONLY, ST_UNRESOLVED, "VISION_DIAGNOSTIC")
        ):
            if rec.get("field_status") in (ST_VISION_REJECTED, ST_VISION_CONFLICT):
                rejected.append({
                    "field": field,
                    "reason": rec.get("reason"),
                    "status": rec.get("field_status"),
                })
    return {
        "accepted_shadow_fields": [a["field"] for a in accepted],
        "accepted_shadow_field_details": accepted,
        "rejected_shadow_fields": [r["field"] for r in rejected],
        "rejected_shadow_field_details": rejected,
        "conflict_fields": [c["field"] for c in conflicts],
        "conflict_field_details": conflicts,
    }


def candidate_decision(summary: Dict[str, Any]) -> str:
    if summary.get("conflict_fields"):
        return DEC_KEEP_DET_CONFLICT
    if summary.get("accepted_shadow_fields"):
        return "KEEP_DETERMINISTIC_WITH_SHADOW_FIELD_CANDIDATES"
    return DEC_KEEP_DET


__all__ = [
    "candidate_decision",
    "compare_fields",
    "extract_det_value",
    "extract_vis_value",
    "summarize_fields",
    "values_equivalent",
]
