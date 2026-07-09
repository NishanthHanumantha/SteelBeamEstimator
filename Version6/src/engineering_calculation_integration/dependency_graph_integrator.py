"""Integrate recovered bars into the production dependency graph."""

from __future__ import annotations

from typing import Any, List


class DependencyGraphIntegrator:
    """Ensure dependency graph exists and report recovered bar linkage."""

    def integrate(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        project_id: str,
        recovered_bar_ids: List[str],
    ) -> dict[str, Any]:
        from src.engineering_calculations.calculation_dependency.dependency_builder import (
            CalculationDependencyBuilder,
        )

        if model.get("calculation_dependency_graph"):
            graph = model["calculation_dependency_graph"]
            source = "EXISTING_PRODUCTION_GRAPH"
        else:
            _, exports = CalculationDependencyBuilder().build(drawing_models, project_id=project_id)
            model.update(exports)
            graph = model.get("calculation_dependency_graph") or {}
            source = "PRODUCTION_DEPENDENCY_BUILDER"

        indexed = sum(
            1
            for bar in model.get("reinforcement_bars") or []
            if str(bar.get("bar_id") or "") in set(recovered_bar_ids)
            and (bar.get("calculation_index") or {}).get("references")
        )
        return {
            "source": source,
            "dependency_graph": graph,
            "dependency_registry": model.get("calculation_dependency_registry") or {},
            "recovered_bars_indexed": indexed,
            "recovered_bar_count": len(recovered_bar_ids),
        }
