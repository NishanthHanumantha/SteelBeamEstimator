"""Authority / provenance audit. D.4 must not overwrite valid Vision fields."""
from __future__ import annotations

from typing import Any, Dict, List


def audit_beam(*, bound: Dict[str, Any], hybrid_calc: Dict[str, Any]) -> Dict[str, Any]:
    dia_ok = True
    role_ok = True
    count_ok = True
    spacer_ok = (hybrid_calc.get("spacers") or {}).get("source") == "DETERMINISTIC"
    stirrup_ok = (hybrid_calc.get("stirrups") or {}).get("engineering_calculation_authority") == "DETERMINISTIC_ENGINEERING"
    stirrup_no_vis_qty = (hybrid_calc.get("stirrups") or {}).get("quantities_from_vision") is False
    longest = True
    amb_forced = False
    src_groups = {str(g.get("group_id")): g for g in (bound.get("groups") or []) if isinstance(g, dict)}
    for g in hybrid_calc.get("groups") or []:
        src = src_groups.get(str(g.get("group_id"))) or {}
        sem = src.get("semantic") if isinstance(src.get("semantic"), dict) else {}
        recs = sem.get("field_records") if isinstance(sem.get("field_records"), dict) else {}
        dia = recs.get("diameter") if isinstance(recs.get("diameter"), dict) else {}
        role = recs.get("role") if isinstance(recs.get("role"), dict) else {}
        cnt = recs.get("bar_count") if isinstance(recs.get("bar_count"), dict) else {}
        if dia.get("source") == "VISION" and g.get("diameter_mm") != dia.get("value") and g.get("status") == "CALCULATED":
            dia_ok = False
        if role.get("source") == "VISION" and g.get("role") != role.get("value") and g.get("status") == "CALCULATED":
            role_ok = False
        if cnt.get("source") == "VISION" and g.get("bar_count") != cnt.get("value") and g.get("status") == "CALCULATED":
            count_ok = False
        if (sem.get("longer_bar_likely_main_hook") or "ARCHITECTURE_HOOK_ONLY") != "ARCHITECTURE_HOOK_ONLY":
            longest = False
        if g.get("ambiguous") and g.get("status") == "CALCULATED":
            amb_forced = True
    return {
        "beam_id": hybrid_calc.get("beam_id"),
        "vision_diameter_preserved": dia_ok,
        "vision_role_preserved": role_ok,
        "vision_bar_count_preserved": count_ok,
        "spacer_deterministic": spacer_ok,
        "stirrup_split": stirrup_ok and stirrup_no_vis_qty,
        "no_longest_bar_main_override": longest,
        "ambiguous_not_force_resolved": not amb_forced,
    }


def audit_population(bound_beams: List[Dict[str, Any]], hybrids: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {str(b.get("beam_id")): b for b in bound_beams}
    rows = [audit_beam(bound=by_id.get(str(h.get("beam_id"))) or {}, hybrid_calc=h) for h in hybrids]
    ok = all(
        r.get("vision_diameter_preserved")
        and r.get("vision_role_preserved")
        and r.get("spacer_deterministic")
        and r.get("stirrup_split")
        and r.get("ambiguous_not_force_resolved")
        for r in rows
    ) if rows else False
    return {"ok": ok, "beams": rows}


__all__ = ["audit_beam", "audit_population"]
