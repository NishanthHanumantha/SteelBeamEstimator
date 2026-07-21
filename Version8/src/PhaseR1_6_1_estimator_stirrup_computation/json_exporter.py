"""
JSON exporters for Phase R.1.6.1.
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from stirrup_model import StirrupComputation, StirrupEngineeringBar

MODEL_VERSION = "8.8.1"


class JsonExporter:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, payload: Dict[str, Any]) -> Dict[str, str]:
        comps: List[StirrupComputation] = payload["computations"]
        bars: List[StirrupEngineeringBar] = payload["bars"]
        paths: Dict[str, str] = {}

        def dump(name: str, data: Any) -> None:
            p = self.output_dir / name
            p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[name] = str(p)

        dump("stirrup_notation.json", {
            "model_version": MODEL_VERSION,
            "items": [
                {"beam_id": c.beam_id, "label": c.label, "notation": c.notation.to_dict()}
                for c in comps
            ],
        })
        dump("spacing_patterns.json", {
            "model_version": MODEL_VERSION,
            "items": [
                {
                    "beam_id": c.beam_id,
                    "pattern": c.notation.spacing_pattern,
                    "values_mm": list(c.notation.spacing_values_mm),
                    "type": c.notation.notation_type,
                }
                for c in comps
            ],
        })
        dump("stirrup_zones.json", {
            "model_version": MODEL_VERSION,
            "items": [
                {
                    "beam_id": c.beam_id,
                    "label": c.label,
                    "beam_length_mm": c.beam_length_mm,
                    "zone_count": len(c.zones),
                    "zones": [z.to_dict() for z in c.zones],
                }
                for c in comps
            ],
        })
        dump("stirrup_quantities.json", {
            "model_version": MODEL_VERSION,
            "items": [
                {
                    "beam_id": c.beam_id,
                    "label": c.label,
                    "zone_quantities": {z.zone_name: z.quantity for z in c.zones},
                    "total_quantity": c.total_quantity,
                }
                for c in comps
            ],
        })
        dump("stirrup_cut_lengths.json", {
            "model_version": MODEL_VERSION,
            "items": [
                {
                    "beam_id": c.beam_id,
                    "perimeter_mm": c.perimeter_mm,
                    "hook_length_mm": c.hook.hook_length_mm,
                    "cut_length_mm": c.cut_length_mm,
                    "formula": "perimeter + 2 * hook_length",
                }
                for c in comps
            ],
        })
        dump("stirrup_weights.json", {
            "model_version": MODEL_VERSION,
            "items": [
                {
                    "beam_id": c.beam_id,
                    "diameter_mm": c.notation.diameter_mm,
                    "quantity": c.total_quantity,
                    "cut_length_mm": c.cut_length_mm,
                    "total_length_m": c.total_length_m,
                    "unit_weight_kg_per_m": c.unit_weight_kg_per_m,
                    "weight_kg": c.weight_kg,
                }
                for c in comps
            ],
            "total_weight_kg": round(sum(c.weight_kg for c in comps), 4),
        })
        dump("engineering_stirrups.json", {
            "model_version": MODEL_VERSION,
            "computation_count": len(comps),
            "bar_count": len(bars),
            "computations": [c.to_dict() for c in comps],
            "engineering_bars": [b.to_dict() for b in bars],
        })
        dump("validation_report.json", payload["validation"])
        dump("general_notes_integration.json", payload["gn_summary"])
        return paths
