"""
comparison_reporter.py — Before/after comparison for Phase R.1.1B.
MODEL_VERSION: 8.2.1
"""
from __future__ import annotations

from typing import Any, Dict

R11B_BASELINE = {
    "phase": "R.1.3 (pre R.1.1A)",
    "beams_with_bars": 7,
    "total_bars": 46,
    "beams_reaching_steel": 7,
    "total_steel_kg": 1481.795,
    "reinforcement_source": "EngineeringBarModel_R1.3 (old R.1 data)",
}


class ComparisonReporter:

    def compare(
        self,
        r13_result: Dict[str, Any],
        production_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        before = dict(R11B_BASELINE)
        after = {
            "phase": "R.1.1B (R.1.1A + R.1.3 re-run)",
            "beams_with_bars": r13_result.get("beams_with_bars", 0),
            "total_bars": r13_result.get("total_bars", 0),
            "beams_reaching_steel": production_result.get("beams_reaching_steel", 0),
            "total_steel_kg": round(production_result.get("total_steel_kg", 0.0), 3),
            "reinforcement_source": production_result.get("reinforcement_source", "EngineeringBarModel_R1.3"),
        }
        delta = {
            "beams_with_bars_delta": after["beams_with_bars"] - before["beams_with_bars"],
            "total_bars_delta": after["total_bars"] - before["total_bars"],
            "beams_reaching_steel_delta": after["beams_reaching_steel"] - before["beams_reaching_steel"],
            "steel_kg_delta": round(after["total_steel_kg"] - before["total_steel_kg"], 3),
        }
        return {"before": before, "after": after, "delta": delta}
