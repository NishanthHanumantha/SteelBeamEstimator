"""
EngineeringIntentResolutionEngine — Facts → EngineeringIntent.
MODEL_VERSION: 8.3.2
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List, Optional, Tuple

from .engineering_consistency_engine import (
    EngineeringConsistencyEngine,
    EngineeringIntentConfidenceEngine,
)
from .engineering_diameter_resolver import EngineeringDiameterResolver
from .engineering_extent_resolver import EngineeringExtentResolver
from .engineering_intent_model import EngineeringIntent, MODEL_VERSION
from .engineering_role_resolver import EngineeringRoleResolver

_ZONE = {
    "TOP_MAIN": "TOP_ZONE",
    "TOP_EXTRA": "TOP_ZONE",
    "BOTTOM_MAIN": "BOTTOM_ZONE",
    "BOTTOM_EXTRA": "BOTTOM_ZONE",
    "STIRRUP": "TRANSVERSE_ZONE",
    "SPACER_BAR": "BOTTOM_ZONE",
    "SIDE_FACE_REINFORCEMENT": "SIDE_ZONE",
    "UNKNOWN": "UNKNOWN_ZONE",
}


class EngineeringIntentResolutionEngine:
    """Resolve EngineeringIntent for every reinforcement annotation fact."""

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root
        self._annotations = self._load_annotations()
        self._extents = self._load_extents()
        self._geometry = self._load_geometry()
        self._role = EngineeringRoleResolver()
        self._dia = EngineeringDiameterResolver()
        self._ext = EngineeringExtentResolver(self._extents)
        self._consistency = EngineeringConsistencyEngine()
        self._confidence = EngineeringIntentConfidenceEngine()
        self._last_payload: Dict[str, Any] = {}

    def resolve_all(
        self, beam_ids: Optional[List[str]] = None
    ) -> Tuple[List[EngineeringIntent], Dict[str, Any]]:
        ids = beam_ids or sorted(self._annotations.keys())
        intents: List[EngineeringIntent] = []
        role_report: List[Dict[str, Any]] = []
        dia_report: List[Dict[str, Any]] = []
        ext_report: List[Dict[str, Any]] = []
        seq = 0

        for bid in ids:
            anns = list(self._annotations.get(bid) or [])
            geo = self._geometry.get(bid) or {}
            role_map = self._role.resolve_beam(bid, anns, geo)

            for ann in anns:
                if not ann.get("is_reinforcement", True):
                    continue
                aid = str(ann.get("annotation_id") or "")
                if not aid:
                    continue
                seq += 1
                rr = role_map.get(aid) or {
                    "role": "UNKNOWN",
                    "confidence": 0.3,
                    "evidence": ["missing_role"],
                    "layer": "UNKNOWN",
                    "source_role_hypothesis": ann.get("role") or "",
                }
                dr = self._dia.resolve(ann, neighbours=anns)
                er = self._ext.resolve(ann, rr["role"], beam_annotations=anns)

                spacing = ann.get("spacing_mm")
                if spacing is None and rr["role"] == "STIRRUP":
                    m = re.search(r"@\s*(\d+)", str(ann.get("bar_label") or ann.get("clean_text") or ""))
                    spacing = float(m.group(1)) if m else None

                intent = EngineeringIntent(
                    intent_id=f"INT::{bid}::{seq:04d}",
                    beam_id=bid,
                    role=rr["role"],
                    diameter_mm=float(dr["diameter_mm"]),
                    quantity=int(dr["quantity"]),
                    extent=er["extent"],
                    continuity=er["continuity"],
                    support_type=er["support_type"],
                    layer=str(rr.get("layer") or ""),
                    bar_label=str(dr.get("bar_label") or ann.get("bar_label") or ""),
                    spacing_mm=spacing,
                    zone=_ZONE.get(rr["role"], "UNKNOWN_ZONE"),
                    role_confidence=float(rr["confidence"]),
                    diameter_confidence=float(dr["confidence"]),
                    extent_confidence=float(er["confidence"]),
                    intent_reason=(
                        f"role={rr['role']}; dia={dr['diameter_mm']}; extent={er['extent']}"
                    ),
                    evidence_ids=[aid],
                    annotation_ids=[aid],
                    geometry_ids=list(er.get("geometry_ids") or []),
                    relationship_ids=list(er.get("relationship_ids") or []),
                    evidence=list(rr.get("evidence") or [])
                    + list(dr.get("evidence") or [])
                    + list(er.get("evidence") or []),
                    source_role_hypothesis=str(rr.get("source_role_hypothesis") or ""),
                )
                self._confidence.apply(intent)
                intents.append(intent)

                role_report.append({
                    "intent_id": intent.intent_id,
                    "beam_id": bid,
                    "annotation_id": aid,
                    "source_role": intent.source_role_hypothesis,
                    "resolved_role": intent.role,
                    "changed": intent.source_role_hypothesis != intent.role,
                    "confidence": intent.role_confidence,
                    "evidence": rr.get("evidence"),
                })
                dia_report.append({
                    "intent_id": intent.intent_id,
                    "beam_id": bid,
                    "diameter_mm": intent.diameter_mm,
                    "quantity": intent.quantity,
                    "confidence": intent.diameter_confidence,
                    "evidence": dr.get("evidence"),
                })
                ext_report.append({
                    "intent_id": intent.intent_id,
                    "beam_id": bid,
                    "extent": intent.extent,
                    "continuity": intent.continuity,
                    "support_type": intent.support_type,
                    "confidence": intent.extent_confidence,
                    "evidence": er.get("evidence"),
                })

        consistency = self._consistency.validate(intents)
        # re-apply confidence after flags
        for it in intents:
            self._confidence.apply(it)
        conf_dist = self._confidence.distribution(intents)

        role_changes = sum(1 for r in role_report if r.get("changed"))
        payload = {
            "model_version": MODEL_VERSION,
            "intent_count": len(intents),
            "beam_count": len(ids),
            "role_changes": role_changes,
            "role_resolution": {
                "model_version": MODEL_VERSION,
                "entries": role_report,
                "changed_count": role_changes,
                "unchanged_count": len(role_report) - role_changes,
            },
            "diameter_resolution": {
                "model_version": MODEL_VERSION,
                "entries": dia_report,
            },
            "extent_resolution": {
                "model_version": MODEL_VERSION,
                "entries": ext_report,
                "extent_histogram": _hist([e["extent"] for e in ext_report]),
            },
            "confidence": conf_dist,
            "consistency": consistency,
        }
        self._last_payload = payload
        return intents, payload

    def intents_for_beam(self, beam_id: str) -> List[EngineeringIntent]:
        intents, _ = self.resolve_all([beam_id])
        return intents

    def _load_annotations(self) -> Dict[str, List[Dict[str, Any]]]:
        path = (
            self._v7
            / "data/output/PhaseR.1_generalized_reinforcement_discovery"
            / "reinforcement_annotations.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("by_beam") or {}

    def _load_extents(self) -> Dict[str, Dict[str, Any]]:
        path = (
            self._v7
            / "data/output/PhaseR3.1_engineering_relationship_engine"
            / "ExtentEvidence.json"
        )
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        out = {}
        for row in data.get("extents") or []:
            aid = row.get("annotation_id")
            if aid:
                out[str(aid)] = row
        return out

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


def _hist(values: List[str]) -> Dict[str, int]:
    h: Dict[str, int] = {}
    for v in values:
        h[v] = h.get(v, 0) + 1
    return h
