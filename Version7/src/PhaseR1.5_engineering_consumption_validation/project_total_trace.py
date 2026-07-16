"""Project total consumption trace — READ-ONLY."""
from __future__ import annotations
from typing import Any, Dict

from .engineering_bar_loader import EngineeringBarLoader


class ProjectTotalTrace:

    def trace(
        self,
        loader: EngineeringBarLoader,
        steel_traces: Dict[str, Any],
    ) -> Dict[str, Any]:
        eng_total = sum(
            (st.weight_kg or 0)
            for st in steel_traces.values()
            if st.consumed and st.skip_reason != "DUPLICATE_EXPANSION"
        )
        json_total = loader.steel_summary_json.get("total_weight_kg", 0)
        comp_total = 0.0
        if loader.steel_summary_computed:
            comp_total = loader.steel_summary_computed.total_weight_kg

        eng_totals = loader.engineering_totals
        report_steel = (
            loader.production_report.get("sections", {})
            .get("3_steel_summary", {})
            .get("total_weight_kg", 0)
        )

        return {
            "engineering_trace_total_kg": round(eng_total, 3),
            "steel_json_total_kg": json_total,
            "steel_computed_total_kg": round(comp_total, 3),
            "engineering_totals_json_kg": eng_totals.get("total_steel_kg", 0),
            "production_report_kg": report_steel,
            "delta_computed_vs_json_kg": round(comp_total - json_total, 3),
            "internal_match": abs(comp_total - eng_total) < 1.0,
            "json_match": abs(comp_total - json_total) < 1.0,
            "match": abs(comp_total - eng_total) < 1.0,
            "total_engineering_bars": len(loader.traces),
            "consumed_bars": sum(1 for st in steel_traces.values() if st.consumed),
        }
