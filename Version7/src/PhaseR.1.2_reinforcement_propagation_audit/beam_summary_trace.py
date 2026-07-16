"""Beam summary / Excel trace per beam."""
from __future__ import annotations
from typing import Any, Dict, List

from .reinforcement_model_reader import ReinforcementModelReader


class BeamSummaryTrace:

    def trace(self, reader: ReinforcementModelReader) -> Dict[str, Any]:
        traces: List[Dict[str, Any]] = []
        excel_loaded = reader._loaded.get("excel")
        excel_exists = bool(excel_loaded and excel_loaded.get("exists"))

        for beam_id in reader.beam_ids():
            steel = reader.steel_beam(beam_id)
            weight = float(steel.get("total_weight_kg") or 0)
            bar_count = len(steel.get("bar_weights") or [])
            bbs_rows = reader.bbs_rows_for_beam(beam_id)
            traces.append({
                "beam_id": beam_id,
                "beam_exists_in_workbook": excel_exists,
                "bars_shown": bar_count,
                "steel_shown_kg": round(weight, 3),
                "zero_weight_beam": weight == 0,
                "bbs_rows": len(bbs_rows),
                "reason": (
                    "NO_L2_BARS — benchmark-only reference classification"
                    if weight == 0 and bar_count == 0 else
                    "FULLY_PROPAGATED" if weight > 0 else
                    "UNKNOWN"
                ),
            })
        return {
            "phase": "V.B.1 Excel / Beam Summary",
            "module": "estimator_excel_generator.py",
            "workbook_path": (
                excel_loaded.get("path") if excel_loaded else None
            ),
            "beams": traces,
            "beams_with_steel_in_excel": sum(
                1 for t in traces if t["steel_shown_kg"] > 0
            ),
        }
