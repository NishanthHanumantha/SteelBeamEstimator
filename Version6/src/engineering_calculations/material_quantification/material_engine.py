"""Material quantification engine — Phase I.14."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.material_quantification.material_builder import MaterialBuilder
from src.engineering_calculations.material_quantification.material_registry import MaterialRegistry
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class MaterialQuantificationEngine:
    """Aggregate quantity registry outputs into material-centric records."""

    def __init__(
        self,
        rules_path: Path | None = None,
        dependency_graph: CalculationDependencyGraph | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._dependency_graph = dependency_graph or CalculationDependencyGraph.from_spec()
        self._builder = MaterialBuilder()

    def determine(
        self,
        quantity_records: List[dict[str, Any]],
        quantity_registry: dict[str, Any] | None = None,
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        _ = quantity_registry
        material_records = self._builder.build_records(quantity_records)
        registry = MaterialRegistry()

        for record in material_records:
            record["material_id"] = registry.next_id()
            registry.register(record)

        primary = drawing_models[0] if drawing_models else {}
        project_registry = MaterialRegistry.build_project_registry(
            material_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        return material_records, {
            "material_results": material_records,
            "material_registry": project_registry,
        }

    @staticmethod
    def build_project_exports(
        material_records: List[dict[str, Any]],
        material_registry: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "material_results": material_records,
            "material_registry": material_registry,
        }
