"""Hard safety gates — Vision may never become production authority."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Generic multi-leg + spacing syntax (stirrup-like), not SFR wording.
_STIRRUP_SYNTAX_RE = re.compile(
    r"\d+\s*L\s*-?\s*Y\s*\d+.*@",
    re.IGNORECASE,
)
_EXPLICIT_LONGITUDINAL_RE = re.compile(
    r"(?<![A-Z0-9])(\d+)\s*-?\s*Y\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def annotation_has_explicit_quantity(text: str) -> bool:
    t = text or ""
    if _STIRRUP_SYNTAX_RE.search(t):
        return False
    return bool(_EXPLICIT_LONGITUDINAL_RE.search(t))


def apply_safety_gates(
    *,
    annotation_text: str,
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    validation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Flag unsafe Vision interpretations. Never repair them into production values.
    Invalid schema is a Vision failure, not a patched interpretation.
    """
    flags: List[str] = []
    errors: List[str] = []

    if not validation.get("valid") or vision is None:
        errors.append("INVALID_OR_MISSING_VISION_SCHEMA")
        return {
            "ok": False,
            "flags": flags,
            "errors": errors + list(validation.get("errors") or []),
            "vision_rejected": True,
            "zone_promotable": False,
            "production_write": False,
        }

    stype = vision.get("semantic_type")
    role = vision.get("role")
    qty = vision.get("quantity")
    text = annotation_text or ""

    if qty is not None and not annotation_has_explicit_quantity(text):
        flags.append("INVENTED_QUANTITY")
        errors.append("VISION_INVENTED_QUANTITY")

    if stype == "STIRRUP" and qty is not None:
        flags.append("STIRRUP_LONGITUDINAL_QUANTITY")
        errors.append("STIRRUP_MUST_NOT_BECOME_LONGITUDINAL_QUANTITY")

    if stype == "SIDE_FACE_REINFORCEMENT" and _STIRRUP_SYNTAX_RE.search(text):
        flags.append("SIDE_FACE_FROM_STIRRUP_SYNTAX")
        errors.append("SFR_NOT_FROM_GENERIC_MULTI_LEG_SPACING")

    det_type = deterministic.get("deterministic_type")
    det_role = deterministic.get("deterministic_role")
    det_type_ok = det_type not in (None, "", "UNKNOWN")
    det_role_ok = det_role not in (None, "", "UNKNOWN")
    if det_type_ok and stype not in (None, "UNKNOWN") and stype != det_type:
        if not (
            {stype, det_type} <= {"SIDE_FACE_REINFORCEMENT", "SIDE_FACE"}
            or {stype, det_type} <= {"SUPPORT_REINFORCEMENT", "LONGITUDINAL_BAR"}
        ):
            flags.append("TYPE_CHANGE_VS_DETERMINISTIC")
    if det_role_ok and role not in (None, "UNKNOWN") and role != det_role:
        if not (
            {role, det_role} <= {"SIDE_FACE", "SIDE_FACE_REINFORCEMENT"}
            or {role, det_role} <= {"SUPPORT_TOP", "TOP_BAR"}
            or {role, det_role} <= {"SUPPORT_BOTTOM", "BOTTOM_BAR"}
        ):
            flags.append("ROLE_CHANGE_VS_DETERMINISTIC")

    zone = vision.get("zone")
    if zone not in (None, "UNKNOWN"):
        flags.append("ZONE_DIAGNOSTIC_ONLY")

    rejected = any(
        f in flags
        for f in (
            "INVENTED_QUANTITY",
            "STIRRUP_LONGITUDINAL_QUANTITY",
            "SIDE_FACE_FROM_STIRRUP_SYNTAX",
        )
    )

    return {
        "ok": not rejected,
        "flags": flags,
        "errors": errors,
        "vision_rejected": rejected,
        "zone_promotable": False,
        "production_write": False,
    }


def assert_no_production_mutation(
    before: Any,
    after: Any,
    label: str,
) -> Tuple[bool, str]:
    if before != after:
        return False, f"{label}_MUTATED"
    return True, f"{label}_UNCHANGED"


__all__ = [
    "annotation_has_explicit_quantity",
    "apply_safety_gates",
    "assert_no_production_mutation",
]
