"""Consumption statistics for Phase R.2B."""
from __future__ import annotations
from typing import Any, Dict


class EngineeringContextConsumptionStatistics:

    def compute(
        self,
        loader,
        dependency_map: Dict[str, Any],
        production_result: Dict[str, Any],
        execution_time_s: float,
    ) -> Dict[str, Any]:
        summary = loader.summary() if loader else {}
        matrix = dependency_map.get("consumption_matrix", [])
        consumed = sum(1 for m in matrix if m["consumed"])
        return {
            "model_version": "7.6.0",
            "phase": "R.2B",
            "execution_time_s": round(execution_time_s, 3),
            "parameters_consumed": consumed,
            "parameters_total": len(matrix),
            "consumption_rate": dependency_map.get("consumption_rate", "0/0"),
            "consumption_pct": dependency_map.get("consumption_pct", 0),
            "loader_summary": summary,
            "production_steel_weight_kg": production_result.get("steel_weight_kg", 0),
            "production_workbook": production_result.get("workbook_path"),
            "fallback_events": len(loader.fallback_log) if loader else 0,
            "engineering_parameters": {
                "steel_grade": summary.get("primary_steel_grade"),
                "concrete_grade": summary.get("concrete_grade_beam"),
                "cover_mm": summary.get("cover_beam_mm"),
                "dev_length_factor": summary.get("dev_length_factor"),
                "hook_135d": summary.get("hook_multiple_135"),
                "min_lap_mm": summary.get("min_lap_mm"),
                "dl_table_entries": summary.get("dl_table_entries"),
            },
        }
