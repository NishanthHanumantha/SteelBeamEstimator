"""Beam-level shadow aggregation. No production routing."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    STATUS_AMBIGUOUS,
    STATUS_CALCULATED,
    STATUS_COMPLETE,
    STATUS_GROUP_AMBIGUOUS,
    STATUS_INCOMPATIBLE,
    STATUS_PARTIAL,
)
from .group_calculator import calculate_group
from .spacer_adapter import calculate_spacers
from .stirrup_adapter import calculate_stirrups
from .ambiguity_handler import withheld_rows


def _add_dia(acc: Dict[str, float], dia: Any, kg: float) -> None:
    if dia is None or kg is None:
        return
    key = f"Y{int(float(dia))}"
    acc[key] = round(acc.get(key, 0.0) + float(kg), 4)


def calculate_beam(*, bound: Dict[str, Any], r13_model: Dict[str, Any] = None) -> Dict[str, Any]:
    beam_id = str(bound.get("beam_id") or "")
    geometry = bound.get("geometry") if isinstance(bound.get("geometry"), dict) else {}
    groups_in = [g for g in (bound.get("groups") or []) if isinstance(g, dict)]
    calculated = [calculate_group(g, geometry=geometry) for g in groups_in]
    withheld = withheld_rows(calculated)
    spacers = calculate_spacers(bound.get("spacers") if isinstance(bound.get("spacers"), dict) else {})
    stirrups = calculate_stirrups(
        vision_items=list(bound.get("stirrups") or []),
        model=r13_model,
        geometry=geometry,
    )

    long_kg = 0.0
    by_dia: Dict[str, float] = {}
    n_calc = 0
    n_inc = 0
    n_partial = 0
    n_amb = 0
    for g in calculated:
        st = g.get("status")
        if st == STATUS_CALCULATED and g.get("weight_kg") is not None:
            long_kg += float(g.get("weight_kg") or 0.0)
            _add_dia(by_dia, g.get("diameter_mm"), float(g.get("weight_kg")))
            n_calc += 1
        elif st == STATUS_GROUP_AMBIGUOUS:
            n_amb += 1
        elif st == STATUS_INCOMPATIBLE:
            n_inc += 1
        else:
            n_partial += 1
    spacer_kg = float(spacers.get("weight_kg") or 0.0)
    stirrup_kg = float(stirrups.get("weight_kg") or 0.0)
    for k, v in (spacers.get("weight_by_diameter") or {}).items():
        by_dia[k] = round(by_dia.get(k, 0.0) + float(v), 4)
    for k, v in (stirrups.get("weight_by_diameter") or {}).items():
        by_dia[k] = round(by_dia.get(k, 0.0) + float(v), 4)
    total = round(long_kg + spacer_kg + stirrup_kg, 4)

    if n_inc and not n_calc:
        overall = STATUS_INCOMPATIBLE
        completeness = "INCOMPATIBLE"
    elif n_amb:
        overall = STATUS_AMBIGUOUS
        completeness = "PARTIAL"
    elif n_partial or n_inc:
        overall = STATUS_PARTIAL
        completeness = "PARTIAL"
    else:
        overall = STATUS_COMPLETE
        completeness = "COMPLETE"

    return {
        "beam_id": beam_id,
        "status": overall,
        "completeness": completeness,
        "groups": calculated,
        "withheld_ambiguous": withheld,
        "spacers": spacers,
        "stirrups": stirrups,
        "longitudinal_weight_kg": round(long_kg, 4),
        "spacer_weight_kg": round(spacer_kg, 4),
        "stirrup_weight_kg": round(stirrup_kg, 4),
        "hybrid_weight_kg": total,
        "weight_by_diameter": by_dia,
        "group_counts": {
            "total": len(calculated),
            "calculated": n_calc,
            "ambiguous_withheld": n_amb,
            "partial": n_partial,
            "incompatible": n_inc,
        },
        "possible_duplicates_unmerged": sum(1 for g in calculated if g.get("possible_duplicate")),
        "calculations_performed": {
            "cut_length": True,
            "development_length": True,
            "steel_weight": True,
            "bbs": False,
            "workbook": False,
        },
    }


def calculate_population(bound_beams: List[Dict[str, Any]], catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for bound in bound_beams:
        if not isinstance(bound, dict):
            continue
        bid = str(bound.get("beam_id") or "")
        rows.append(calculate_beam(bound=bound, r13_model=(catalog or {}).get(bid)))
    rows.sort(key=lambda r: str(r.get("beam_id") or ""))
    return rows


__all__ = ["calculate_beam", "calculate_population"]
