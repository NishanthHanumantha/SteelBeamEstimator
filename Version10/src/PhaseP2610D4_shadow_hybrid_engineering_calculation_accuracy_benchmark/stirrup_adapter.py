"""Deterministic stirrup engineering. Vision owns identification only; no Vision quantities."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .engineering_adapter import derive_cut_length_mm, numeric_cut, weight_kg


def _stirrup_objects(model: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(model, dict):
        return []
    raw = model.get("stirrups")
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        items = raw.get("items") or raw.get("groups") or []
        return [x for x in items if isinstance(x, dict)]
    return []


def calculate_stirrups(
    *,
    vision_items: List[Dict[str, Any]],
    model: Optional[Dict[str, Any]],
    geometry: Dict[str, Any],
) -> Dict[str, Any]:
    objects = _stirrup_objects(model)
    width = geometry.get("width_mm")
    depth = geometry.get("depth_mm")
    span = geometry.get("span_mm") or 0.0
    rows = []
    total = 0.0
    by_dia: Dict[str, float] = {}
    for item in objects:
        dia = item.get("diameter_mm") or item.get("diameter")
        qty = item.get("quantity") or item.get("count") or item.get("bar_count")
        cut = numeric_cut(item.get("cut_length_mm"))
        try:
            dia_f = float(dia) if dia is not None else None
            qty_i = int(qty) if qty is not None else 0
        except (TypeError, ValueError):
            dia_f, qty_i = None, 0
        if dia_f is None or qty_i <= 0:
            continue
        if cut is None:
            bind_cuts = []
            for vis in vision_items or []:
                bind = vis.get("engineering_binding") if isinstance(vis.get("engineering_binding"), dict) else {}
                ref = bind.get("stirrup_engineering_reference") if isinstance(bind.get("stirrup_engineering_reference"), dict) else {}
                inst = ref.get("existing_instance") if isinstance(ref.get("existing_instance"), dict) else {}
                bound_cut = numeric_cut(inst.get("cut_length_mm"))
                if bound_cut:
                    bind_cuts.append(bound_cut)
            if bind_cuts:
                cut = bind_cuts[0]
            else:
                cut, _src = derive_cut_length_mm(
                    role="STIRRUP",
                    diameter_mm=dia_f,
                    span_mm=float(span or 0.0),
                    depth_mm=float(depth) if depth is not None else None,
                    width_mm=float(width) if width is not None else None,
                    provided_cut_mm=None,
                )
        w = weight_kg(dia_f, cut, qty_i)
        rows.append(
            {
                "diameter_mm": dia_f,
                "quantity": qty_i,
                "cut_length_mm": cut,
                "weight_kg": w,
                "source": "DETERMINISTIC",
                "vision_quantity_used": False,
            }
        )
        if w is not None:
            total += w
            key = f"Y{int(dia_f)}"
            by_dia[key] = round(by_dia.get(key, 0.0) + w, 4)

    conflicts = []
    for vis in vision_items or []:
        ident = vis.get("semantic_identification") if isinstance(vis.get("semantic_identification"), dict) else {}
        if ident.get("conflict_detected"):
            conflicts.append(
                {
                    "code": "STIRRUP_SEMANTIC_CONFLICT",
                    "vision_value": ident.get("vision_value"),
                    "deterministic_value": ident.get("deterministic_value"),
                    "resolution": "DETERMINISTIC_ENGINEERING_CALCULATION_RETAINED",
                }
            )
    return {
        "semantic_identification_authority": "VISION_PREFERRED",
        "engineering_calculation_authority": "DETERMINISTIC_ENGINEERING",
        "vision_items": [
            {
                "origin": v.get("origin"),
                "identification": (v.get("semantic_identification") or {}).get("value")
                if isinstance(v.get("semantic_identification"), dict)
                else None,
            }
            for v in (vision_items or [])
        ],
        "conflicts": conflicts,
        "calculated_groups": rows,
        "weight_kg": round(total, 4),
        "weight_by_diameter": by_dia,
        "quantities_from_vision": False,
        "reason": "DETERMINISTIC_STIRRUP_ENGINEERING" if rows else "DETERMINISTIC_STIRRUP_UNAVAILABLE",
    }


__all__ = ["calculate_stirrups"]
