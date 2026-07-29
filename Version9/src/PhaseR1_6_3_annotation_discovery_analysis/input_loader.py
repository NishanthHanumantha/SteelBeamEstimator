"""
Load read-only artefacts for Phase R.1.6.3.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

MODEL_VERSION = "8.8.3"
_NAT_RE = re.compile(r"(\d+)|(\D+)")


def natural_beam_key(beam_id: str) -> Tuple:
    parts: List[Any] = []
    for num, text in _NAT_RE.findall(str(beam_id)):
        if num:
            parts.append(int(num))
        else:
            parts.append(text.upper())
    return tuple(parts)


def _read(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class InputLoader:
    def __init__(self, v8_root: Path):
        self.v8 = Path(v8_root)
        self.out = self.v8 / "data" / "output"

    def load(self) -> Dict[str, Any]:
        registry = _read(self.out / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json") or {}
        geometry = _read(self.out / "PhaseR1_2A_geometry_accuracy" / "validated_beam_geometry.json") or {}
        annotations = _read(
            self.out / "PhaseR.1_generalized_reinforcement_discovery" / "reinforcement_annotations.json"
        ) or {}
        relationships = _read(
            self.out / "PhaseR.1_generalized_reinforcement_discovery" / "engineering_relationships.json"
        ) or {}
        beam_models = _read(
            self.out / "PhaseR.1_generalized_reinforcement_discovery" / "beam_reinforcement_models.json"
        ) or {}
        intents = _read(self.out / "PhaseR1_2C_engineering_intent_resolution" / "engineering_intents.json") or {}
        details = _read(self.out / "PhaseR1_2D_reinforcement_detailing" / "reinforcement_details.json") or {}
        pieces = _read(self.out / "PhaseR1_3_reinforcement_piece_generation" / "reinforcement_pieces.json") or {}
        bars = _read(self.out / "PhaseR1.3_pipeline_integration" / "engineering_bar_models.json") or {}
        rule012 = _read(self.out / "PhaseR1_6_2_stirrup_coverage_validation" / "beam_stirrup_validation.json") or {}
        dash012 = _read(self.out / "PhaseR1_6_2_stirrup_coverage_validation" / "coverage_dashboard.json") or {}
        leaders = _read(self.out / "PhaseR3.1_engineering_relationship_engine" / "LeaderInventory.json") or {}
        axes = _read(self.out / "PhaseR3_geometry_context_engine" / "BeamAxis.json") or {}

        beam_ids = list(registry.get("beam_ids") or [])
        if not beam_ids and isinstance(registry.get("beams"), dict):
            beam_ids = list(registry["beams"].keys())
        beam_ids = sorted({str(b) for b in beam_ids if b}, key=natural_beam_key)

        detected, missing, status_by = self._rule012_sets(rule012)

        return {
            "model_version": MODEL_VERSION,
            "beam_ids": beam_ids,
            "registry": registry,
            "geometry": geometry.get("geometries") or {},
            "annotations_by_beam": annotations.get("by_beam") or {},
            "relationships_by_beam": relationships.get("by_beam") or {},
            "beam_models": self._index_models(beam_models),
            "intents": intents.get("intents") or [],
            "details": details.get("details") or [],
            "pieces": pieces.get("pieces") or [],
            "bars": bars.get("beams") or [],
            "rule012": rule012,
            "dashboard012": dash012,
            "detected_ids": detected,
            "missing_ids": missing,
            "rule012_status_by_beam": status_by,
            "leaders": leaders.get("leaders") or [],
            "axes": axes.get("axes") or {},
            "sources": {
                "beam_registry": str(self.out / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"),
                "geometry": str(self.out / "PhaseR1_2A_geometry_accuracy" / "validated_beam_geometry.json"),
                "annotations": str(
                    self.out / "PhaseR.1_generalized_reinforcement_discovery" / "reinforcement_annotations.json"
                ),
                "rule012": str(
                    self.out / "PhaseR1_6_2_stirrup_coverage_validation" / "beam_stirrup_validation.json"
                ),
            },
        }

    @staticmethod
    def _index_models(beam_models: Dict[str, Any]) -> Dict[str, Any]:
        models = beam_models.get("models") or []
        out: Dict[str, Any] = {}
        if isinstance(models, dict):
            return {str(k): v for k, v in models.items()}
        for m in models:
            if isinstance(m, dict) and m.get("beam_id"):
                out[str(m["beam_id"])] = m
        return out

    @staticmethod
    def _rule012_sets(rule012: Dict[str, Any]) -> Tuple[Set[str], Set[str], Dict[str, str]]:
        detected: Set[str] = set()
        missing: Set[str] = set()
        status_by: Dict[str, str] = {}
        levels = (rule012.get("levels") or {}).get("beam") or []
        if levels:
            for row in levels:
                bid = str(row.get("beam_id") or "")
                st = str(row.get("status") or "UNKNOWN")
                status_by[bid] = st
                if st == "PASS":
                    detected.add(bid)
                elif st == "FAIL":
                    missing.add(bid)
            return detected, missing, status_by
        for row in rule012.get("beams") or []:
            bid = str(row.get("beam_id") or "")
            st = str(row.get("status") or "UNKNOWN")
            status_by[bid] = st
            if st == "PASS" or row.get("stirrup_exists"):
                detected.add(bid)
            elif st == "FAIL":
                missing.add(bid)
        return detected, missing, status_by
