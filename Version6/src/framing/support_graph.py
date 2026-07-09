"""Structural support graph — support nodes connected through beams."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.framing.support_classifier import SUPPORT_FREE_END, VALID_SUPPORT_TYPES


class SupportGraphBuilder:
    """Build support-node ↔ beam structural connectivity graph."""

    def build(
        self,
        beams: List[dict[str, Any]],
        structural_nodes: List[dict[str, Any]],
    ) -> dict[str, Any]:
        beam_nodes = [
            {
                "id": beam["beam_id"],
                "type": "BEAM",
                "beam_mark": beam.get("beam_mark"),
            }
            for beam in beams
        ]
        support_nodes = [
            {
                "id": node["id"],
                "type": node["type"],
            }
            for node in structural_nodes
        ]

        edges: List[dict[str, Any]] = []
        chains: List[dict[str, Any]] = []

        for beam in beams:
            beam_id = beam["beam_id"]
            support_model = beam.get("supports", {})
            left = support_model.get("left", {})
            right = support_model.get("right", {})

            left_id = self._node_id(left)
            right_id = self._node_id(right)

            if left_id:
                edges.append(
                    {
                        "from": left_id,
                        "to": beam_id,
                        "relationship": "support_to_beam",
                        "end": "start",
                        "support_type": left.get("type"),
                        "confidence": left.get("confidence"),
                    }
                )
            if right_id:
                edges.append(
                    {
                        "from": beam_id,
                        "to": right_id,
                        "relationship": "beam_to_support",
                        "end": "end",
                        "support_type": right.get("type"),
                        "confidence": right.get("confidence"),
                    }
                )

            if left_id and right_id:
                chains.append(
                    {
                        "chain": [left_id, beam_id, right_id],
                        "beam_mark": beam.get("beam_mark"),
                    }
                )

        adjacency: Dict[str, List[str]] = {}
        for edge in edges:
            adjacency.setdefault(edge["from"], []).append(edge["to"])
            adjacency.setdefault(edge["to"], []).append(edge["from"])

        return {
            "phase": "Phase F.3",
            "beam_node_count": len(beam_nodes),
            "support_node_count": len(support_nodes),
            "edge_count": len(edges),
            "nodes": {
                "beams": beam_nodes,
                "supports": support_nodes,
            },
            "edges": edges,
            "chains": chains,
            "adjacency": adjacency,
        }

    @staticmethod
    def _node_id(support: dict[str, Any]) -> Optional[str]:
        if not support:
            return None
        support_type = support.get("type")
        if support_type == SUPPORT_FREE_END:
            return None
        if support_type not in VALID_SUPPORT_TYPES:
            return None
        node_id = support.get("id")
        if node_id:
            return str(node_id)
        if support_type == SUPPORT_FREE_END:
            return None
        return support_type

    def build_structural_nodes(
        self,
        beams: List[dict[str, Any]],
        columns: List[Any],
    ) -> List[dict[str, Any]]:
        nodes: Dict[str, dict[str, Any]] = {}

        for zone in columns:
            nodes[zone.support_id] = {
                "id": zone.support_id,
                "type": "COLUMN",
                "location": zone.centroid.as_dict(),
                "bbox": zone.bbox,
                "layer": zone.layer,
                "connected_beams": [],
            }

        for beam in beams:
            beam_id = beam["beam_id"]
            geometry = beam.get("geometry", {})
            centerline = geometry.get("centerline") or {}
            support_model = beam.get("supports", {})

            for end_name, point_key in (("left", "start_point"), ("right", "end_point")):
                support = support_model.get(end_name, {})
                support_type = support.get("type")
                support_id = support.get("id")
                if support_type == SUPPORT_FREE_END or not support_id:
                    continue

                if support_id not in nodes:
                    location = self._endpoint_location(centerline, end_name)
                    nodes[support_id] = {
                        "id": support_id,
                        "type": support_type,
                        "location": location,
                        "connected_beams": [],
                    }

                connected = nodes[support_id]["connected_beams"]
                if beam_id not in connected:
                    connected.append(beam_id)

        return sorted(nodes.values(), key=lambda item: item["id"])

    @staticmethod
    def _endpoint_location(centerline: dict[str, Any], end_name: str) -> Optional[dict[str, float]]:
        key = "start_point" if end_name == "left" else "end_point"
        point = centerline.get(key)
        if isinstance(point, dict):
            return {"x": point.get("x"), "y": point.get("y")}
        return None
