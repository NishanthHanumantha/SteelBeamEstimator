"""Diagnostic-only: what WOULD change if Vision were naively promoted. Never applied."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


_FIELD_MAP = (
    ("type", "deterministic_type", "semantic_type", "TYPE"),
    ("role", "deterministic_role", "role", "ROLE"),
    ("diameter", "deterministic_diameter", "diameter_mm", "DIAMETER"),
    ("quantity", "deterministic_quantity", "quantity", "QUANTITY"),
    ("legs", "deterministic_legs", "legs", "LEGS"),
    ("spacing", "deterministic_spacing", "spacing_mm", "SPACING"),
    ("beam_association", "deterministic_association", "beam_association", "ASSOCIATION"),
    ("zone", "deterministic_zone", "zone", "ZONE"),
)


def _values_differ(a: Any, b: Any) -> bool:
    if isinstance(a, list) or isinstance(b, list):
        aa = [float(x) for x in (a or [])]
        bb = [float(x) for x in (b or [])]
        return aa != bb
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    try:
        return abs(float(a) - float(b)) > 1e-6
    except Exception:
        return str(a) != str(b)


def hypothetical_impact(
    *,
    deterministic: Dict[str, Any],
    vision: Optional[Dict[str, Any]],
    conflict_fields: List[str],
    comparison_class: str,
) -> Dict[str, Any]:
    changes: List[str] = []
    if vision:
        for key, d_key, v_key, label in _FIELD_MAP:
            if key == "zone":
                continue
            if _values_differ(deterministic.get(d_key), vision.get(v_key)):
                # Ignore Vision UNKNOWN / empty vs populated det for "would change"
                v = vision.get(v_key)
                if v in (None, "UNKNOWN", [], ""):
                    continue
                changes.append(label)

    would = bool(changes) or bool(conflict_fields)
    dangerous = comparison_class in ("VISION_CONFLICT", "VISION_WRONG") or any(
        c in ("TYPE", "ROLE") for c in changes
    )
    return {
        "hypothetical_change": changes,
        "hypothetical_production_impact": "WOULD_CHANGE" if would else "NONE",
        "actual_production_impact": "NONE",
        "dangerous_if_promoted": dangerous,
        "note": "Diagnostic only. Vision was not applied to production objects.",
    }


__all__ = ["hypothetical_impact"]
