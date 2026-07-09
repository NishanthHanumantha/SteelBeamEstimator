"""Engineering quantity engine — Phase I.13."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.quantity.quantity_builder import QuantityBuilder
from src.engineering_calculations.quantity.quantity_registry import QuantityRegistry
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class QuantityEngine:
    """Aggregate beam summary outputs into engineering quantity records."""

    def __init__(
        self,
        rules_path: Path | None = None,
        dependency_graph: CalculationDependencyGraph | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._dependency_graph = dependency_graph or CalculationDependencyGraph.from_spec()
        self._builder = QuantityBuilder()

    def determine(
        self,
        summary_records: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        registry = QuantityRegistry()
        quantity_records: List[dict[str, Any]] = []

        sorted_summaries = sorted(
            summary_records,
            key=lambda item: str(item.get("beam_summary_id", "")),
        )
        for summary in sorted_summaries:
            record = self._builder.build(summary)
            record["quantity_id"] = registry.next_id()
            registry.register(record)
            quantity_records.append(record)

        primary = drawing_models[0] if drawing_models else {}
        project_registry = QuantityRegistry.build_project_registry(
            quantity_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        return quantity_records, {
            "quantity_results": quantity_records,
            "quantity_registry": project_registry,
        }

    @staticmethod
    def build_project_exports(
        quantity_records: List[dict[str, Any]],
        quantity_registry: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "quantity_results": quantity_records,
            "quantity_registry": quantity_registry,
        }
