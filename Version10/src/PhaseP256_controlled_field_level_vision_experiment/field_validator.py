"""Validate individual Vision fields. Never repair invalid values into production."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PhaseP254_semantic_reinforcement_vision_benchmark.config import (
    BEAM_ASSOCIATIONS,
    ROLES,
    SEMANTIC_TYPES,
)
from PhaseP255_controlled_shadow_integration.safety_gates import (
    annotation_has_explicit_quantity,
)

# Conventional bar diameters (mm). Not benchmark-specific answers.
_CONVENTIONAL_DIAMETERS_MM = frozenset({6, 8, 10, 12, 16, 20, 25, 28, 32, 36, 40})
_DIAMETER_MIN = 6.0
_DIAMETER_MAX = 40.0
_SPACING_MIN = 20.0
_SPACING_MAX = 600.0
_LEGS_MIN = 1
_LEGS_MAX = 12
_SPACING_MAX_LEN = 6


def _as_number(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


def _as_int(v: Any) -> Optional[int]:
    n = _as_number(v)
    if n is None:
        return None
    if abs(n - round(n)) > 1e-9:
        return None
    return int(round(n))


def vision_present(value: Any, *, field: str) -> bool:
    if field == "spacing":
        return bool(value)
    if field in ("semantic_type", "reinforcement_role", "beam_association", "zone"):
        return value not in (None, "", "UNKNOWN", "UNCERTAIN")
    return value is not None


def det_present(value: Any, *, field: str) -> bool:
    return vision_present(value, field=field)


def validate_diameter(value: Any) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    n = _as_number(value)
    if n is None:
        return False, ["DIAMETER_NOT_NUMERIC"]
    if n <= 0:
        return False, ["DIAMETER_NOT_POSITIVE"]
    if n < _DIAMETER_MIN or n > _DIAMETER_MAX:
        return False, ["DIAMETER_OUT_OF_CONVENTIONAL_RANGE"]
    if abs(n - round(n)) > 1e-9:
        return False, ["DIAMETER_NOT_WHOLE_MM"]
    if int(round(n)) not in _CONVENTIONAL_DIAMETERS_MM:
        return False, ["DIAMETER_NOT_CONVENTIONAL"]
    return True, errors


def validate_legs(value: Any) -> Tuple[bool, List[str]]:
    i = _as_int(value)
    if i is None:
        return False, ["LEGS_NOT_INTEGER"]
    if i < _LEGS_MIN:
        return False, ["LEGS_NOT_POSITIVE"]
    if i > _LEGS_MAX:
        return False, ["LEGS_OUT_OF_RANGE"]
    return True, []


def validate_spacing(value: Any) -> Tuple[bool, List[str]]:
    if value is None:
        return False, ["SPACING_MISSING"]
    if not isinstance(value, list):
        return False, ["SPACING_NOT_LIST"]
    if not value:
        return False, ["SPACING_EMPTY"]
    if len(value) > _SPACING_MAX_LEN:
        return False, ["SPACING_SEQUENCE_TOO_LONG"]
    cleaned: List[float] = []
    for item in value:
        n = _as_number(item)
        if n is None:
            return False, ["SPACING_NOT_NUMERIC"]
        if n <= 0:
            return False, ["SPACING_NOT_POSITIVE"]
        if n < _SPACING_MIN or n > _SPACING_MAX:
            return False, ["SPACING_OUT_OF_RANGE"]
        cleaned.append(n)
    return True, []


def validate_quantity(value: Any) -> Tuple[bool, List[str]]:
    i = _as_int(value)
    if i is None:
        return False, ["QUANTITY_NOT_INTEGER"]
    if i <= 0:
        return False, ["QUANTITY_NOT_POSITIVE"]
    return True, []


def validate_type(value: Any) -> Tuple[bool, List[str]]:
    if value not in SEMANTIC_TYPES or value in (None, "UNKNOWN"):
        return False, ["INVALID_SEMANTIC_TYPE"]
    return True, []


def validate_role(value: Any) -> Tuple[bool, List[str]]:
    if value not in ROLES or value in (None, "UNKNOWN"):
        return False, ["INVALID_ROLE"]
    return True, []


def validate_association(value: Any) -> Tuple[bool, List[str]]:
    if value not in BEAM_ASSOCIATIONS or value in (None, "UNCERTAIN"):
        return False, ["INVALID_BEAM_ASSOCIATION"]
    return True, []


def validate_zone(value: Any) -> Tuple[bool, List[str]]:
    """Zone is diagnostic only — structural check, never promotion."""
    if value in (None, "", "UNKNOWN"):
        return False, ["ZONE_MISSING"]
    if value not in ("SPAN", "SUPPORT", "END", "UNKNOWN"):
        return False, ["INVALID_ZONE"]
    return True, []


def validate_vision_field(
    *,
    field: str,
    value: Any,
    annotation_text: str,
    effective_type: Optional[str],
) -> Dict[str, Any]:
    """
    Return {ok, errors, applicable}.
    Does not invent replacements. Stirrup quantity is never derived from legs/dia/spacing.
    """
    if field == "zone":
        ok, errors = validate_zone(value)
        return {"ok": ok, "errors": errors, "applicable": True, "promotable": False}

    if field == "legs":
        if effective_type == "LONGITUDINAL_BAR":
            return {
                "ok": False,
                "errors": ["LEGS_NOT_APPLICABLE_FOR_LONGITUDINAL"],
                "applicable": False,
                "promotable": False,
            }
        ok, errors = validate_legs(value)
        return {"ok": ok, "errors": errors, "applicable": True, "promotable": ok}

    if field == "quantity":
        if effective_type == "STIRRUP":
            return {
                "ok": False,
                "errors": ["STIRRUP_QUANTITY_NOT_DERIVABLE_FROM_NOTATION"],
                "applicable": False,
                "promotable": False,
            }
        if not annotation_has_explicit_quantity(annotation_text):
            return {
                "ok": False,
                "errors": ["INVENTED_QUANTITY"],
                "applicable": True,
                "promotable": False,
            }
        ok, errors = validate_quantity(value)
        return {"ok": ok, "errors": errors, "applicable": True, "promotable": ok}

    if field == "diameter":
        ok, errors = validate_diameter(value)
        return {"ok": ok, "errors": errors, "applicable": True, "promotable": ok}
    if field == "spacing":
        ok, errors = validate_spacing(value)
        return {"ok": ok, "errors": errors, "applicable": True, "promotable": ok}
    if field == "semantic_type":
        ok, errors = validate_type(value)
        return {"ok": ok, "errors": errors, "applicable": True, "promotable": ok}
    if field == "reinforcement_role":
        ok, errors = validate_role(value)
        return {"ok": ok, "errors": errors, "applicable": True, "promotable": ok}
    if field == "beam_association":
        ok, errors = validate_association(value)
        return {"ok": ok, "errors": errors, "applicable": True, "promotable": ok}

    return {"ok": False, "errors": ["UNKNOWN_FIELD"], "applicable": False, "promotable": False}


__all__ = [
    "det_present",
    "validate_diameter",
    "validate_legs",
    "validate_quantity",
    "validate_spacing",
    "validate_vision_field",
    "vision_present",
]
