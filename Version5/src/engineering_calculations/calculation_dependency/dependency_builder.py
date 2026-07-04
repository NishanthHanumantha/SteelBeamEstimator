"""Calculation dependency builder — Phase I.4.6."""

from __future__ import annotations

from typing import Any, Tuple

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_dependency.dependency_registry import (
    CalculationDependencyRegistry,
)


def calculation_dependency_applied(model: dict[str, Any]) -> bool:
    registry = model.get("calculation_dependency_registry", {})
    if registry.get("phase") == "Phase I.4.6" and registry.get("node_count", 0) >= 0:
        return True
    if model.get("calculation_dependency_graph") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("calculation_dependency_complete"))


class CalculationDependencyBuilder:
    """Build metadata-only calculation dependency graph."""

    def build(
        self,
        drawing_models: list[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[dict[str, Any], dict[str, Any]]:
        graph = CalculationDependencyGraph.from_spec()
        graph_dict = graph.to_dict()

        primary = drawing_models[0] if drawing_models else {}
        registry = CalculationDependencyRegistry.build_project_registry(
            graph_dict,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        exports = {
            "calculation_dependency_graph": graph_dict,
            "calculation_dependency_registry": registry,
        }
        return graph_dict, exports
