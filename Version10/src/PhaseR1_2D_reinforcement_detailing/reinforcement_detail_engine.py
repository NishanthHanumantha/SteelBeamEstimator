"""
ReinforcementDetailEngine — public API for R.1.2D.
MODEL_VERSION: 8.4.0
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple

from .reinforcement_detail_builder import ReinforcementDetailBuilder
from .reinforcement_detail_model import ReinforcementDetail

MODEL_VERSION = "8.4.0"


class ReinforcementDetailEngine:
    """Convert EngineeringIntent objects into ReinforcementDetail objects."""

    def __init__(
        self,
        v7_root: pathlib.Path,
        engineering_context: Optional[Dict[str, Any]] = None,
    ):
        self._v7 = v7_root
        self._ctx = engineering_context or {}
        self._geometry = self._load_geometry()
        self._builder = ReinforcementDetailBuilder(self._ctx)
        self._last_payload: Dict[str, Any] = {}

    def build_from_intents(
        self, intents: List[Any]
    ) -> Tuple[List[ReinforcementDetail], Dict[str, Any]]:
        by_beam: Dict[str, List[Any]] = {}
        for it in intents:
            by_beam.setdefault(str(it.beam_id), []).append(it)
        details, payload = self._builder.build_for_beams(by_beam, self._geometry)
        payload["intent_count"] = len(intents)
        # summaries
        payload["support_zone_summary"] = self._summarize_support(details)
        payload["continuity_summary"] = self._hist([d.continuity for d in details])
        payload["development_length_summary"] = self._summarize_ld(details)
        payload["curtailment_summary"] = self._hist([d.curtailment_type for d in details])
        payload["side_face_detection"] = {
            "side_face_true": sum(1 for d in details if d.side_face),
            "side_face_false": sum(1 for d in details if not d.side_face),
            "entries": [
                {
                    "detail_id": d.detail_id,
                    "beam_id": d.beam_id,
                    "side_face": d.side_face,
                    "role": d.role,
                }
                for d in details
                if d.side_face
            ],
        }
        self._last_payload = payload
        return details, payload

    def build_from_intents_by_beam(
        self, intents_by_beam: Dict[str, List[Any]]
    ) -> Tuple[Dict[str, List[ReinforcementDetail]], Dict[str, Any]]:
        flat = []
        for intents in intents_by_beam.values():
            flat.extend(intents)
        details, payload = self.build_from_intents(flat)
        by_beam: Dict[str, List[ReinforcementDetail]] = {}
        for d in details:
            by_beam.setdefault(d.beam_id, []).append(d)
        return by_beam, payload

    def _load_geometry(self) -> Dict[str, Any]:
        path = (
            self._v7
            / "data/output/PhaseR1_2A_geometry_accuracy"
            / "validated_beam_geometry.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("geometries") or {}

    @staticmethod
    def _hist(values: List[str]) -> Dict[str, int]:
        h: Dict[str, int] = {}
        for v in values:
            h[v] = h.get(v, 0) + 1
        return h

    def _summarize_support(self, details: List[ReinforcementDetail]) -> Dict[str, Any]:
        return {
            "regions": self._hist([d.support_region for d in details]),
            "left_true": sum(1 for d in details if d.left_support_zone),
            "mid_true": sum(1 for d in details if d.mid_zone),
            "right_true": sum(1 for d in details if d.right_support_zone),
        }

    def _summarize_ld(self, details: List[ReinforcementDetail]) -> Dict[str, Any]:
        computed = [d for d in details if d.development_length_mm is not None]
        flagged = [d for d in details if d.development_source == "UNAVAILABLE"]
        return {
            "computed_count": len(computed),
            "flagged_unavailable": len(flagged),
            "sources": self._hist([d.development_source for d in details]),
            "sample": [
                {
                    "detail_id": d.detail_id,
                    "diameter_mm": d.diameter_mm,
                    "development_length_mm": d.development_length_mm,
                    "rule": d.development_rule,
                    "source": d.development_source,
                }
                for d in computed[:20]
            ],
        }
