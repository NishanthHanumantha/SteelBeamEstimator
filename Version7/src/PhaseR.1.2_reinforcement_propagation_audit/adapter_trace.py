"""Adapter trace — R.1 groups vs R.1.1 adapted L.2 bars."""
from __future__ import annotations
from typing import Any, Dict, List

from .reinforcement_model_reader import ReinforcementModelReader


class AdapterTrace:

    def trace(self, reader: ReinforcementModelReader) -> Dict[str, Any]:
        traces: List[Dict[str, Any]] = []
        for beam_id in reader.beam_ids():
            r1 = reader.r1_model(beam_id)
            gc, qty, roles = reader.count_r1_groups(r1)
            adapter = reader.adapter_model(beam_id)
            adapter_bars, adapter_roles = reader.count_l2_bars(adapter)
            rejected = max(0, qty - adapter_bars) if adapter_bars < qty else 0
            traces.append({
                "beam_id": beam_id,
                "groups_entered": gc,
                "group_total_quantity": qty,
                "r1_roles": roles,
                "engineering_bars_produced": adapter_bars,
                "adapter_roles": adapter_roles,
                "bars_rejected": rejected,
                "rejection_reason": (
                    "NO_REINFORCEMENT" if qty == 0 else
                    "ADAPTER_NOT_RUN" if not adapter and qty > 0 else
                    "LABEL_PARSE_FAILED" if rejected > 0 else
                    "NONE"
                ),
                "adapter_available": bool(adapter),
            })
        return {
            "phase": "R.1.1 Adapter",
            "module": "reinforcement_source_adapter.py",
            "function": "ReinforcementSourceAdapter.adapt()",
            "beams": traces,
            "beams_with_adapter_bars": sum(
                1 for t in traces if t["engineering_bars_produced"] > 0
            ),
        }
