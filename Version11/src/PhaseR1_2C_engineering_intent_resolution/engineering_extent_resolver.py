"""
EngineeringExtentResolver — physical reinforcement extent from geometry evidence.
MODEL_VERSION: 8.3.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .engineering_intent_model import (
    CONTINUITY_CONTINUOUS,
    CONTINUITY_CURTAILED,
    CONTINUITY_SINGLE,
    CONTINUITY_SUPPORT,
    EXTENT_CENTRE_SPAN,
    EXTENT_CONTINUOUS,
    EXTENT_CURTAILED,
    EXTENT_FULL_SPAN,
    EXTENT_LEFT_SUPPORT,
    EXTENT_RIGHT_SUPPORT,
    EXTENT_SUPPORT_ZONE,
    EXTENT_UNKNOWN,
    ROLE_BOTTOM_EXTRA,
    ROLE_BOTTOM_MAIN,
    ROLE_STIRRUP,
    ROLE_TOP_EXTRA,
    ROLE_TOP_MAIN,
    SUPPORT_BOTH,
    SUPPORT_LEFT,
    SUPPORT_NONE,
    SUPPORT_RIGHT,
    SUPPORT_UNKNOWN,
)

MODEL_VERSION = "8.3.2"

# Map R.3.1 geometry extent labels → engineering intent extents
_R31_MAP = {
    "FULL_SPAN": EXTENT_FULL_SPAN,
    "LEFT_SUPPORT_ONLY": EXTENT_LEFT_SUPPORT,
    "RIGHT_SUPPORT_ONLY": EXTENT_RIGHT_SUPPORT,
    "LEFT_TO_MIDSPAN": EXTENT_CURTAILED,
    "MIDSPAN_TO_RIGHT": EXTENT_CURTAILED,
    "CENTER_ONLY": EXTENT_CENTRE_SPAN,
    "UNKNOWN": EXTENT_UNKNOWN,
}


class EngineeringExtentResolver:
    """Resolve extent / continuity / support behaviour."""

    def __init__(self, extent_by_annotation: Optional[Dict[str, Dict[str, Any]]] = None):
        self._ext = extent_by_annotation or {}

    def resolve(
        self,
        ann: Dict[str, Any],
        role: str,
        beam_annotations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        aid = str(ann.get("annotation_id") or "")
        evidence: List[str] = []
        r31 = self._ext.get(aid)

        if r31 and r31.get("extent_label") and r31.get("extent_label") != "UNKNOWN":
            raw = str(r31["extent_label"])
            extent = _R31_MAP.get(raw, EXTENT_UNKNOWN)
            conf = {"HIGH": 0.9, "MEDIUM": 0.7, "LOW": 0.45}.get(
                str(r31.get("extent_confidence") or "").upper(), 0.6
            )
            evidence.append(f"r31_extent:{raw}")
            evidence.append(str(r31.get("extent_reason") or ""))
        else:
            extent, conf, evid = self._heuristic(ann, role, beam_annotations or [])
            evidence.extend(evid)

        continuity, support = self._continuity_support(extent, role)
        evidence.append(f"continuity={continuity}")
        evidence.append(f"support_type={support}")

        return {
            "extent": extent,
            "continuity": continuity,
            "support_type": support,
            "confidence": round(conf, 4),
            "evidence": [e for e in evidence if e],
            "geometry_ids": [aid] if r31 else [],
            "relationship_ids": [],
        }

    def _heuristic(
        self,
        ann: Dict[str, Any],
        role: str,
        beam_annotations: List[Dict[str, Any]],
    ) -> tuple:
        evidence: List[str] = []
        label = str(ann.get("bar_label") or "")
        same = [
            a for a in beam_annotations
            if str(a.get("bar_label") or "") == label and a.get("is_reinforcement", True)
        ]
        # Multiple identical callouts often mark support extras at both ends
        if role in (ROLE_TOP_EXTRA, ROLE_BOTTOM_EXTRA) and len(same) >= 2:
            xs = [float(a.get("x") or 0) for a in same]
            if xs:
                spread = max(xs) - min(xs)
                evidence.append(f"duplicate_callouts={len(same)}")
                evidence.append(f"x_spread={spread:.1f}")
                # Large spread → both supports; treat as support-zone extras
                return EXTENT_SUPPORT_ZONE, 0.72, evidence + ["multi_callout_support_zone"]
            return EXTENT_CURTAILED, 0.65, evidence + ["extra_curtailed_default"]

        if role in (ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN):
            return EXTENT_FULL_SPAN, 0.8, evidence + ["main_full_span_convention"]

        if role == ROLE_STIRRUP:
            return EXTENT_FULL_SPAN, 0.85, evidence + ["stirrup_along_span"]

        if role in (ROLE_TOP_EXTRA, ROLE_BOTTOM_EXTRA):
            return EXTENT_SUPPORT_ZONE, 0.6, evidence + ["extra_support_zone_default"]

        return EXTENT_UNKNOWN, 0.4, evidence + ["extent_unknown"]

    @staticmethod
    def _continuity_support(extent: str, role: str) -> tuple:
        if extent in (EXTENT_FULL_SPAN, EXTENT_CONTINUOUS):
            cont = CONTINUITY_CONTINUOUS if role in (ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN) else CONTINUITY_SINGLE
            return cont, SUPPORT_BOTH if extent == EXTENT_FULL_SPAN else SUPPORT_NONE
        if extent == EXTENT_LEFT_SUPPORT:
            return CONTINUITY_SUPPORT, SUPPORT_LEFT
        if extent == EXTENT_RIGHT_SUPPORT:
            return CONTINUITY_SUPPORT, SUPPORT_RIGHT
        if extent in (EXTENT_SUPPORT_ZONE, EXTENT_CURTAILED):
            return CONTINUITY_CURTAILED, SUPPORT_BOTH
        if extent == EXTENT_CENTRE_SPAN:
            return CONTINUITY_CURTAILED, SUPPORT_NONE
        return CONTINUITY_SINGLE, SUPPORT_UNKNOWN
