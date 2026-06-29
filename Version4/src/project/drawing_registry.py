"""Registry of identified drawings across the project."""

from __future__ import annotations

from typing import Any, List

from src.project.drawing_identity import DrawingIdentity


class DrawingRegistry:
    """Build a project-level drawing registry from identities."""

    @staticmethod
    def build(identities: List[DrawingIdentity]) -> dict[str, Any]:
        drawings = [
            {
                "drawing_id": identity.drawing_id,
                "type": identity.drawing_type,
                "floor_id": identity.floor_id,
                "floor_name": identity.floor_name,
                "status": identity.status,
                "source_file": identity.source_file,
            }
            for identity in identities
        ]
        return {
            "phase": "Phase G.1.1",
            "drawing_count": len(drawings),
            "drawings": drawings,
        }
