"""Quantity comparison and loss detection — READ-ONLY."""
from __future__ import annotations
from typing import Any, Dict, List

from .engineering_bar_loader import EngineeringBarLoader
from .engineering_consumption_models import ConsumptionMatrixRow


ROOT_CAUSES = {
    "UNSUPPORTED_ROLE": "UNSUPPORTED_ROLE",
    "ROLE_MAPPING_ERROR": "ROLE_MAPPING_ERROR",
    "Zero quantity": "CUT_LENGTH_SKIPPED",
    "No mapping in production model": "STEEL_SKIPPED",
    "Filtered by steel module": "STEEL_SKIPPED",
    "Missing geometry": "STEEL_SKIPPED",
    "BBS_SKIPPED": "BBS_SKIPPED",
    "MULTIPLE_COUNTING": "MULTIPLE_COUNTING",
    "DIAMETER_NOT_COUNTED": "DIAMETER_NOT_COUNTED",
    "BEAM_TOTAL_ERROR": "BEAM_TOTAL_ERROR",
    "PROJECT_TOTAL_ERROR": "PROJECT_TOTAL_ERROR",
    "DUPLICATE_CONSUMPTION": "DUPLICATE_CONSUMPTION",
}


class QuantityComparator:

    def build_matrix(
        self,
        loader: EngineeringBarLoader,
        steel_traces: Dict[str, Any],
        bbs_traces: Dict[str, Any],
        dia_trace: Dict[str, Any],
        beam_trace: Dict[str, Any],
        project_trace: Dict[str, Any],
        excel_trace: Dict[str, Any],
    ) -> List[ConsumptionMatrixRow]:
        dia_contrib = dia_trace.get("trace_contributions", {})
        beam_map = {b["beam_id"]: b for b in beam_trace.get("beams", [])}
        project_ok = project_trace.get("match", False)
        excel_ok = excel_trace.get("pipeline_consistency", {}).get("workbook_exists", False)

        matrix: List[ConsumptionMatrixRow] = []
        for trace in loader.traces:
            st = steel_traces.get(trace.trace_id)
            bt = bbs_traces.get(trace.trace_id)
            steel_yes = st and st.consumed
            bbs_yes = bt and bt.consumed
            dia_yes = dia_contrib.get(trace.trace_id, False)
            beam_rec = beam_map.get(trace.beam_id, {})
            beam_yes = steel_yes and beam_rec.get("match", True)
            root = self._classify_root_cause(trace, st, bt, dia_yes, beam_rec, project_ok)

            matrix.append(ConsumptionMatrixRow(
                trace_id=trace.trace_id,
                beam_id=trace.beam_id,
                bar_role=trace.bar_role,
                diameter_mm=trace.diameter_mm,
                quantity=trace.quantity,
                steel="YES" if steel_yes else "NO",
                bbs="YES" if bbs_yes else "NO",
                diameter_summary="YES" if dia_yes else "NO",
                beam_total="YES" if beam_yes else "NO",
                project_total="YES" if project_ok and steel_yes else "NO",
                excel="YES" if excel_ok and bbs_yes else "NO",
                root_cause=root,
            ))
        return matrix

    def detect_losses(self, matrix: List[ConsumptionMatrixRow]) -> Dict[str, Any]:
        lost_steel = [m for m in matrix if m.steel == "NO"]
        lost_bbs = [m for m in matrix if m.steel == "YES" and m.bbs == "NO"]
        lost_excel = [m for m in matrix if m.bbs == "YES" and m.excel == "NO"]
        duplicated = [m for m in matrix if m.root_cause == "MULTIPLE_COUNTING"]
        dia_mismatch = [m for m in matrix if m.root_cause == "DIAMETER_NOT_COUNTED"]

        return {
            "lost_before_steel": len(lost_steel),
            "lost_before_bbs": len(lost_bbs),
            "lost_before_excel": len(lost_excel),
            "duplicated_or_multi_counted": len(duplicated),
            "diameter_mismatches": len(dia_mismatch),
            "lost_steel_trace_ids": [m.trace_id for m in lost_steel],
            "lost_bbs_trace_ids": [m.trace_id for m in lost_bbs],
        }

    def quantity_validation(
        self,
        loader: EngineeringBarLoader,
        steel_traces: Dict[str, Any],
        dia_trace: Dict[str, Any],
        excel_trace: Dict[str, Any],
    ) -> Dict[str, Any]:
        role_qty_expected: Dict[str, int] = {}
        role_qty_consumed: Dict[str, int] = {}
        for trace in loader.traces:
            role_qty_expected[trace.bar_role] = (
                role_qty_expected.get(trace.bar_role, 0) + trace.quantity
            )
            st = steel_traces.get(trace.trace_id)
            if st and st.consumed:
                role_qty_consumed[trace.bar_role] = (
                    role_qty_consumed.get(trace.bar_role, 0) + trace.quantity
                )

        role_gaps = {
            role: role_qty_expected.get(role, 0) - role_qty_consumed.get(role, 0)
            for role in role_qty_expected
            if role_qty_expected.get(role, 0) != role_qty_consumed.get(role, 0)
        }

        ref_comp = excel_trace.get("reference_comparison", {})
        return {
            "role_quantity_gaps": role_gaps,
            "under_consumed_roles": sorted(role_gaps.keys()),
            "reference_project_delta_kg": ref_comp.get("project_total_delta_kg"),
            "reference_diameter_mismatches": ref_comp.get("diameter_mismatches", []),
            "reference_beam_mismatches": ref_comp.get("beam_mismatches", []),
            "per_diameter_validation": dia_trace.get("per_diameter", []),
        }

    def _classify_root_cause(
        self, trace, st, bt, dia_yes, beam_rec, project_ok
    ) -> str:
        if not st or not st.consumed:
            reason = st.skip_reason if st else "UNKNOWN"
            return ROOT_CAUSES.get(reason, reason or "STEEL_SKIPPED")
        if st.skip_reason == "DUPLICATE_EXPANSION":
            return "DUPLICATE_CONSUMPTION"
        if st.skip_reason == "MULTIPLE_COUNTING":
            return "MULTIPLE_COUNTING"
        if not bt or not bt.consumed:
            return "BBS_SKIPPED"
        if bt.skip_reason == "MULTIPLE_COUNTING":
            return "MULTIPLE_COUNTING"
        if not dia_yes:
            return "DIAMETER_NOT_COUNTED"
        if not beam_rec.get("match", True):
            return "BEAM_TOTAL_ERROR"
        if not project_ok:
            return "PROJECT_TOTAL_ERROR"
        return ""
