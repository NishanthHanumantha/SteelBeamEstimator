"""Registry export for Engineering Reinforcement Contexts."""

from __future__ import annotations

from typing import Any, List


class EngineeringReinforcementContextRegistry:
    """Build project-level ERC and ownership registry exports."""

    @staticmethod
    def build_registry(
        contexts: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        entries = [
            {
                "reinforcement_context_id": ctx.get("reinforcement_context_id"),
                "beam_mark": ctx.get("beam_mark"),
                "beam_context_id": ctx.get("beam_context_id"),
                "beam_match_id": ctx.get("beam_match_id"),
                "ownership_status": ctx.get("ownership_status"),
                "engineering_status": ctx.get("engineering_status"),
            }
            for ctx in contexts
        ]
        return {
            "namespace": "ENGINEERING_REINFORCEMENT_CONTEXT",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "context_count": len(entries),
            "contexts": entries,
        }

    @staticmethod
    def build_ownership_registry(ownership_entries: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "namespace": "OWNERSHIP",
            "ownership_count": len(ownership_entries),
            "entries": list(ownership_entries),
        }

    @staticmethod
    def build_ownership_summary(
        contexts: List[dict[str, Any]],
        ownership_entries: List[dict[str, Any]],
    ) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for entry in ownership_entries:
            gtype = str(entry.get("geometry_type", "UNKNOWN"))
            by_type[gtype] = by_type.get(gtype, 0) + 1
        return {
            "phase": "Phase G.4",
            "context_count": len(contexts),
            "ownership_count": len(ownership_entries),
            "ownership_status": "RESOLVED" if contexts else "NOT_STARTED",
            "entities_by_type": by_type,
            "view_count": sum(len(c.get("owned_views", [])) for c in contexts),
            "geometry_count": sum(len(c.get("owned_geometry", [])) for c in contexts),
            "text_count": sum(len(c.get("owned_text", [])) for c in contexts),
            "leader_count": sum(len(c.get("owned_leaders", [])) for c in contexts),
            "block_count": sum(len(c.get("owned_blocks", [])) for c in contexts),
        }
