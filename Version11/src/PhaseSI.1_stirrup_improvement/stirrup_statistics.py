"""
Stirrup Statistics — Phase SI.1 MODULE 8

Aggregates stirrup computation metrics.
"""
from typing import List, Dict
from stirrup_models import BeamStirrupResult, StirrupType, ZoneRole


def compute_statistics(beam_results: List[BeamStirrupResult]) -> Dict:
    uniform_beams = [b for b in beam_results if b.stirrup_type == StirrupType.UNIFORM]
    variable_beams = [b for b in beam_results if b.stirrup_type == StirrupType.VARIABLE]

    support_zones = 0
    mid_zones = 0
    merged_rows = 0
    eng_rows = 0

    for br in beam_results:
        for g in br.groups:
            eng_rows += 1
            if g.is_merged:
                merged_rows += 1
            for z in g.zones:
                if z.role in (ZoneRole.LEFT_SUPPORT, ZoneRole.RIGHT_SUPPORT):
                    support_zones += 1
                else:
                    mid_zones += 1

    total_qty  = sum(b.total_quantity for b in beam_results)
    total_wt   = sum(b.total_weight_kg for b in beam_results)
    old_wt     = sum(b.old_weight_kg for b in beam_results)

    diam_totals: Dict[int, float] = {}
    for br in beam_results:
        for g in br.groups:
            d = int(g.diameter_mm)
            diam_totals[d] = round(diam_totals.get(d, 0.0) + g.total_weight_kg, 3)

    return {
        "total_beams_with_stirrups": len(beam_results),
        "uniform_stirrup_beams": len(uniform_beams),
        "variable_stirrup_beams": len(variable_beams),
        "total_support_zones": support_zones,
        "total_midspan_zones": mid_zones,
        "total_merged_rows": merged_rows,
        "total_engineering_bbs_rows": eng_rows,
        "total_stirrup_quantity": total_qty,
        "total_stirrup_weight_kg": round(total_wt, 3),
        "old_engine_weight_kg": round(old_wt, 3),
        "weight_change_kg": round(total_wt - old_wt, 3),
        "diameter_totals_kg": {f"Y{d}": w for d, w in sorted(diam_totals.items())},
    }
