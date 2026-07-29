"""
Load geometry, intents, details, rule library (JSON only — no Excel/benchmark).
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

MODEL_VERSION = "8.8.1"


def _read(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class InputLoader:
    def __init__(self, v8_root: Path):
        self.v8 = Path(v8_root)
        self.out = self.v8 / "data" / "output"

    def load(self) -> Dict[str, Any]:
        geo = _read(self.out / "PhaseR1_2A_geometry_accuracy" / "validated_beam_geometry.json") or {}
        intents = (_read(self.out / "PhaseR1_2C_engineering_intent_resolution" / "engineering_intents.json") or {}).get("intents") or []
        details = (_read(self.out / "PhaseR1_2D_reinforcement_detailing" / "reinforcement_details.json") or {}).get("details") or []
        rules = _read(self.out / "PhaseR1_6_engineering_rule_synthesis" / "engineering_rule_library.json") or {}

        geometries = geo.get("geometries") or {}
        stirrup_intents = [
            i for i in intents
            if str(i.get("role") or "").upper() == "STIRRUP"
        ]
        # Map detail by intent_id
        detail_by_intent = {d.get("intent_id"): d for d in details if d.get("intent_id")}

        jobs: List[Dict[str, Any]] = []
        for it in stirrup_intents:
            bid = str(it.get("beam_id") or "")
            g = geometries.get(bid) or {}
            length = float(g.get("effective_span_mm") or g.get("clear_span_mm") or 0)
            width = float(g.get("width_mm") or 0)
            depth = float(g.get("depth_mm") or 0)
            if length <= 0 or width <= 0 or depth <= 0:
                continue
            label = str(it.get("bar_label") or "")
            if not label:
                continue
            det = detail_by_intent.get(it.get("intent_id")) or {}
            jobs.append({
                "beam_id": bid,
                "label": label,
                "beam_length_mm": length,
                "beam_width_mm": width,
                "beam_depth_mm": depth,
                "intent_id": it.get("intent_id") or "",
                "detail_id": det.get("detail_id") or "",
            })

        return {
            "jobs": jobs,
            "geometry_count": len(geometries),
            "stirrup_intent_count": len(stirrup_intents),
            "rule_library_ref": {
                "available": bool(rules),
                "families": rules.get("families") or [],
                "has_stirrup_rule": "Stirrup Interpretation" in (rules.get("families") or []),
            },
            "sources": {
                "geometry": str(self.out / "PhaseR1_2A_geometry_accuracy" / "validated_beam_geometry.json"),
                "intents": str(self.out / "PhaseR1_2C_engineering_intent_resolution" / "engineering_intents.json"),
                "details": str(self.out / "PhaseR1_2D_reinforcement_detailing" / "reinforcement_details.json"),
                "rules": str(self.out / "PhaseR1_6_engineering_rule_synthesis" / "engineering_rule_library.json"),
            },
        }
