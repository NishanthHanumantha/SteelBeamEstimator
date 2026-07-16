"""Beam total consumption trace — READ-ONLY."""
from __future__ import annotations
from typing import Any, Dict, List

from .engineering_bar_loader import EngineeringBarLoader


class BeamTotalTrace:

    def trace(
        self,
        loader: EngineeringBarLoader,
        steel_traces: Dict[str, Any],
    ) -> Dict[str, Any]:
        beam_ids = sorted({t.beam_id for t in loader.traces})
        json_beams = {
            b["beam_id"]: b
            for b in loader.steel_summary_json.get("beam_weights", [])
        }
        computed_beams = {}
        if loader.steel_summary_computed:
            computed_beams = {
                bw.beam_id: bw for bw in loader.steel_summary_computed.beam_weights
            }

        beam_records: List[Dict[str, Any]] = []
        for bid in beam_ids:
            expected_weight = sum(
                (steel_traces.get(t.trace_id).weight_kg or 0)
                for t in loader.traces
                if t.beam_id == bid
                and steel_traces.get(t.trace_id)
                and steel_traces[t.trace_id].consumed
                and steel_traces[t.trace_id].skip_reason != "DUPLICATE_EXPANSION"
            )
            json_w = json_beams.get(bid, {}).get("total_weight_kg", 0)
            comp_bw = computed_beams.get(bid)
            comp_w = comp_bw.total_weight_kg if comp_bw else 0
            internal_match = abs(expected_weight - comp_w) < 1.0
            json_match = abs(comp_w - json_w) < 1.0
            bar_count = sum(
                1 for t in loader.traces
                if t.beam_id == bid
                and steel_traces.get(t.trace_id, {}).consumed
            )
            beam_records.append({
                "beam_id": bid,
                "engineering_bars_consumed": bar_count,
                "expected_weight_from_traces_kg": round(expected_weight, 3),
                "steel_json_weight_kg": json_w,
                "steel_computed_weight_kg": round(comp_w, 3),
                "weight_delta_kg": round(comp_w - json_w, 3),
                "internal_match": internal_match,
                "json_match": json_match,
                "match": internal_match,
            })

        return {
            "beams": beam_records,
            "total_beams": len(beam_records),
            "mismatched_beams": [
                b["beam_id"] for b in beam_records if not b["internal_match"]
            ],
            "json_stale_beams": [
                b["beam_id"] for b in beam_records if not b.get("json_match", True)
            ],
        }
