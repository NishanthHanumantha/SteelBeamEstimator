"""Registry for Engineering Semantic Relationships."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.reinforcement.engineering_semantic_relationship import (
    format_semantic_relationship_id,
    format_semantic_relationship_registry_id,
)
from src.reinforcement.engineering_semantic_relationship_types import REL_UNKNOWN


class EngineeringSemanticRelationshipRegistry:
    """Store and export semantic relationships per ERC and project."""

    def __init__(self) -> None:
        self._sequence = 0
        self._relationships: dict[str, dict[str, Any]] = {}

    def next_id(self) -> str:
        self._sequence += 1
        return format_semantic_relationship_id(self._sequence)

    def register(self, relationship: dict[str, Any]) -> str:
        rel_id = str(relationship.get("relationship_id", ""))
        if not rel_id:
            rel_id = self.next_id()
            relationship = dict(relationship)
            relationship["relationship_id"] = rel_id
        self._relationships[rel_id] = relationship
        return rel_id

    def lookup(self, relationship_id: str) -> Optional[dict[str, Any]]:
        return self._relationships.get(relationship_id)

    def all_relationships(self) -> List[dict[str, Any]]:
        return list(self._relationships.values())

    def relationships_for_role(self, role_id: str) -> List[dict[str, Any]]:
        return [
            r
            for r in self._relationships.values()
            if r.get("source_role_id") == role_id or r.get("target_role_id") == role_id
        ]

    @staticmethod
    def build_project_registry(
        contexts: List[dict[str, Any]],
        relationships: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        erc_registries = [
            {
                "reinforcement_context_id": ctx.get("reinforcement_context_id"),
                "beam_mark": ctx.get("beam_mark"),
                "registry_id": format_semantic_relationship_registry_id(
                    str(ctx.get("beam_mark", ""))
                ),
                "relationship_count": len(ctx.get("semantic_relationships", [])),
            }
            for ctx in contexts
        ]
        by_type: Dict[str, int] = {}
        for rel in relationships:
            rtype = str(rel.get("relationship_type", REL_UNKNOWN))
            by_type[rtype] = by_type.get(rtype, 0) + 1
        return {
            "namespace": "ENGINEERING_SEMANTIC_RELATIONSHIP",
            "phase": "Phase G.5.0.1",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "relationship_count": len(relationships),
            "relationships_by_type": by_type,
            "relationships": list(relationships),
            "erc_registries": erc_registries,
        }

    @staticmethod
    def build_summary(
        contexts: List[dict[str, Any]],
        relationships: List[dict[str, Any]],
        unknown_threshold: float = 0.15,
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        for rel in relationships:
            rtype = str(rel.get("relationship_type", REL_UNKNOWN))
            by_type[rtype] = by_type.get(rtype, 0) + 1
        total = len(relationships)
        unknown_count = by_type.get(REL_UNKNOWN, 0)
        unknown_ratio = unknown_count / total if total else 0.0
        return {
            "phase": "Phase G.5.0.1",
            "context_count": len(contexts),
            "relationship_count": total,
            "relationships_by_type": by_type,
            "unknown_count": unknown_count,
            "unknown_ratio": round(unknown_ratio, 4),
            "unknown_below_threshold": unknown_ratio <= unknown_threshold,
            "status": "RELATIONSHIP_CLASSIFIED",
        }
