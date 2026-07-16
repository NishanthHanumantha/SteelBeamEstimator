"""Engineering bar trace — L.2 bar lists per beam."""
from __future__ import annotations
from typing import Any, Dict, List

from .propagation_models import BENCHMARK_BEAMS, L2_BAR_KEYS
from .reinforcement_model_reader import ReinforcementModelReader


class EngineeringBarTrace:

    def trace(self, reader: ReinforcementModelReader) -> Dict[str, Any]:
        traces: List[Dict[str, Any]] = []
        for beam_id in reader.beam_ids():
            l2 = reader.l2_model(beam_id)
            bar_count, roles = reader.count_l2_bars(l2)
            is_benchmark = beam_id in BENCHMARK_BEAMS
            traces.append({
                "beam_id": beam_id,
                "is_benchmark_beam": is_benchmark,
                "is_reference_anchored": l2.get("is_benchmark_beam", is_benchmark),
                "bars_entering_steel_weight": bar_count,
                "roles": roles,
                "total_classified_bars": l2.get("total_classified_bars", bar_count),
                "unclassified_bar_count": l2.get("unclassified_bar_count", 0),
                "classification_complete": l2.get("classification_complete", False),
                "discarded_bars": 0,
                "source": (
                    "REFERENCE_CLASSIFICATION" if is_benchmark else
                    "NONE — no L.2 bar data"
                ),
            })
        return {
            "phase": "L.2 Engineering Interpretation",
            "module": "bar_role_classifier.py",
            "function": "BarRoleClassifier.classify() / REFERENCE_CLASSIFICATION",
            "benchmark_beams": sorted(BENCHMARK_BEAMS),
            "beams": traces,
            "beams_with_engineering_bars": sum(
                1 for t in traces if t["bars_entering_steel_weight"] > 0
            ),
        }
