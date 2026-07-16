"""Diameter summary consumption trace — READ-ONLY."""
from __future__ import annotations
from typing import Any, Dict, List

from .engineering_bar_loader import EngineeringBarLoader
from .engineering_consumption_models import EngineeringBarTrace


class DiameterSummaryTrace:

    def trace(
        self,
        loader: EngineeringBarLoader,
        steel_traces: Dict[str, Any],
    ) -> Dict[str, Any]:
        eng_qty_by_dia: Dict[int, int] = {}
        eng_weight_by_dia: Dict[int, float] = {}
        dia_contrib: Dict[str, bool] = {}

        for trace in loader.traces:
            st = steel_traces.get(trace.trace_id)
            dia = int(trace.diameter_mm)
            if st and st.consumed:
                eng_qty_by_dia[dia] = eng_qty_by_dia.get(dia, 0) + trace.quantity
                eng_weight_by_dia[dia] = eng_weight_by_dia.get(dia, 0) + (st.weight_kg or 0)
                dia_contrib[trace.trace_id] = True
            else:
                dia_contrib[trace.trace_id] = False

        json_summary = loader.steel_summary_json.get("diameter_summary", [])
        json_by_dia = {int(d["diameter_mm"]): d for d in json_summary}

        computed_by_dia: Dict[int, Dict[str, float]] = {}
        if loader.steel_summary_computed:
            for ds in loader.steel_summary_computed.diameter_summary:
                computed_by_dia[ds.diameter_mm] = {
                    "total_bars": ds.total_bars,
                    "total_weight_kg": ds.total_weight_kg,
                }

        per_diameter: List[Dict[str, Any]] = []
        all_dias = sorted(set(eng_qty_by_dia) | set(json_by_dia) | set(computed_by_dia))
        for dia in all_dias:
            js = json_by_dia.get(dia, {})
            cs = computed_by_dia.get(dia, {})
            per_diameter.append({
                "diameter_mm": dia,
                "engineering_bar_qty": eng_qty_by_dia.get(dia, 0),
                "steel_json_bars": js.get("total_bars", 0),
                "steel_computed_bars": cs.get("total_bars", 0),
                "steel_json_weight_kg": js.get("total_weight_kg", 0),
                "steel_computed_weight_kg": cs.get("total_weight_kg", 0),
                "bars_match": js.get("total_bars", 0) == cs.get("total_bars", 0),
                "weight_delta_kg": round(
                    (cs.get("total_weight_kg", 0) or 0) - (js.get("total_weight_kg", 0) or 0), 3
                ),
            })

        traced_count = sum(1 for v in dia_contrib.values() if v)
        return {
            "per_diameter": per_diameter,
            "trace_contributions": dia_contrib,
            "bars_contributing": traced_count,
            "bars_total": len(loader.traces),
        }
