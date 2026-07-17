"""Property graph export helpers — Phase G.5.2."""

from __future__ import annotations

from typing import Any, List


class PropertyGraphExporter:
    """Serialize property graph artifacts for pipeline export."""

    @staticmethod
    def export_candidates(candidates: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase G.5.2",
            "candidate_count": len(candidates),
            "candidates": candidates,
        }
