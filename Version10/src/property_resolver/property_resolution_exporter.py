"""Property resolution export helpers — Phase G.5.3.2."""

from __future__ import annotations

from typing import Any, List


class PropertyResolutionExporter:
    """Serialize property resolution artifacts for pipeline export."""

    @staticmethod
    def export_resolved(resolved: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase G.5.3.2",
            "resolved_property_count": len(resolved),
            "resolved_properties": resolved,
        }

    @staticmethod
    def export_conflicts(conflicts: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase G.5.3.2",
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
        }
