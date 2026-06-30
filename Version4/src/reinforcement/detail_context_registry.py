"""Registry for engineering detail contexts."""

from __future__ import annotations

from typing import Any, List


class DetailContextRegistry:
    """Build a project-level detail context registry."""

    @staticmethod
    def build(
        detail_contexts: List[dict[str, Any]],
        drawing_id: str = "",
        floor_id: str = "",
    ) -> dict[str, Any]:
        entries = [
            {
                "detail_context_id": ctx.get("detail_context_id"),
                "detail_type": ctx.get("detail_type"),
                "region_id": ctx.get("region_id"),
                "beam_marks": ctx.get("beam_marks", []),
                "view_count": ctx.get("view_count", 0),
                "drawing_id": ctx.get("metadata", {}).get("drawing_id", drawing_id),
            }
            for ctx in detail_contexts
        ]
        return {
            "namespace": "DETAIL_CTX",
            "drawing_id": drawing_id,
            "floor_id": floor_id,
            "detail_context_count": len(entries),
            "detail_contexts": entries,
        }
