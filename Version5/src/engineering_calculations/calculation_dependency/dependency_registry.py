"""Calculation dependency registry — Phase I.4.6."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_dependency.dependency_types import (
    NAMESPACE_CALCULATION_DEPENDENCY,
)


def format_dependency_registry_id() -> str:
    return "CALC_DEPENDENCY_REGISTRY"


class CalculationDependencyRegistry:
    """Registry wrapper for dependency graph metadata."""

    @staticmethod
    def build_project_registry(
        graph: dict[str, Any],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        nodes = graph.get("nodes", {})
        return {
            "namespace": NAMESPACE_CALCULATION_DEPENDENCY,
            "phase": "Phase I.4.6",
            "registry_id": format_dependency_registry_id(),
            "graph_id": graph.get("graph_id"),
            "node_count": len(nodes),
            "ordered_categories": graph.get("ordered_categories", []),
            "metadata_only": True,
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }
