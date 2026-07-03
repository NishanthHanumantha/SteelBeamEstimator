"""Registry for graph-instantiated Engineering Objects."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.engineering_objects.engineering_object import (
    erc_engineering_object_count,
    format_object_registry_id,
)
from src.engineering_objects.engineering_object_types import (
    ENGINEERING_STATUS_OBJECT_CREATED,
    LIFECYCLE_OBJECT_CREATED,
    OBJECT_UNKNOWN,
)


class EngineeringObjectRegistry:
    """Store and export engineering objects per ERC and project."""

    def __init__(self) -> None:
        self._sequence = 0
        self._objects: dict[str, dict[str, Any]] = {}

    def next_id(self) -> str:
        from src.engineering_objects.engineering_object import format_object_id

        self._sequence += 1
        return format_object_id(self._sequence)

    def register(self, obj: dict[str, Any]) -> str:
        obj_id = str(obj.get("object_id") or obj.get("engineering_object_id", ""))
        if not obj_id:
            obj_id = self.next_id()
            obj = dict(obj)
            obj["object_id"] = obj_id
            obj["engineering_object_id"] = obj_id
        self._objects[obj_id] = obj
        return obj_id

    def lookup(self, object_id: str) -> Optional[dict[str, Any]]:
        return self._objects.get(object_id)

    def all_objects(self) -> List[dict[str, Any]]:
        return list(self._objects.values())

    @staticmethod
    def build_project_registry(
        contexts: List[dict[str, Any]],
        objects: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_lifecycle: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_confidence: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}

        for obj in objects:
            otype = str(obj.get("object_type", OBJECT_UNKNOWN))
            by_type[otype] = by_type.get(otype, 0) + 1
            lifecycle = str(obj.get("lifecycle", LIFECYCLE_OBJECT_CREATED))
            by_lifecycle[lifecycle] = by_lifecycle.get(lifecycle, 0) + 1
            status = str(obj.get("engineering_status", ENGINEERING_STATUS_OBJECT_CREATED))
            by_status[status] = by_status.get(status, 0) + 1
            conf = float(obj.get("confidence", 0.0))
            if conf >= 0.85:
                by_confidence["high"] += 1
            elif conf >= 0.6:
                by_confidence["medium"] += 1
            else:
                by_confidence["low"] += 1

        erc_registries = [
            {
                "reinforcement_context_id": ctx.get("reinforcement_context_id"),
                "beam_mark": ctx.get("beam_mark"),
                "registry_id": format_object_registry_id(str(ctx.get("beam_mark", ""))),
                "object_count": erc_engineering_object_count(ctx),
            }
            for ctx in contexts
        ]

        return {
            "namespace": "ENGINEERING_OBJECT",
            "phase": "Phase G.5.1",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": "ENGINEERING_OBJECT_REGISTRY",
            "object_count": len(objects),
            "object_ids": [o.get("object_id") for o in objects],
            "objects_by_type": by_type,
            "objects_by_lifecycle": by_lifecycle,
            "objects_by_engineering_status": by_status,
            "objects_by_confidence_bucket": by_confidence,
            "objects": list(objects),
            "erc_registries": erc_registries,
        }
