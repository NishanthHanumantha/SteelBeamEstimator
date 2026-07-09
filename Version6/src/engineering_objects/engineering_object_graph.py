"""Engineering Object graph derived from semantic relationships."""

from __future__ import annotations

from typing import Any, Dict, List, Set


class EngineeringObjectGraph:
    """Build directed object graph preserving semantic relationship direction."""

    @staticmethod
    def build(
        objects: List[dict[str, Any]],
        relationships: List[dict[str, Any]],
        role_to_object: Dict[str, str],
        project_id: str = "",
    ) -> dict[str, Any]:
        nodes: List[dict[str, Any]] = []
        edges: List[dict[str, Any]] = []
        existing: Set[str] = set()

        def add_node(node: dict[str, Any]) -> None:
            nid = node.get("id")
            if nid and nid not in existing:
                nodes.append(node)
                existing.add(nid)

        if project_id:
            add_node({"id": project_id, "type": "PROJECT"})

        objects_by_id = {o.get("object_id"): o for o in objects}

        for obj in objects:
            oid = obj.get("object_id")
            if not oid:
                continue
            add_node(
                {
                    "id": oid,
                    "type": "ENGINEERING_OBJECT",
                    "graph_node_id": obj.get("graph_node_id"),
                    "object_type": obj.get("object_type"),
                    "owner_context_id": obj.get("owner_context_id"),
                    "source_role_id": obj.get("source_role_id"),
                }
            )

        seen_edges: Set[tuple] = set()

        for rel in relationships:
            src_role = rel.get("source_role_id")
            tgt_role = rel.get("target_role_id")
            src_obj = role_to_object.get(src_role)
            tgt_obj = role_to_object.get(tgt_role)
            if not src_obj or not tgt_obj or src_obj == tgt_obj:
                continue
            rel_type = rel.get("relationship_type", "REFERENCES")
            edge_key = (src_obj, tgt_obj, rel_type)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "from": src_obj,
                    "to": tgt_obj,
                    "relationship": rel_type,
                    "semantic_relationship_id": rel.get("relationship_id"),
                    "direction": "outgoing",
                }
            )
            edges.append(
                {
                    "from": tgt_obj,
                    "to": src_obj,
                    "relationship": f"INCOMING_{rel_type}",
                    "semantic_relationship_id": rel.get("relationship_id"),
                    "direction": "incoming",
                }
            )

        for obj in objects:
            oid = obj.get("object_id")
            for connected in obj.get("connected_object_ids", []):
                if connected == oid or connected not in objects_by_id:
                    continue
                edge_key = (oid, connected, "CONNECTED")
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                edges.append(
                    {
                        "from": oid,
                        "to": connected,
                        "relationship": "CONNECTED_OBJECT",
                        "direction": "outgoing",
                    }
                )

        return {
            "phase": "Phase G.5.1",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "supports_traversal": True,
            "supports_neighbour_lookup": True,
            "nodes": nodes,
            "edges": edges,
        }

    @staticmethod
    def neighbour_lookup(graph: dict[str, Any], object_id: str) -> dict[str, List[str]]:
        incoming: List[str] = []
        outgoing: List[str] = []
        for edge in graph.get("edges", []):
            if edge.get("to") == object_id and edge.get("direction") == "outgoing":
                incoming.append(edge.get("from", ""))
            if edge.get("from") == object_id and edge.get("direction") == "outgoing":
                outgoing.append(edge.get("to", ""))
        return {"incoming": incoming, "outgoing": outgoing}
