"""Registry for resolved Engineering Properties — Phase G.5.3.2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.property_resolver.property_resolver_types import (
    PREFIX_RESOLUTION_REGISTRY,
    RESOLUTION_CONFLICT,
)
from src.property_resolver.resolved_engineering_property import format_resolved_property_id


def format_resolution_registry_id(beam_mark: str = "") -> str:
    if beam_mark:
        return f"{PREFIX_RESOLUTION_REGISTRY}::{beam_mark.upper()}"
    return PREFIX_RESOLUTION_REGISTRY


class PropertyResolutionRegistry:
    """Store and export resolved engineering properties."""

    def __init__(self) -> None:
        self._sequence = 0
        self._resolved: dict[str, dict[str, Any]] = {}

    def next_id(self) -> str:
        self._sequence += 1
        return format_resolved_property_id(self._sequence)

    def register(self, resolved: dict[str, Any]) -> str:
        rid = str(resolved.get("resolved_property_id") or "")
        if not rid:
            rid = self.next_id()
            resolved["resolved_property_id"] = rid
        self._resolved[rid] = resolved
        return rid

    def lookup(self, resolved_property_id: str) -> Optional[dict[str, Any]]:
        return self._resolved.get(resolved_property_id)

    def all_resolved(self) -> List[dict[str, Any]]:
        return list(self._resolved.values())

    @staticmethod
    def build_project_registry(
        resolved_properties: List[dict[str, Any]],
        engineering_properties: List[dict[str, Any]],
        engineering_objects: List[dict[str, Any]],
        conflicts: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_strategy: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_object: Dict[str, int] = {}

        for resolved in resolved_properties:
            strategy = str(resolved.get("resolution_strategy", "UNKNOWN"))
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1
            ptype = str(resolved.get("property_type", "UNKNOWN"))
            by_type[ptype] = by_type.get(ptype, 0) + 1
            obj_id = str(resolved.get("engineering_object_id", ""))
            by_object[obj_id] = by_object.get(obj_id, 0) + 1

        return {
            "namespace": "PROPERTY_RESOLUTION",
            "phase": "Phase G.5.3.4",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": format_resolution_registry_id(),
            "resolved_property_count": len(resolved_properties),
            "resolved_property_ids": [r.get("resolved_property_id") for r in resolved_properties],
            "engineering_property_count": len(engineering_properties),
            "engineering_object_count": len(engineering_objects),
            "conflict_count": len(conflicts),
            "unresolved_conflict_count": sum(
                1
                for r in resolved_properties
                if r.get("resolution_strategy") == RESOLUTION_CONFLICT
            ),
            "resolved_by_strategy": by_strategy,
            "resolved_by_type": by_type,
            "resolved_by_object": by_object,
            "resolved_properties": list(resolved_properties),
        }
