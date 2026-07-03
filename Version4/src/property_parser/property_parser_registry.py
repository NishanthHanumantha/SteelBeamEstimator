"""Registry for parsed Engineering Properties — Phase G.5.3.1."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.property_parser.engineering_property import format_parser_registry_id
from src.property_parser.property_parser_types import (
    PARSE_STATUS_PARSED,
    PARSE_STATUS_UNPARSED,
    PROP_UNKNOWN,
)


class PropertyParserRegistry:
    """Store and export parsed engineering properties."""

    def __init__(self) -> None:
        self._sequence = 0
        self._properties: dict[str, dict[str, Any]] = {}
        self._processed_candidates: set[str] = set()

    def next_id(self) -> str:
        from src.property_parser.engineering_property import format_property_id

        self._sequence += 1
        return format_property_id(self._sequence)

    def register(self, prop: dict[str, Any]) -> str:
        pid = str(prop.get("property_id") or "")
        if not pid:
            pid = self.next_id()
            prop["property_id"] = pid
        self._properties[pid] = prop
        cid = prop.get("candidate_id")
        if cid:
            self._processed_candidates.add(str(cid))
        return pid

    def mark_candidate_processed(self, candidate_id: str) -> None:
        self._processed_candidates.add(candidate_id)

    def lookup(self, property_id: str) -> Optional[dict[str, Any]]:
        return self._properties.get(property_id)

    def all_properties(self) -> List[dict[str, Any]]:
        return list(self._properties.values())

    def processed_candidate_ids(self) -> set[str]:
        return set(self._processed_candidates)

    @staticmethod
    def build_project_registry(
        properties: List[dict[str, Any]],
        candidates: List[dict[str, Any]],
        processed_candidate_ids: set[str],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {PARSE_STATUS_PARSED: 0, PARSE_STATUS_UNPARSED: 0}
        by_object: Dict[str, int] = {}

        for prop in properties:
            ptype = str(prop.get("property_type", PROP_UNKNOWN))
            by_type[ptype] = by_type.get(ptype, 0) + 1
            status = str(prop.get("parse_status", PARSE_STATUS_UNPARSED))
            by_status[status] = by_status.get(status, 0) + 1
            obj_id = str(prop.get("engineering_object_id", ""))
            by_object[obj_id] = by_object.get(obj_id, 0) + 1

        return {
            "namespace": "PROPERTY_PARSER",
            "phase": "Phase G.5.3.1",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": format_parser_registry_id(),
            "property_count": len(properties),
            "property_ids": [p.get("property_id") for p in properties],
            "candidates_processed": len(processed_candidate_ids),
            "candidate_count": len(candidates),
            "properties_by_type": by_type,
            "properties_by_status": by_status,
            "properties_by_object": by_object,
            "properties": list(properties),
        }
