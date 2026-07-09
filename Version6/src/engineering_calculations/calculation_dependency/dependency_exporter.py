"""Calculation dependency export helpers — Phase I.4.6."""

from __future__ import annotations

from typing import Any


class CalculationDependencyExporter:
    """Serialize dependency graph artifacts for pipeline export."""

    @staticmethod
    def export_graph(graph: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4.6",
            "graph_id": graph.get("graph_id"),
            "node_count": len(graph.get("nodes", {})),
            "graph": graph,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.4.6",
            "node_count": summary.get("node_count", 0),
            "ordered_categories": summary.get("ordered_categories", []),
            "metadata_only": summary.get("metadata_only", True),
            "validation_status": summary.get("validation_summary", {}).get("status", "SKIP"),
        }
