"""Build one explicit repaired stirrup notation from promoted fields. Do not merge lists."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _intish(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(round(float(v)))
    except Exception:
        return None


def _spacing_list(v: Any) -> List[int]:
    out: List[int] = []
    for x in v or []:
        n = _intish(x)
        if n is not None:
            out.append(n)
    return out


def selected_interpretation(promoted: List[Dict[str, Any]], *, fallback_text: str) -> Dict[str, Any]:
    """One explicit selected interpretation per annotation from CONTROLLED_RECOMPUTE fields."""
    legs = None
    dia = None
    spacing: List[int] = []
    for rec in promoted:
        if rec.get("promotion_decision") != "CONTROLLED_RECOMPUTE":
            continue
        if rec.get("field_name") == "legs":
            legs = _intish(rec.get("promoted_value"))
        elif rec.get("field_name") == "diameter":
            dia = _intish(rec.get("promoted_value"))
        elif rec.get("field_name") == "spacing":
            spacing = _spacing_list(rec.get("promoted_value"))
    # Fill remaining from original text only when that field was not promoted
    # (keep deterministic confirmed values).
    return {
        "legs": legs,
        "diameter_mm": dia,
        "spacing_mm": spacing,
        "bar_label": format_stirrup_label(legs=legs, diameter_mm=dia, spacing_mm=spacing),
        "fallback_text": fallback_text,
    }


def format_stirrup_label(*, legs: Optional[int], diameter_mm: Optional[int], spacing_mm: List[int]) -> Optional[str]:
    if diameter_mm is None or not spacing_mm:
        return None
    leg_s = f"{legs}L-" if legs else ""
    sp = "/".join(str(s) for s in spacing_mm)
    return f"{leg_s}Y{diameter_mm}@{sp}"


def merge_with_deterministic(interp: Dict[str, Any], det: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    """Confirmed deterministic values fill holes. Never merge spacing lists."""
    legs = interp.get("legs")
    if legs is None:
        legs = _intish(det.get("leg_count"))
    dia = interp.get("diameter_mm")
    if dia is None:
        dia = _intish(det.get("diameter_value_mm"))
    spacing = list(interp.get("spacing_mm") or [])
    if not spacing:
        spacing = _spacing_list(det.get("spacing_values_mm"))
    label = format_stirrup_label(legs=legs, diameter_mm=dia, spacing_mm=spacing)
    return label, {"legs": legs, "diameter_mm": dia, "spacing_mm": spacing, "bar_label": label}


__all__ = ["format_stirrup_label", "merge_with_deterministic", "selected_interpretation"]
