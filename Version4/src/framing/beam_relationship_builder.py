"""Build beam-to-beam and beam-to-support relationships."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Set, Tuple

from src.framing.framing_knowledge_graph import (
    EDGE_CONNECTED_TO,
    EDGE_CONTINUOUS_WITH,
    EDGE_INTERSECTS,
    EDGE_SUPPORTED_BY,
    GraphEdge,
)


class BeamRelationshipBuilder:
    """Derive engineering relationships from resolved supports and geometry."""

    def __init__(self, config: dict[str, Any]) -> None:
        kg = config.get("knowledge_graph", {})
        self._junction_tol = float(
            kg.get("junction_tolerance_mm", config.get("connectivity_tolerance_mm", 250.0))
        )
        self._angle_tol = float(
            kg.get("continuous_angle_tolerance_deg", config.get("orthogonal_tolerance_deg", 5.0))
        )

    def build(self, model: dict[str, Any]) -> dict[str, Any]:
        beams = model.get("beams", [])
        structural_nodes = model.get("structural_nodes", [])
        beam_index = {b["beam_id"]: b for b in beams}

        edges: List[GraphEdge] = []
        seen: Set[Tuple[str, str, str]] = set()

        for beam in beams:
            beam_id = beam["beam_id"]
            supports = beam.get("supports", {})
            for end_name, support in (("left", supports.get("left", {})), ("right", supports.get("right", {}))):
                support_type = str(support.get("type", "UNKNOWN")).upper()
                support_id = support.get("id")
                if not support_id or support_type == "FREE_END":
                    continue
                key = (beam_id, support_id, EDGE_SUPPORTED_BY)
                if key not in seen:
                    seen.add(key)
                    edges.append(
                        GraphEdge(
                            from_id=beam_id,
                            to_id=str(support_id),
                            relationship=EDGE_SUPPORTED_BY,
                            confidence=float(support.get("confidence", 0.0)),
                            properties={"end": "start" if end_name == "left" else "end"},
                        )
                    )
                key = (beam_id, str(support_id), EDGE_CONNECTED_TO)
                if key not in seen:
                    seen.add(key)
                    edges.append(
                        GraphEdge(
                            from_id=beam_id,
                            to_id=str(support_id),
                            relationship=EDGE_CONNECTED_TO,
                            confidence=float(support.get("confidence", 0.0)),
                        )
                    )

        edges.extend(self._continuous_from_nodes(structural_nodes, beam_index, seen))
        edges.extend(self._intersects_from_endpoints(beams, seen))
        edges.extend(self._continuous_from_beam_joints(beams, seen))

        by_rel: Dict[str, List[dict[str, Any]]] = {}
        for edge in edges:
            by_rel.setdefault(edge.relationship, []).append(edge.to_dict())

        return {
            "phase": "Phase F.5",
            "edge_count": len(edges),
            "relationships": by_rel,
            "edges": [e.to_dict() for e in edges],
        }

    def _continuous_from_nodes(
        self,
        nodes: List[dict[str, Any]],
        beam_index: Dict[str, dict[str, Any]],
        seen: Set[Tuple[str, str, str]],
    ) -> List[GraphEdge]:
        edges: List[GraphEdge] = []
        for node in nodes:
            connected = node.get("connected_beams", [])
            if len(connected) < 2:
                continue
            for i, beam_a in enumerate(connected):
                for beam_b in connected[i + 1:]:
                    if not self._compatible_orientation(beam_index.get(beam_a), beam_index.get(beam_b)):
                        continue
                    key = (beam_a, beam_b, EDGE_CONTINUOUS_WITH)
                    if key in seen:
                        continue
                    seen.add(key)
                    edges.append(
                        GraphEdge(
                            from_id=beam_a,
                            to_id=beam_b,
                            relationship=EDGE_CONTINUOUS_WITH,
                            confidence=0.88,
                            properties={"via_support": node.get("id")},
                        )
                    )
        return edges

    def _continuous_from_beam_joints(
        self,
        beams: List[dict[str, Any]],
        seen: Set[Tuple[str, str, str]],
    ) -> List[GraphEdge]:
        edges: List[GraphEdge] = []
        for beam in beams:
            beam_id = beam["beam_id"]
            for end_name, support in (
                ("left", beam.get("supports", {}).get("left", {})),
                ("right", beam.get("supports", {}).get("right", {})),
            ):
                if str(support.get("type", "")).upper() != "BEAM":
                    continue
                other_id = support.get("id")
                if not other_id:
                    continue
                if not self._compatible_orientation(beam, next(
                    (b for b in beams if b["beam_id"] == other_id), None
                )):
                    continue
                pair = tuple(sorted([beam_id, str(other_id)]))
                key = (pair[0], pair[1], EDGE_CONTINUOUS_WITH)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    GraphEdge(
                        from_id=beam_id,
                        to_id=str(other_id),
                        relationship=EDGE_CONTINUOUS_WITH,
                        confidence=float(support.get("confidence", 0.85)),
                        properties={"joint_end": end_name},
                    )
                )
        return edges

    def _intersects_from_endpoints(
        self,
        beams: List[dict[str, Any]],
        seen: Set[Tuple[str, str, str]],
    ) -> List[GraphEdge]:
        endpoints: List[Tuple[str, float, float]] = []
        for beam in beams:
            cl = beam.get("geometry", {}).get("centerline") or {}
            for pt in (cl.get("start_point"), cl.get("end_point")):
                if pt:
                    endpoints.append((beam["beam_id"], float(pt["x"]), float(pt["y"])))

        edges: List[GraphEdge] = []
        for i, (id_a, ax, ay) in enumerate(endpoints):
            for id_b, bx, by in endpoints[i + 1:]:
                if id_a == id_b:
                    continue
                dist = math.hypot(ax - bx, ay - by)
                if dist > self._junction_tol:
                    continue
                key = tuple(sorted([id_a, id_b])) + (EDGE_INTERSECTS,)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    GraphEdge(
                        from_id=id_a,
                        to_id=id_b,
                        relationship=EDGE_INTERSECTS,
                        confidence=max(0.7, 1.0 - dist / self._junction_tol),
                        properties={"distance_mm": round(dist, 3)},
                    )
                )
        return edges

    def _compatible_orientation(
        self,
        beam_a: dict[str, Any] | None,
        beam_b: dict[str, Any] | None,
    ) -> bool:
        if not beam_a or not beam_b:
            return False
        ang_a = float((beam_a.get("geometry", {}).get("centerline") or {}).get("angle_deg", 0))
        ang_b = float((beam_b.get("geometry", {}).get("centerline") or {}).get("angle_deg", 0))
        diff = abs(ang_a - ang_b)
        diff = min(diff, 180.0 - diff)
        return diff <= self._angle_tol or abs(diff - 90.0) <= self._angle_tol
