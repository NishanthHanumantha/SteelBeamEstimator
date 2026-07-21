"""
EngineeringRoleResolver — multi-evidence role resolution.
MODEL_VERSION: 8.3.2

Does NOT classify from text alone. Uses zone, elevation, diameter hierarchy,
neighbour comparison, stirrup markers, and section depth.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .engineering_intent_model import (
    ROLE_BOTTOM_EXTRA,
    ROLE_BOTTOM_MAIN,
    ROLE_SIDE_FACE,
    ROLE_SPACER,
    ROLE_STIRRUP,
    ROLE_TOP_EXTRA,
    ROLE_TOP_MAIN,
    ROLE_UNKNOWN,
)

MODEL_VERSION = "8.3.2"
_SPACER_MAX_DIA = 12.0
_DEEP_BEAM_MM = 900.0


def _is_stirrup(ann: Dict[str, Any]) -> bool:
    if ann.get("role") == ROLE_STIRRUP:
        return True
    if ann.get("spacing_mm") is not None:
        return True
    text = str(ann.get("clean_text") or ann.get("bar_label") or "")
    return bool(re.search(r"@", text))


def _zone_of(ann: Dict[str, Any]) -> str:
    z = str(ann.get("position_zone") or "UNKNOWN_ZONE")
    if z in ("TOP_ZONE", "BOTTOM_ZONE"):
        return z
    dy = ann.get("dy_from_centroid")
    if dy is None:
        return "UNKNOWN_ZONE"
    # Observed convention: positive dy → top, negative → bottom
    if float(dy) > 50:
        return "TOP_ZONE"
    if float(dy) < -50:
        return "BOTTOM_ZONE"
    return "MID_ZONE"


def _main_score(ann: Dict[str, Any], max_dia: float, max_qty: float, max_elev: float) -> float:
    """
    Diameter-dominant score. Quantity must not let small bars beat large mains
    (e.g. 8Y8 must not outrank 3Y20).
    """
    dia = float(ann.get("diameter_mm") or 0)
    qty = float(ann.get("quantity") or 0)
    elev = abs(float(ann.get("dy_from_centroid") or 0))
    dia_n = (dia / max_dia) if max_dia > 0 else 0.0
    qty_n = (qty / max_qty) if max_qty > 0 else 0.0
    elev_n = (elev / max_elev) if max_elev > 0 else 0.0
    # Diameter heavily weighted — structural hierarchy
    return 0.70 * dia_n + 0.20 * qty_n + 0.10 * elev_n


class EngineeringRoleResolver:
    """Resolve reinforcement role from combined engineering evidence."""

    def resolve_beam(
        self,
        beam_id: str,
        annotations: List[Dict[str, Any]],
        geometry: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Returns mapping annotation_id -> {role, confidence, evidence, layer}.
        """
        geometry = geometry or {}
        depth = float(geometry.get("depth_mm") or 750.0)
        rebar = [a for a in annotations if a.get("is_reinforcement", True)]
        results: Dict[str, Dict[str, Any]] = {}

        stirrups = [a for a in rebar if _is_stirrup(a)]
        others = [a for a in rebar if not _is_stirrup(a)]

        for a in stirrups:
            aid = str(a.get("annotation_id") or "")
            results[aid] = {
                "role": ROLE_STIRRUP,
                "confidence": 0.95,
                "evidence": [
                    "stirrup_marker_or_spacing",
                    f"label={a.get('bar_label')}",
                ],
                "layer": "TRANSVERSE",
                "source_role_hypothesis": a.get("role") or "",
            }

        by_zone: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for a in others:
            by_zone[_zone_of(a)].append(a)

        for zone, anns in by_zone.items():
            if zone == "TOP_ZONE":
                self._assign_longitudinal(
                    anns, results, ROLE_TOP_MAIN, ROLE_TOP_EXTRA, "TOP"
                )
            elif zone == "BOTTOM_ZONE":
                self._assign_longitudinal(
                    anns, results, ROLE_BOTTOM_MAIN, ROLE_BOTTOM_EXTRA, "BOTTOM"
                )
            elif zone == "MID_ZONE":
                for a in anns:
                    aid = str(a.get("annotation_id") or "")
                    dia = float(a.get("diameter_mm") or 0)
                    if depth >= _DEEP_BEAM_MM and dia <= 16:
                        role = ROLE_SIDE_FACE
                        conf = 0.75
                        evid = ["mid_zone", "deep_beam", f"dia={dia}"]
                        layer = "SIDE"
                    elif dia <= _SPACER_MAX_DIA:
                        role = ROLE_SPACER
                        conf = 0.7
                        evid = ["mid_zone", "small_diameter"]
                        layer = "SPACER"
                    else:
                        role = ROLE_BOTTOM_EXTRA
                        conf = 0.55
                        evid = ["mid_zone_fallback"]
                        layer = "BOTTOM"
                    results[aid] = {
                        "role": role,
                        "confidence": conf,
                        "evidence": evid,
                        "layer": layer,
                        "source_role_hypothesis": a.get("role") or "",
                    }
            else:
                for a in anns:
                    aid = str(a.get("annotation_id") or "")
                    dia = float(a.get("diameter_mm") or 0)
                    role = ROLE_SPACER if dia <= _SPACER_MAX_DIA else ROLE_UNKNOWN
                    results[aid] = {
                        "role": role,
                        "confidence": 0.45,
                        "evidence": ["unknown_zone"],
                        "layer": "UNKNOWN",
                        "source_role_hypothesis": a.get("role") or "",
                    }

        return results

    def _assign_longitudinal(
        self,
        anns: List[Dict[str, Any]],
        results: Dict[str, Dict[str, Any]],
        main_role: str,
        extra_role: str,
        layer: str,
    ) -> None:
        if not anns:
            return

        # Unique identities by label — avoid duplicate callout inflation for MAIN
        by_label: Dict[str, Dict[str, Any]] = {}
        for a in anns:
            lbl = str(a.get("bar_label") or a.get("clean_text") or "")
            prev = by_label.get(lbl)
            if prev is None:
                by_label[lbl] = a
            else:
                # keep highest association confidence representative
                if float(a.get("association_confidence") or 0) >= float(
                    prev.get("association_confidence") or 0
                ):
                    by_label[lbl] = a

        reps = list(by_label.values())
        max_dia = max(float(a.get("diameter_mm") or 0) for a in reps) or 1.0
        max_qty = max(float(a.get("quantity") or 0) for a in reps) or 1.0
        max_elev = max(abs(float(a.get("dy_from_centroid") or 0)) for a in reps) or 1.0

        scored: List[Tuple[float, str, Dict[str, Any]]] = []
        for a in reps:
            s = _main_score(a, max_dia, max_qty, max_elev)
            scored.append((s, str(a.get("bar_label") or ""), a))
        scored.sort(key=lambda t: (t[0], float(t[2].get("diameter_mm") or 0)), reverse=True)

        main_label = scored[0][1] if scored else ""
        main_ann = scored[0][2] if scored else None

        # Map every annotation instance (including duplicates) to resolved role
        for a in anns:
            aid = str(a.get("annotation_id") or "")
            lbl = str(a.get("bar_label") or a.get("clean_text") or "")
            dia = float(a.get("diameter_mm") or 0)
            evidence = [
                f"zone={_zone_of(a)}",
                f"dia={dia}",
                f"qty={a.get('quantity')}",
                f"elev_dy={a.get('dy_from_centroid')}",
                "diameter_dominant_main_selection",
            ]

            if lbl == main_label:
                role = main_role
                conf = min(0.98, 0.75 + 0.05 * len(scored))
                evidence.append(f"selected_main_score={scored[0][0]:.3f}")
            elif dia <= _SPACER_MAX_DIA and layer == "BOTTOM":
                # Small bottom bars are typically spacers/chairs when a larger main exists
                if main_ann and float(main_ann.get("diameter_mm") or 0) > dia + 0.1:
                    role = ROLE_SPACER
                    conf = 0.8
                    evidence.append("small_dia_below_main_hierarchy")
                else:
                    role = extra_role
                    conf = 0.7
                    evidence.append("extra_same_zone")
            else:
                role = extra_role
                conf = 0.78
                evidence.append("extra_same_zone_not_main")

            # Leader / association evidence boost
            if float(a.get("association_confidence") or 0) >= 0.8:
                conf = min(0.99, conf + 0.05)
                evidence.append("strong_leader_association")

            results[aid] = {
                "role": role,
                "confidence": round(conf, 4),
                "evidence": evidence,
                "layer": layer,
                "source_role_hypothesis": a.get("role") or "",
            }
