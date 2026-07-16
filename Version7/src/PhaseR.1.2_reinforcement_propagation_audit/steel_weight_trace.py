"""Steel weight trace — bars entering vs producing weight."""
from __future__ import annotations
from typing import Any, Dict, List

from .reinforcement_model_reader import ReinforcementModelReader


class SteelWeightTrace:

    def trace(self, reader: ReinforcementModelReader) -> Dict[str, Any]:
        traces: List[Dict[str, Any]] = []
        for beam_id in reader.beam_ids():
            l2 = reader.l2_model(beam_id)
            entering, _ = reader.count_l2_bars(l2)
            steel = reader.steel_beam(beam_id)
            bar_weights = steel.get("bar_weights") or []
            producing = len(bar_weights)
            weight = float(steel.get("total_weight_kg") or 0)
            skipped = max(0, entering - producing)
            traces.append({
                "beam_id": beam_id,
                "bars_entering_calculation": entering,
                "bars_producing_weight": producing,
                "bars_skipped": skipped,
                "weight_by_diameter": steel.get("weight_by_diameter") or {},
                "total_weight_kg": round(weight, 3),
                "skipped_reason": (
                    "NO_L2_BARS" if entering == 0 else
                    "STEEL_SKIPPED" if skipped > 0 else
                    "NONE"
                ),
            })
        return {
            "phase": "V.B.1 Steel Weight Completion",
            "module": "steel_weight_completion.py",
            "function": "SteelWeightCompletion.compute()",
            "input_source": "PhaseL.2/beam_reinforcement_models.json",
            "beams": traces,
            "beams_with_steel_weight": sum(
                1 for t in traces if t["total_weight_kg"] > 0
            ),
            "total_steel_kg": round(
                sum(t["total_weight_kg"] for t in traces), 3
            ),
        }
