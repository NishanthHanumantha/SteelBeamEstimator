"""Shadow-only engineering/schema validation of Claude semantic interpretations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import (
    BEAM_ASSOCIATIONS,
    ROLES,
    SEMANTIC_TYPES,
    STATUS_INSUFFICIENT,
    STATUS_RESOLVED,
    ZONES,
)
from .semantic_schema import ALLOWED_STATUSES

MODEL_VERSION = "10.8.0"


def _as_number(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def validate_interpretation(
    *,
    parsed: Dict[str, Any],
    expected_candidate_id: str,
) -> Dict[str, Any]:
    """Reject unsafe/invalid responses — do not silently repair or inject values."""
    errors: List[str] = []
    warnings: List[str] = []

    if parsed.get("candidate_id") != expected_candidate_id:
        errors.append("CANDIDATE_ID_MISMATCH")

    status = parsed.get("interpretation_status")
    if status not in ALLOWED_STATUSES:
        errors.append("INVALID_INTERPRETATION_STATUS")

    stype = parsed.get("semantic_type")
    if stype not in SEMANTIC_TYPES:
        errors.append("INVALID_SEMANTIC_TYPE")

    role = parsed.get("role")
    if role not in ROLES:
        errors.append("INVALID_ROLE")

    assoc = parsed.get("beam_association")
    if assoc not in BEAM_ASSOCIATIONS:
        errors.append("INVALID_BEAM_ASSOCIATION")

    zone = parsed.get("zone")
    if zone not in ZONES:
        errors.append("INVALID_ZONE")

    qty = parsed.get("quantity")
    dia = _as_number(parsed.get("diameter_mm"))
    legs = parsed.get("legs")
    spacings = parsed.get("spacing_mm") or []
    conf = parsed.get("confidence")

    if conf is not None:
        cnum = _as_number(conf)
        if cnum is None or cnum < 0 or cnum > 1:
            errors.append("INVALID_CONFIDENCE")

    clean_spacings: List[float] = []
    if not isinstance(spacings, list):
        errors.append("SPACING_NOT_LIST")
    else:
        for s in spacings:
            sn = _as_number(s)
            if sn is None or sn <= 0:
                errors.append("INVALID_SPACING_VALUE")
                break
            clean_spacings.append(sn)

    if dia is not None and dia <= 0:
        errors.append("INVALID_DIAMETER")

    if legs is not None:
        try:
            if int(legs) <= 0:
                errors.append("INVALID_LEGS")
        except Exception:
            errors.append("INVALID_LEGS")

    if qty is not None:
        try:
            if int(qty) <= 0:
                errors.append("INVALID_QUANTITY")
        except Exception:
            errors.append("INVALID_QUANTITY")

    if stype == "STIRRUP":
        if qty is not None:
            errors.append("STIRRUP_MUST_NOT_HAVE_LONGITUDINAL_QUANTITY")
        if role not in ("STIRRUP", "UNKNOWN"):
            errors.append("STIRRUP_ROLE_INCONSISTENT")
        if status == STATUS_RESOLVED:
            if dia is None:
                errors.append("STIRRUP_RESOLVED_REQUIRES_DIAMETER")
            if not clean_spacings:
                errors.append("STIRRUP_RESOLVED_REQUIRES_SPACING")
            if legs is None:
                warnings.append("STIRRUP_RESOLVED_MISSING_LEGS")

    if stype == "LONGITUDINAL_BAR":
        if role == "STIRRUP":
            errors.append("LONGITUDINAL_ROLE_INCONSISTENT")
        if status == STATUS_RESOLVED:
            if qty is None:
                errors.append("LONGITUDINAL_RESOLVED_REQUIRES_QUANTITY")
            if dia is None:
                errors.append("LONGITUDINAL_RESOLVED_REQUIRES_DIAMETER")

    if stype == "SIDE_FACE_REINFORCEMENT":
        if role not in ("SIDE_FACE", "UNKNOWN"):
            errors.append("SIDE_FACE_ROLE_INCONSISTENT")

    if stype == "DEVELOPMENT_NOTE" and status == STATUS_RESOLVED and (qty or dia or clean_spacings):
        warnings.append("DEVELOPMENT_NOTE_WITH_NUMERIC_FIELDS")

    if status == STATUS_INSUFFICIENT and stype not in (None, "UNKNOWN") and (
        (stype == "STIRRUP" and dia and clean_spacings)
        or (stype == "LONGITUDINAL_BAR" and qty and dia)
    ):
        warnings.append("ABSTENTION_WITH_DETAILED_VALUES")

    valid = len(errors) == 0
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings + list(parsed.get("warnings") or []),
        "validated_interpretation": parsed if valid else None,
    }


__all__ = ["validate_interpretation"]
