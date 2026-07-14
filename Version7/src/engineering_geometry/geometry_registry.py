"""Geometry Association registry — Phase H.2."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_geometry.geometry_reference import format_geometry_association_id, format_geometry_registry_id


class GeometryAssociationRegistry:
    """Sequence registry for geometry associations."""

    def __init__(self) -> None:
        self._sequence = 0
        self._associations: dict[str, dict[str, Any]] = {}
        self._processed_specification_ids: List[str] = []

    def next_id(self) -> str:
        self._sequence += 1
        return format_geometry_association_id(self._sequence)

    def register(self, association: dict[str, Any]) -> str:
        assoc_id = str(association.get("association_id") or "")
        if not assoc_id:
            assoc_id = self.next_id()
            association["association_id"] = assoc_id
        self._associations[assoc_id] = association
        return assoc_id

    def mark_processed(self, specification_id: str) -> None:
        if specification_id and specification_id not in self._processed_specification_ids:
            self._processed_specification_ids.append(specification_id)

    def all_associations(self) -> List[dict[str, Any]]:
        return list(self._associations.values())

    @property
    def processed_specification_ids(self) -> List[str]:
        return list(self._processed_specification_ids)

    @staticmethod
    def build_project_registry(
        associations: List[dict[str, Any]],
        specifications: List[dict[str, Any]],
        processed_specification_ids: List[str],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_status: Dict[str, int] = {}
        by_beam: Dict[str, int] = {}
        for assoc in associations:
            status = str(assoc.get("association_status", "UNKNOWN"))
            by_status[status] = by_status.get(status, 0) + 1
            beam = str(assoc.get("beam_id", ""))
            by_beam[beam] = by_beam.get(beam, 0) + 1

        return {
            "namespace": "GEOMETRY_ASSOCIATION",
            "phase": "Phase H.2",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": format_geometry_registry_id(),
            "association_count": len(associations),
            "association_ids": [item.get("association_id") for item in associations],
            "specification_count": len(specifications),
            "processed_specification_ids": list(processed_specification_ids),
            "associations_by_status": by_status,
            "associations_by_beam": by_beam,
            "associations": list(associations),
        }
