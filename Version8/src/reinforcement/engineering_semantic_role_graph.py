"""Graph export for Engineering Semantic Roles."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.engineering_semantic_role import format_semantic_role_registry_id


class EngineeringSemanticRoleGraph:
    """Build semantic role reference graph."""

    @staticmethod
    def build(
        contexts: List[dict[str, Any]],
        roles: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        nodes: List[dict[str, Any]] = []
        edges: List[dict[str, Any]] = []
        existing: set[str] = set()

        def add_node(node: dict[str, Any]) -> None:
            nid = node.get("id")
            if nid and nid not in existing:
                nodes.append(node)
                existing.add(nid)

        def add_edge(edge: dict[str, Any]) -> None:
            if edge not in edges:
                edges.append(edge)

        if project_id:
            add_node({"id": project_id, "type": "PROJECT"})

        roles_by_id = {r.get("semantic_role_id"): r for r in roles}

        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id", "")
            beam_mark = str(ctx.get("beam_mark", ""))
            if not erc_id:
                continue
            add_node({"id": erc_id, "type": "ENGINEERING_REINFORCEMENT_CONTEXT"})
            registry_id = format_semantic_role_registry_id(beam_mark)
            add_node(
                {
                    "id": registry_id,
                    "type": "SEMANTIC_ROLE_REGISTRY",
                    "parent": erc_id,
                }
            )
            add_edge(
                {
                    "from": erc_id,
                    "to": registry_id,
                    "relationship": "HAS_SEMANTIC_ROLE_REGISTRY",
                }
            )

            for role_ref in ctx.get("semantic_roles", []):
                role_id = role_ref if isinstance(role_ref, str) else role_ref.get("semantic_role_id")
                role = roles_by_id.get(role_id, {})
                if not role_id:
                    continue
                add_node(
                    {
                        "id": role_id,
                        "type": "SEMANTIC_ROLE",
                        "parent": erc_id,
                        "role_type": role.get("role_type"),
                    }
                )
                add_edge(
                    {
                        "from": erc_id,
                        "to": role_id,
                        "relationship": "HAS_SEMANTIC_ROLE",
                    }
                )
                for geom_id in role.get("geometry_asset_ids", []):
                    add_edge(
                        {
                            "from": role_id,
                            "to": geom_id,
                            "relationship": "REFERENCES",
                            "asset_kind": "geometry",
                        }
                    )
                for text_id in role.get("text_asset_ids", []):
                    add_edge(
                        {
                            "from": role_id,
                            "to": text_id,
                            "relationship": "REFERENCES",
                            "asset_kind": "text",
                        }
                    )
                for leader_id in role.get("leader_asset_ids", []):
                    add_edge(
                        {
                            "from": role_id,
                            "to": leader_id,
                            "relationship": "REFERENCES",
                            "asset_kind": "leader",
                        }
                    )
                for block_id in role.get("block_asset_ids", []):
                    add_edge(
                        {
                            "from": role_id,
                            "to": block_id,
                            "relationship": "REFERENCES",
                            "asset_kind": "block",
                        }
                    )

        return {
            "phase": "Phase G.5.0",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }
