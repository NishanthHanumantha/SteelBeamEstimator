"""Registry for Engineering Specifications — Phase H.1."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.engineering_specifications.engineering_specification import format_specification_id
from src.engineering_specifications.specification_types import (
    PREFIX_SPECIFICATION_REGISTRY,
)


def format_registry_id(beam_mark: str = "") -> str:
    if beam_mark:
        return f"{PREFIX_SPECIFICATION_REGISTRY}::{beam_mark.upper()}"
    return PREFIX_SPECIFICATION_REGISTRY


class SpecificationRegistry:
    """Sequence-based registry for engineering specifications."""

    def __init__(self) -> None:
        self._sequence = 0
        self._specifications: dict[str, dict[str, Any]] = {}
        self._processed_object_ids: List[str] = []
        self._skipped_object_ids: List[str] = []

    def next_id(self) -> str:
        self._sequence += 1
        return format_specification_id(self._sequence)

    def register(self, specification: dict[str, Any]) -> str:
        spec_id = str(specification.get("specification_id") or "")
        if not spec_id:
            spec_id = self.next_id()
            specification["specification_id"] = spec_id
        self._specifications[spec_id] = specification
        return spec_id

    def mark_processed(self, engineering_object_id: str, created: bool) -> None:
        if engineering_object_id not in self._processed_object_ids:
            self._processed_object_ids.append(engineering_object_id)
        if created:
            if engineering_object_id in self._skipped_object_ids:
                self._skipped_object_ids.remove(engineering_object_id)
        elif engineering_object_id not in self._skipped_object_ids:
            self._skipped_object_ids.append(engineering_object_id)

    def lookup(self, specification_id: str) -> Optional[dict[str, Any]]:
        return self._specifications.get(specification_id)

    def all_specifications(self) -> List[dict[str, Any]]:
        return list(self._specifications.values())

    @property
    def processed_object_ids(self) -> List[str]:
        return list(self._processed_object_ids)

    @property
    def skipped_object_ids(self) -> List[str]:
        return list(self._skipped_object_ids)

    @staticmethod
    def build_project_registry(
        specifications: List[dict[str, Any]],
        engineering_objects: List[dict[str, Any]],
        processed_object_ids: List[str],
        skipped_object_ids: List[str],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_beam: Dict[str, int] = {}

        for spec in specifications:
            spec_type = str(spec.get("reinforcement_type", "UNKNOWN"))
            by_type[spec_type] = by_type.get(spec_type, 0) + 1
            status = str(spec.get("specification_status", "UNKNOWN"))
            by_status[status] = by_status.get(status, 0) + 1
            beam_id = str(spec.get("beam_id", ""))
            by_beam[beam_id] = by_beam.get(beam_id, 0) + 1

        return {
            "namespace": "ENGINEERING_SPECIFICATION",
            "phase": "Phase H.1",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": format_registry_id(),
            "specification_count": len(specifications),
            "specification_ids": [spec.get("specification_id") for spec in specifications],
            "engineering_object_count": len(engineering_objects),
            "processed_object_count": len(processed_object_ids),
            "skipped_object_count": len(skipped_object_ids),
            "processed_object_ids": list(processed_object_ids),
            "skipped_object_ids": list(skipped_object_ids),
            "specifications_by_type": by_type,
            "specifications_by_status": by_status,
            "specifications_by_beam": by_beam,
            "specifications": list(specifications),
        }
