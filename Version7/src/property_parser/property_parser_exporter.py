"""Property parser export helpers — Phase G.5.3.1."""

from __future__ import annotations

from typing import Any, List


class PropertyParserExporter:
    """Serialize property parser artifacts for pipeline export."""

    @staticmethod
    def export_properties(properties: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase G.5.3.1",
            "property_count": len(properties),
            "properties": properties,
        }

    @staticmethod
    def export_unparsed(unparsed: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase G.5.3.1",
            "unparsed_count": len(unparsed),
            "candidates": unparsed,
        }
