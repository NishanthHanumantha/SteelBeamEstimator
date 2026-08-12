"""Local engineering/schema validation of Claude interpretations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import (
    REINFORCEMENT_TYPES,
    STATUS_CONFLICT,
    STATUS_INSUFFICIENT,
    STATUS_PARTIAL,
    STATUS_RESOLVED,
)
from .response_schema import ALLOWED_STATUSES

MODEL_VERSION = "10.7.0"


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
    """
    Validate Claude JSON. Reject unsafe/invalid responses — do not silently repair.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if parsed.get("candidate_id") != expected_candidate_id:
        errors.append("CANDIDATE_ID_MISMATCH")

    status = parsed.get("interpretation_status")
    if status not in ALLOWED_STATUSES:
        errors.append("INVALID_INTERPRETATION_STATUS")

    rtype = parsed.get("reinforcement_type")
    if rtype not in REINFORCEMENT_TYPES:
        errors.append("INVALID_REINFORCEMENT_TYPE")

    qty = parsed.get("quantity")
    dia = _as_number(parsed.get("diameter_mm"))
    legs = parsed.get("legs")
    spacings = parsed.get("spacing_mm") or []
    conf = parsed.get("confidence")

    if conf is not None:
        cnum = _as_number(conf)
        if cnum is None or cnum < 0 or cnum > 1:
            errors.append("INVALID_CONFIDENCE")

    # Spacing validity
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
            li = int(legs)
            if li <= 0:
                errors.append("INVALID_LEGS")
        except Exception:
            errors.append("INVALID_LEGS")

    if qty is not None:
        try:
            qi = int(qty)
            if qi <= 0:
                errors.append("INVALID_QUANTITY")
        except Exception:
            errors.append("INVALID_QUANTITY")

    # Semantic consistency
    if rtype == "STIRRUP":
        if qty is not None:
            errors.append("STIRRUP_MUST_NOT_HAVE_LONGITUDINAL_QUANTITY")
        if status == STATUS_RESOLVED:
            if dia is None:
                errors.append("STIRRUP_RESOLVED_REQUIRES_DIAMETER")
            if not clean_spacings:
                errors.append("STIRRUP_RESOLVED_REQUIRES_SPACING")
            if legs is None:
                warnings.append("STIRRUP_RESOLVED_MISSING_LEGS")

    if rtype == "LONGITUDINAL_BAR":
        if status == STATUS_RESOLVED:
            if qty is None:
                errors.append("LONGITUDINAL_RESOLVED_REQUIRES_QUANTITY")
            if dia is None:
                errors.append("LONGITUDINAL_RESOLVED_REQUIRES_DIAMETER")
            if clean_spacings:
                warnings.append("LONGITUDINAL_UNEXPECTED_SPACING")

    if status in (STATUS_INSUFFICIENT, STATUS_CONFLICT):
        # Abstention/conflict should not assert full engineering values as resolved certainty
        if status == STATUS_INSUFFICIENT and (
            (rtype == "STIRRUP" and dia and clean_spacings and legs)
            or (rtype == "LONGITUDINAL_BAR" and qty and dia)
        ):
            warnings.append("ABSTENTION_WITH_DETAILED_VALUES")

    if status == STATUS_PARTIAL:
        # Must have at least some content
        if rtype in (None, "UNKNOWN") and qty is None and dia is None and not clean_spacings:
            warnings.append("PARTIAL_WITHOUT_CONTENT")

    valid = len(errors) == 0
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings + list(parsed.get("warnings") or []),
        "validated_interpretation": parsed if valid else None,
    }


__all__ = ["validate_interpretation"]
