"""Graph export for Engineering Semantic Relationships."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.engineering_semantic_relationship import (
    format_semantic_relationship_registry_id,
)


class EngineeringSemanticRelationshipGraph:
    """Build role-to-role relationship graph per ERC."""

    @staticmethod
    def build(
        contexts: List[dict[str, Any]],
        relationships: List[dict[str, Any]],
        roles: List[dict[str, Any]],
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

        if project_id:
            add_node({"id": project_id, "type": "PROJECT"})

        roles_by_id = {r.get("semantic_role_id"): r for r in roles}
        rels_by_erc: dict[str, list] = {}
        for rel in relationships:
            erc_id = rel.get("owner_context_id", "")
            rels_by_erc.setdefault(erc_id, []).append(rel)

        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id", "")
            beam_mark = str(ctx.get("beam_mark", ""))
            if not erc_id:
                continue
            add_node({"id": erc_id, "type": "ENGINEERING_REINFORCEMENT_CONTEXT"})
            registry_id = format_semantic_relationship_registry_id(beam_mark)
            add_node(
                {
                    "id": registry_id,
                    "type": "SEMANTIC_RELATIONSHIP_REGISTRY",
                    "parent": erc_id,
                }
            )
            edges.append(
                {
                    "from": erc_id,
                    "to": registry_id,
                    "relationship": "HAS_SEMANTIC_RELATIONSHIP_REGISTRY",
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
                        "engineering_priority": role.get("engineering_priority"),
                    }
                )
                edges.append(
                    {
                        "from": erc_id,
                        "to": role_id,
                        "relationship": "HAS_SEMANTIC_ROLE",
                    }
                )

            for rel in rels_by_erc.get(erc_id, []):
                rel_id = rel.get("relationship_id")
                if not rel_id:
                    continue
                add_node(
                    {
                        "id": rel_id,
                        "type": "SEMANTIC_RELATIONSHIP",
                        "parent": erc_id,
                        "relationship_type": rel.get("relationship_type"),
                    }
                )
                edges.append(
                    {
                        "from": rel.get("source_role_id"),
                        "to": rel_id,
                        "relationship": "HAS_RELATIONSHIP",
                    }
                )
                edges.append(
                    {
                        "from": rel_id,
                        "to": rel.get("target_role_id"),
                        "relationship": rel.get("relationship_type"),
                    }
                )

        return {
            "phase": "Phase G.5.0.1",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }
