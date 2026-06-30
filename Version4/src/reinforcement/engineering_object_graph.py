"""Engineering Object Graph — reference-only graph for engineering objects."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.engineering_object import format_engineering_object_registry_id
from src.reinforcement.engineering_reinforcement_context import format_engineering_results_id


PREFIX_OBJECT_GRAPH = "ENG_OBJ_GRAPH"


class EngineeringObjectGraph:
    """Build engineering object graph with reference nodes only."""

    @staticmethod
    def build(
        contexts: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
        objects: List[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        nodes: List[dict[str, Any]] = []
        edges: List[dict[str, Any]] = []
        existing_ids: set[str] = set()

        def add_node(node: dict[str, Any]) -> None:
            nid = node.get("id")
            if nid and nid not in existing_ids:
                nodes.append(node)
                existing_ids.add(nid)

        def add_edge(edge: dict[str, Any]) -> None:
            if edge not in edges:
                edges.append(edge)

        if project_id:
            add_node({"id": project_id, "type": "PROJECT"})
            graph_root = f"{PREFIX_OBJECT_GRAPH}::{project_id}"
            add_node({"id": graph_root, "type": "ENGINEERING_OBJECT_GRAPH", "parent": project_id})
            add_edge(
                {
                    "from": project_id,
                    "to": graph_root,
                    "relationship": "HAS_ENGINEERING_OBJECT_GRAPH",
                }
            )

        registry_root = f"{PREFIX_OBJECT_GRAPH}::REGISTRY"
        add_node({"id": registry_root, "type": "ENGINEERING_OBJECT_REGISTRY"})
        if project_id:
            add_edge(
                {
                    "from": project_id,
                    "to": registry_root,
                    "relationship": "HAS_ENGINEERING_OBJECT_REGISTRY",
                }
            )

        for dm in drawing_models:
            drawing_id = dm.get("drawing_id", "")
            if drawing_id:
                add_node({"id": drawing_id, "type": "DRAWING", "parent": project_id})
                if project_id:
                    add_edge(
                        {
                            "from": project_id,
                            "to": drawing_id,
                            "relationship": "HAS_DRAWING",
                        }
                    )
                add_edge(
                    {
                        "from": drawing_id,
                        "to": registry_root,
                        "relationship": "HAS_ENGINEERING_OBJECT_REGISTRY",
                    }
                )

        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id", "")
            beam_mark = str(ctx.get("beam_mark", ""))
            if not erc_id:
                continue

            add_node({"id": erc_id, "type": "ENGINEERING_REINFORCEMENT_CONTEXT"})
            drawing_id = ctx.get("drawing_id", "")
            if drawing_id:
                add_edge(
                    {
                        "from": drawing_id,
                        "to": erc_id,
                        "relationship": "HAS_ERC",
                    }
                )

            obj_registry_id = format_engineering_object_registry_id(beam_mark)
            add_node(
                {
                    "id": obj_registry_id,
                    "type": "ENGINEERING_OBJECT_REGISTRY",
                    "parent": erc_id,
                    "beam_mark": beam_mark,
                }
            )
            add_edge(
                {
                    "from": erc_id,
                    "to": obj_registry_id,
                    "relationship": "HAS_ENGINEERING_OBJECT_REGISTRY",
                }
            )
            add_edge(
                {
                    "from": obj_registry_id,
                    "to": registry_root,
                    "relationship": "BELONGS_TO",
                }
            )

            results_id = format_engineering_results_id(beam_mark)
            add_edge(
                {
                    "from": obj_registry_id,
                    "to": results_id,
                    "relationship": "FEEDS",
                }
            )

            for obj in ctx.get("engineering_objects", {}).get("objects", []):
                if isinstance(obj, str):
                    obj_id = obj
                    obj_data = next(
                        (o for o in objects or [] if o.get("engineering_object_id") == obj_id),
                        {},
                    )
                else:
                    obj_data = obj
                    obj_id = obj.get("engineering_object_id")
                if not obj_id:
                    continue
                if obj_id not in existing_ids:
                    add_node(
                        {
                            "id": obj_id,
                            "type": "ENGINEERING_OBJECT",
                            "parent": erc_id,
                            "object_type": obj_data.get("object_type"),
                        }
                    )
                    existing_ids.add(obj_id)
                add_edge(
                    {
                        "from": erc_id,
                        "to": obj_id,
                        "relationship": "HAS_ENGINEERING_OBJECT",
                    }
                )
                add_edge(
                    {
                        "from": obj_id,
                        "to": obj_registry_id,
                        "relationship": "BELONGS_TO",
                    }
                )
                refs = obj_data.get("asset_references", {})
                for geom_id in refs.get("geometry", []):
                    ref_id = f"ASSET_REF::{obj_id}::{geom_id}"
                    add_node(
                        {
                            "id": ref_id,
                            "type": "ASSET_REFERENCE",
                            "parent": obj_id,
                            "asset_id": geom_id,
                        }
                    )
                    add_edge(
                        {
                            "from": obj_id,
                            "to": ref_id,
                            "relationship": "REFERENCES",
                        }
                    )
                    add_edge(
                        {
                            "from": ref_id,
                            "to": geom_id,
                            "relationship": "RESOLVES_TO",
                        }
                    )
                for text_id in refs.get("text", []):
                    ref_id = f"ASSET_REF::{obj_id}::{text_id}"
                    add_node(
                        {
                            "id": ref_id,
                            "type": "ASSET_REFERENCE",
                            "parent": obj_id,
                            "asset_id": text_id,
                        }
                    )
                    add_edge(
                        {
                            "from": obj_id,
                            "to": ref_id,
                            "relationship": "REFERENCES",
                        }
                    )
                    add_edge(
                        {
                            "from": ref_id,
                            "to": text_id,
                            "relationship": "RESOLVES_TO",
                        }
                    )
                for leader_id in refs.get("leaders", []):
                    ref_id = f"ASSET_REF::{obj_id}::{leader_id}"
                    add_node(
                        {
                            "id": ref_id,
                            "type": "ASSET_REFERENCE",
                            "parent": obj_id,
                            "asset_id": leader_id,
                        }
                    )
                    add_edge(
                        {
                            "from": obj_id,
                            "to": ref_id,
                            "relationship": "REFERENCES",
                        }
                    )
                    add_edge(
                        {
                            "from": ref_id,
                            "to": leader_id,
                            "relationship": "RESOLVES_TO",
                        }
                    )

        for obj in objects or []:
            obj_id = obj.get("engineering_object_id")
            if obj_id and obj_id not in existing_ids:
                add_node(
                    {
                        "id": obj_id,
                        "type": "ENGINEERING_OBJECT",
                        "object_type": obj.get("object_type"),
                    }
                )

        return {
            "phase": "Phase G.4.2",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }
