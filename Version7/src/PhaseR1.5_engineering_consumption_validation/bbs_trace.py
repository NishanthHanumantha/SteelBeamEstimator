"""BBS consumption trace — READ-ONLY."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .engineering_bar_loader import EngineeringBarLoader
from .engineering_consumption_models import BBSConsumptionTrace, EngineeringBarTrace
from .steel_weight_trace import SteelWeightTrace


class BBSTrace:

    def trace(
        self,
        loader: EngineeringBarLoader,
        steel_traces: Dict[str, Any],
    ) -> Dict[str, BBSConsumptionTrace]:
        bbs_rows = loader.bbs_rows_computed or []
        eng_rows = [
            (i, r) for i, r in enumerate(bbs_rows) if not r.is_beam_header
        ]
        consumed_row_indices: set = set()
        results: Dict[str, BBSConsumptionTrace] = {}

        for trace in loader.traces:
            st = steel_traces.get(trace.trace_id)
            if not st or not st.consumed:
                results[trace.trace_id] = BBSConsumptionTrace(
                    trace_id=trace.trace_id,
                    consumed=False,
                    skip_reason="BBS_SKIPPED: steel not consumed",
                )
                continue

            match = self._find_bbs_row(trace, st, eng_rows, consumed_row_indices)
            if match:
                row_idx, row = match
                consumed_row_indices.add(row_idx)
                results[trace.trace_id] = BBSConsumptionTrace(
                    trace_id=trace.trace_id,
                    consumed=True,
                    row_index=row_idx,
                    description=row.description,
                    diameter_mm=row.diameter_mm,
                    quantity=row.quantity,
                    cut_length_m=row.cut_length_m,
                    weight_kg=row.total_weight_kg,
                )
            else:
                extra = self._find_stirrup_bbs_rows(trace, eng_rows)
                if extra:
                    results[trace.trace_id] = BBSConsumptionTrace(
                        trace_id=trace.trace_id,
                        consumed=True,
                        row_index=extra[0],
                        description=f"STIRRUP zones ({len(extra)} rows)",
                        diameter_mm=trace.diameter_mm,
                        quantity=trace.quantity,
                        skip_reason="MULTIPLE_COUNTING",
                    )
                else:
                    results[trace.trace_id] = BBSConsumptionTrace(
                        trace_id=trace.trace_id,
                        consumed=False,
                        skip_reason="BBS_SKIPPED: no matching row",
                    )

        return results

    def _find_bbs_row(
        self,
        trace: EngineeringBarTrace,
        steel: Any,
        eng_rows: List,
        consumed: set,
    ) -> Optional[tuple]:
        for idx, row in eng_rows:
            if idx in consumed:
                continue
            if row.beam_id != trace.beam_id:
                continue
            if abs(float(row.diameter_mm or 0) - trace.diameter_mm) > 0.1:
                continue
            if steel.weight_kg and row.total_weight_kg:
                if abs(row.total_weight_kg - steel.weight_kg) < 0.5:
                    return idx, row
            if int(row.quantity or 0) == trace.quantity:
                return idx, row
        return None

    def _find_stirrup_bbs_rows(self, trace: EngineeringBarTrace, eng_rows: List) -> List[int]:
        if trace.steel_role != "STIRRUP":
            return []
        return [
            idx for idx, row in eng_rows
            if row.beam_id == trace.beam_id
            and "Stirrup" in str(row.description)
            and abs(float(row.diameter_mm or 0) - trace.diameter_mm) < 0.1
        ]
