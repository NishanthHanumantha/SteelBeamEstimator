"""BBS trace — expected vs actual rows per beam."""
from __future__ import annotations
from typing import Any, Dict, List

from .reinforcement_model_reader import ReinforcementModelReader


class BBSTrace:

    def trace(self, reader: ReinforcementModelReader) -> Dict[str, Any]:
        traces: List[Dict[str, Any]] = []
        for beam_id in reader.beam_ids():
            steel = reader.steel_beam(beam_id)
            expected = len(steel.get("bar_weights") or [])
            rows = reader.bbs_rows_for_beam(beam_id)
            eng_rows = [
                r for r in rows
                if not r.get("is_beam_header") and (
                    r.get("total_weight_kg") or r.get("quantity")
                )
            ]
            actual = len(eng_rows)
            traces.append({
                "beam_id": beam_id,
                "expected_bbs_rows": expected,
                "actual_bbs_rows": actual,
                "total_rows_including_headers": len(rows),
                "missing_rows": max(0, expected - actual),
                "missing_categories": (
                    [] if actual >= expected else ["engineering rows not generated"]
                ),
            })
        return {
            "phase": "V.B.1 BBS Completion",
            "module": "bbs_completion_engine.py",
            "function": "BBSCompletionEngine.generate()",
            "beams": traces,
            "total_bbs_engineering_rows": sum(t["actual_bbs_rows"] for t in traces),
        }
