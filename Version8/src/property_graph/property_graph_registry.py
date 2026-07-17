"""Property graph registry — Phase G.5.2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.property_graph.property_candidate import format_property_registry_id
from src.property_graph.property_graph_types import CANDIDATE_UNKNOWN


class PropertyGraphRegistry:
    """Store and export property candidates per ERC and project."""

    def __init__(self) -> None:
        self._sequence = 0
        self._candidates: dict[str, dict[str, Any]] = {}

    def next_id(self) -> str:
        from src.property_graph.property_candidate import format_candidate_id

        self._sequence += 1
        return format_candidate_id(self._sequence)

    def register(self, candidate: dict[str, Any]) -> str:
        cid = str(candidate.get("candidate_id", ""))
        if not cid:
            cid = self.next_id()
            candidate = dict(candidate)
            candidate["candidate_id"] = cid
        self._candidates[cid] = candidate
        return cid

    def lookup(self, candidate_id: str) -> Optional[dict[str, Any]]:
        return self._candidates.get(candidate_id)

    def all_candidates(self) -> List[dict[str, Any]]:
        return list(self._candidates.values())

    @staticmethod
    def build_project_registry(
        contexts: List[dict[str, Any]],
        candidates: List[dict[str, Any]],
        objects: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_object: Dict[str, int] = {}
        by_erc: Dict[str, int] = {}
        by_discovery: Dict[str, int] = {}

        for cand in candidates:
            ctype = str(cand.get("candidate_type", CANDIDATE_UNKNOWN))
            by_type[ctype] = by_type.get(ctype, 0) + 1
            obj_id = str(cand.get("engineering_object_id", ""))
            by_object[obj_id] = by_object.get(obj_id, 0) + 1
            erc_id = str(cand.get("owner_context_id", ""))
            by_erc[erc_id] = by_erc.get(erc_id, 0) + 1
            method = str(cand.get("discovery_method", "UNKNOWN"))
            by_discovery[method] = by_discovery.get(method, 0) + 1

        erc_registries = []
        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id")
            section = ctx.get("property_candidate_registry", {})
            ids = section.get("candidate_ids") if isinstance(section, dict) else []
            if not ids:
                ids = [
                    c["candidate_id"]
                    for c in candidates
                    if c.get("owner_context_id") == erc_id
                ]
            erc_registries.append(
                {
                    "reinforcement_context_id": erc_id,
                    "beam_mark": ctx.get("beam_mark"),
                    "registry_id": format_property_registry_id(str(ctx.get("beam_mark", ""))),
                    "candidate_count": len(ids),
                    "candidate_ids": list(ids),
                }
            )

        return {
            "namespace": "PROPERTY_GRAPH",
            "phase": "Phase G.5.2",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": "PROPERTY_GRAPH_REGISTRY",
            "candidate_count": len(candidates),
            "candidate_ids": [c.get("candidate_id") for c in candidates],
            "candidates_by_type": by_type,
            "candidates_by_object": by_object,
            "candidates_by_erc": by_erc,
            "candidates_by_discovery_method": by_discovery,
            "engineering_object_count": len(objects),
            "candidates": list(candidates),
            "erc_registries": erc_registries,
        }
