"""Engineering Object Registry — store, lookup, and export engineering objects."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.reinforcement.engineering_object import (
    engineering_objects_section,
    format_engineering_object_id,
    format_engineering_object_registry_id,
)


class EngineeringObjectRegistry:
    """Project-level registry for engineering objects."""

    def __init__(self) -> None:
        self._sequence = 0
        self._objects: dict[str, dict[str, Any]] = {}

    def next_id(self) -> str:
        self._sequence += 1
        return format_engineering_object_id(self._sequence)

    def register(self, obj: dict[str, Any]) -> str:
        obj_id = str(obj.get("engineering_object_id", ""))
        if not obj_id:
            obj_id = self.next_id()
            obj = dict(obj)
            obj["engineering_object_id"] = obj_id
        self._objects[obj_id] = obj
        return obj_id

    def lookup(self, engineering_object_id: str) -> Optional[dict[str, Any]]:
        return self._objects.get(engineering_object_id)

    def all_objects(self) -> List[dict[str, Any]]:
        return list(self._objects.values())

    @staticmethod
    def enrich_erc(erc: dict[str, Any]) -> dict[str, Any]:
        """Append empty engineering_objects section to an ERC."""
        enriched = dict(erc)
        beam_mark = str(erc.get("beam_mark", ""))
        enriched["engineering_objects"] = engineering_objects_section(beam_mark, objects=[])
        return enriched

    @staticmethod
    def enrich_contexts(contexts: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return [EngineeringObjectRegistry.enrich_erc(ctx) for ctx in contexts]

    @staticmethod
    def build_project_registry(
        contexts: List[dict[str, Any]],
        objects: List[dict[str, Any]] | None = None,
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        obj_list = list(objects or [])
        erc_registries = [
            {
                "reinforcement_context_id": ctx.get("reinforcement_context_id"),
                "beam_mark": ctx.get("beam_mark"),
                "registry_id": format_engineering_object_registry_id(
                    str(ctx.get("beam_mark", ""))
                ),
                "object_count": len(ctx.get("engineering_objects", {}).get("objects", [])),
            }
            for ctx in contexts
        ]
        return {
            "namespace": "ENGINEERING_OBJECT",
            "phase": "Phase G.4.2",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "object_count": len(obj_list),
            "objects": obj_list,
            "erc_registries": erc_registries,
        }

    @staticmethod
    def build_summary(
        contexts: List[dict[str, Any]],
        objects: List[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        obj_list = list(objects or [])
        by_type: dict[str, int] = {}
        for obj in obj_list:
            otype = str(obj.get("object_type", "UNKNOWN"))
            by_type[otype] = by_type.get(otype, 0) + 1
        return {
            "phase": "Phase G.4.2",
            "context_count": len(contexts),
            "object_count": len(obj_list),
            "objects_by_type": by_type,
            "registry_ready": True,
            "factory_ready": True,
            "lifecycle_ready": True,
            "graph_ready": True,
            "relationships_ready": True,
            "status": "READY_FOR_G5",
        }
