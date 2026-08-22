"""Deterministic-only spacer calculation. Vision is not responsible."""
from __future__ import annotations

from typing import Any, Dict, List

from .engineering_adapter import numeric_cut, weight_kg


def calculate_spacers(spacers: Dict[str, Any]) -> Dict[str, Any]:
    spacers = spacers if isinstance(spacers, dict) else {}
    groups_out: List[Dict[str, Any]] = []
    total = 0.0
    by_dia: Dict[str, float] = {}
    for g in spacers.get("groups") or []:
        if not isinstance(g, dict):
            continue
        dia = g.get("diameter")
        qty = g.get("bar_count")
        raw = g.get("raw") if isinstance(g.get("raw"), dict) else {}
        if raw.get("piece_count") not in (None, ""):
            try:
                qty = int(raw.get("piece_count"))
            except (TypeError, ValueError):
                pass
        cut = numeric_cut(g.get("cut_length_mm"))
        try:
            dia_f = float(dia) if dia is not None else None
            qty_i = int(qty) if qty is not None else 0
        except (TypeError, ValueError):
            dia_f, qty_i = None, 0
        w = weight_kg(dia_f, cut, qty_i) if dia_f and cut and qty_i else None
        row = {
            "group_id": g.get("physical_group_id"),
            "diameter_mm": dia_f,
            "quantity": qty_i,
            "cut_length_mm": cut,
            "weight_kg": w,
            "source": "DETERMINISTIC",
        }
        groups_out.append(row)
        if w is not None:
            total += w
            key = f"Y{int(dia_f)}"
            by_dia[key] = round(by_dia.get(key, 0.0) + w, 4)
    return {
        "source": spacers.get("source") or "DETERMINISTIC",
        "authority": "DETERMINISTIC_ENGINEERING",
        "vision_matched": False,
        "group_count": len(groups_out),
        "groups": groups_out,
        "weight_kg": round(total, 4),
        "weight_by_diameter": by_dia,
        "reason": "SPACER_DETERMINISTIC_ONLY",
    }


__all__ = ["calculate_spacers"]
