"""Registry for Engineering Semantic Roles."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.reinforcement.engineering_semantic_role_types import ROLE_UNKNOWN
from src.reinforcement.engineering_semantic_role import (
    format_semantic_role_id,
    format_semantic_role_registry_id,
    semantic_role_registry_section,
)


class EngineeringSemanticRoleRegistry:
    """Store and export semantic roles per ERC and project."""

    def __init__(self) -> None:
        self._sequence = 0
        self._roles: dict[str, dict[str, Any]] = {}

    def next_id(self) -> str:
        self._sequence += 1
        return format_semantic_role_id(self._sequence)

    def register(self, role: dict[str, Any]) -> str:
        role_id = str(role.get("semantic_role_id", ""))
        if not role_id:
            role_id = self.next_id()
            role = dict(role)
            role["semantic_role_id"] = role_id
        self._roles[role_id] = role
        return role_id

    def lookup(self, semantic_role_id: str) -> Optional[dict[str, Any]]:
        return self._roles.get(semantic_role_id)

    def all_roles(self) -> List[dict[str, Any]]:
        return list(self._roles.values())

    @staticmethod
    def build_project_registry(
        contexts: List[dict[str, Any]],
        roles: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        erc_registries = [
            {
                "reinforcement_context_id": ctx.get("reinforcement_context_id"),
                "beam_mark": ctx.get("beam_mark"),
                "registry_id": format_semantic_role_registry_id(str(ctx.get("beam_mark", ""))),
                "role_count": len(ctx.get("semantic_roles", [])),
            }
            for ctx in contexts
        ]
        by_type: Dict[str, int] = {}
        for role in roles:
            rtype = str(role.get("role_type", ROLE_UNKNOWN))
            by_type[rtype] = by_type.get(rtype, 0) + 1
        return {
            "namespace": "ENGINEERING_SEMANTIC_ROLE",
            "phase": "Phase G.5.0",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "role_count": len(roles),
            "roles_by_type": by_type,
            "roles": list(roles),
            "erc_registries": erc_registries,
        }

    @staticmethod
    def build_summary(
        contexts: List[dict[str, Any]],
        roles: List[dict[str, Any]],
        unknown_threshold: float = 0.15,
    ) -> dict[str, Any]:
        from src.reinforcement.engineering_semantic_role_types import ROLE_UNKNOWN

        by_type: Dict[str, int] = {}
        for role in roles:
            rtype = str(role.get("role_type", ROLE_UNKNOWN))
            by_type[rtype] = by_type.get(rtype, 0) + 1
        total = len(roles)
        unknown_count = by_type.get(ROLE_UNKNOWN, 0)
        unknown_ratio = unknown_count / total if total else 0.0
        return {
            "phase": "Phase G.5.0",
            "context_count": len(contexts),
            "role_count": total,
            "roles_by_type": by_type,
            "unknown_count": unknown_count,
            "unknown_ratio": round(unknown_ratio, 4),
            "unknown_below_threshold": unknown_ratio <= unknown_threshold,
            "status": "ROLE_CLASSIFIED",
        }
