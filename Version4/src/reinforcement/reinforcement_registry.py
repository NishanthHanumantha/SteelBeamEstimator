"""Build reinforcement registry exports."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.reinforcement_workspace import ReinforcementWorkspace


class ReinforcementRegistry:
    """Serialize loaded reinforcement documents and workspaces."""

    @staticmethod
    def build(workspaces: List[ReinforcementWorkspace]) -> dict[str, Any]:
        documents: List[dict[str, Any]] = []
        for ws in workspaces:
            doc = ws.document
            documents.append(
                {
                    "document_id": doc.document_id,
                    "workspace_id": ws.workspace_id,
                    "floor_id": ws.floor_id,
                    "floor": ws.floor_slug,
                    "drawing_name": doc.drawing_name,
                    "source_file": doc.source_file,
                    "status": ws.status,
                    "entity_count": doc.entity_count,
                    "layer_count": doc.layer_count,
                    "metadata": dict(doc.metadata),
                }
            )
        return {
            "phase": "Phase G.1",
            "document_count": len(documents),
            "documents": documents,
        }
