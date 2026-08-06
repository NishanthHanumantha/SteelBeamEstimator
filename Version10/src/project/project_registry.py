"""Build project registry exports."""

from __future__ import annotations

from typing import Any, Dict, List

from src.project.project_workspace import ProjectWorkspace


class ProjectRegistry:
    """Serialize project workspace into registry format."""

    @staticmethod
    def build(workspace: ProjectWorkspace) -> dict[str, Any]:
        floor_names = [
            f.get("floor_name") or f.get("floor_id", "")
            for f in workspace.floors
        ]
        return {
            "phase": "Phase F.7",
            "project": workspace.project_name,
            "project_id": workspace.project_id,
            "general_notes": workspace.general_notes.get("document_id", "GN-001"),
            "floors": floor_names,
            "floor_ids": [f.get("floor_id") for f in workspace.floors],
            "services": workspace.services.get("service_id"),
        }

    @staticmethod
    def build_floor_registry(floors: List[dict[str, Any]]) -> dict[str, Any]:
        entries: List[dict[str, Any]] = []
        for floor in floors:
            framing = floor.get("framing_plan", {})
            reinforcement_ws = floor.get("reinforcement_workspace", {})
            reinforcement_status = reinforcement_ws.get("status", "NOT_LOADED")
            entries.append(
                {
                    "floor_id": floor.get("floor_id"),
                    "floor_name": floor.get("floor_name"),
                    "framing": framing.get("status", "NOT_LOADED"),
                    "reinforcement": reinforcement_status,
                    "beam_count": framing.get("beam_count", len(floor.get("beam_contexts", []))),
                }
            )
        return {
            "phase": "Phase F.7",
            "floor_count": len(entries),
            "entries": entries,
        }
