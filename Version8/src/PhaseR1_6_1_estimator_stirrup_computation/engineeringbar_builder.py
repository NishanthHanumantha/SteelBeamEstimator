"""
Build stirrup EngineeringBars from computations.
MODEL_VERSION: 8.8.1

One EngineeringBar per zone. Hooks are attributes (already in cut length).
"""
from __future__ import annotations

from typing import List

from stirrup_model import StirrupComputation, StirrupEngineeringBar

MODEL_VERSION = "8.8.1"


class EngineeringBarBuilder:
    def build(self, computations: List[StirrupComputation]) -> List[StirrupEngineeringBar]:
        bars: List[StirrupEngineeringBar] = []
        for comp in computations:
            for zone in comp.zones:
                zone_weight = round(
                    (comp.cut_length_mm / 1000.0) * zone.quantity * comp.unit_weight_kg_per_m,
                    4,
                )
                bars.append(StirrupEngineeringBar(
                    beam_id=comp.beam_id,
                    bar_role="STIRRUP",
                    diameter_mm=comp.notation.diameter_mm,
                    quantity=zone.quantity,
                    cut_length_mm=comp.cut_length_mm,
                    weight_kg=zone_weight,
                    zone=zone.zone_name,
                    fabrication_type="Closed_Stirrup",
                    hooks={
                        "hook_type": comp.hook.hook_type,
                        "hook_angle_deg": comp.hook.hook_angle_deg,
                        "hook_length_mm": comp.hook.hook_length_mm,
                        "hook_count": 2,
                        "included_in_cut_length": True,
                        "source": comp.hook.source,
                    },
                    spacing_mm=float(zone.spacing_mm),
                    spacing_pattern=comp.notation.spacing_pattern,
                    legs=comp.notation.legs,
                    perimeter_mm=comp.perimeter_mm,
                    label=comp.label,
                    metadata={
                        "notation_type": comp.notation.notation_type,
                        "zone_index": zone.zone_index,
                        "zone_length_mm": zone.length_mm,
                        "total_beam_quantity": comp.total_quantity,
                        "beam_total_weight_kg": comp.weight_kg,
                        "source_intent_id": comp.source_intent_id,
                        "source_detail_id": comp.source_detail_id,
                        "cover_mm": comp.cover_mm,
                        "beam_width_mm": comp.beam_width_mm,
                        "beam_depth_mm": comp.beam_depth_mm,
                        "beam_length_mm": comp.beam_length_mm,
                    },
                ))
        return bars
