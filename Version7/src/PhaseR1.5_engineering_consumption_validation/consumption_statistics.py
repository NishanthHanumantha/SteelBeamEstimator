"""Consumption statistics — dynamically computed."""
from __future__ import annotations
from typing import Any, Dict, List


class ConsumptionStatistics:

    def compute(
        self,
        loader: Any,
        steel_traces: Dict[str, Any],
        bbs_traces: Dict[str, Any],
        matrix: List[Any],
        losses: Dict[str, Any],
        qty_validation: Dict[str, Any],
        validation: Any,
    ) -> Dict[str, Any]:
        total = len(loader.traces)
        consumed = sum(1 for t in steel_traces.values() if t.consumed)
        skipped = total - consumed
        weights = [
            t.weight_kg for t in steel_traces.values()
            if t.consumed and t.weight_kg
        ]

        role_consumption: Dict[str, Dict[str, int]] = {}
        dia_consumption: Dict[str, Dict[str, int]] = {}
        for trace in loader.traces:
            st = steel_traces.get(trace.trace_id)
            role = trace.bar_role
            dia = str(int(trace.diameter_mm))
            if role not in role_consumption:
                role_consumption[role] = {"expected": 0, "consumed": 0}
            role_consumption[role]["expected"] += trace.quantity
            if st and st.consumed:
                role_consumption[role]["consumed"] += trace.quantity

            if dia not in dia_consumption:
                dia_consumption[dia] = {"expected": 0, "consumed": 0}
            dia_consumption[dia]["expected"] += trace.quantity
            if st and st.consumed:
                dia_consumption[dia]["consumed"] += trace.quantity

        return {
            "engineering_bars_loaded": total,
            "consumed_bars": consumed,
            "skipped_bars": skipped,
            "duplicate_or_multi_counted": losses.get("duplicated_or_multi_counted", 0),
            "lost_bars": losses.get("lost_before_steel", 0),
            "consumption_pct": validation.consumption_score,
            "average_weight_per_bar_kg": (
                round(sum(weights) / len(weights), 3) if weights else 0
            ),
            "role_consumption": role_consumption,
            "diameter_consumption": dia_consumption,
            "pipeline_consumption_score": validation.consumption_score,
            "engineering_accuracy_score": validation.engineering_accuracy_score,
            "reach_steel": consumed,
            "reach_bbs": sum(1 for t in bbs_traces.values() if t.consumed),
            "reach_diameter_summary": sum(
                1 for m in matrix if m.diameter_summary == "YES"
            ),
            "reach_beam_total": sum(1 for m in matrix if m.beam_total == "YES"),
            "reach_project_total": sum(1 for m in matrix if m.project_total == "YES"),
            "reach_excel": sum(1 for m in matrix if m.excel == "YES"),
            "under_consumed_roles": qty_validation.get("under_consumed_roles", []),
        }
