"""Registry of drawing sets across the project."""

from __future__ import annotations

from typing import Any, List

from src.project.drawing_set import DrawingSet


class DrawingSetRegistry:
    """Build project-level drawing set registry."""

    @staticmethod
    def build(drawing_sets: List[DrawingSet]) -> dict[str, Any]:
        entries = [
            {
                "drawing_set_id": ds.drawing_set_id,
                "floor": ds.floor_name,
                "floor_id": ds.floor_id,
                "status": ds.status,
                "drawings": sum(
                    1 for key, value in ds.drawings.items()
                    if key != "general_notes" and value
                ),
            }
            for ds in drawing_sets
        ]
        return {
            "phase": "Phase G.1.2",
            "drawing_set_count": len(entries),
            "drawing_sets": entries,
        }
