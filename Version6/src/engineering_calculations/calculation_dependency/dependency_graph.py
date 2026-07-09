"""Calculation dependency graph — Phase I.4.6."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from src.engineering_calculations.calculation_dependency.dependency_types import (
    CALCULATION_TYPE_TO_DEPENDENCY_CATEGORY,
    DEPENDENCY_NODE_SPECS,
    INDEX_CATEGORY_TO_DEPENDENCY_CATEGORY,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState


class CalculationDependencyGraph:
    """Metadata-only dependency graph for engineering calculation execution order."""

    def __init__(self, nodes: dict[str, dict[str, Any]]) -> None:
        self._nodes = {
            str(category): dict(spec)
            for category, spec in sorted(nodes.items())
        }

    @classmethod
    def from_spec(cls) -> "CalculationDependencyGraph":
        nodes = {
            category: {
                "category": category,
                "sequence": spec["sequence"],
                "depends_on": list(spec["depends_on"]),
                "calculation_type": spec["calculation_type"],
                "index_category": spec["index_category"],
                "metadata_only": True,
            }
            for category, spec in DEPENDENCY_NODE_SPECS.items()
        }
        return cls(nodes)

    @property
    def nodes(self) -> dict[str, dict[str, Any]]:
        return dict(self._nodes)

    def get_node(self, category: str) -> Optional[dict[str, Any]]:
        return self._nodes.get(str(category))

    def depends_on(self, category: str) -> List[str]:
        node = self.get_node(category)
        return list(node.get("depends_on", [])) if node else []

    def sequence(self, category: str) -> Optional[int]:
        node = self.get_node(category)
        return int(node["sequence"]) if node else None

    def resolve_category(
        self,
        calculation_type: str | None = None,
        index_category: str | None = None,
    ) -> Optional[str]:
        if calculation_type:
            mapped = CALCULATION_TYPE_TO_DEPENDENCY_CATEGORY.get(str(calculation_type))
            if mapped:
                return mapped
        if index_category:
            return INDEX_CATEGORY_TO_DEPENDENCY_CATEGORY.get(str(index_category))
        return None

    def can_execute(
        self,
        calculation_type: str,
        bar: dict[str, Any],
        results_by_id: dict[str, dict[str, Any]],
    ) -> bool:
        category = self.resolve_category(calculation_type=calculation_type)
        if not category:
            return True

        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        for dependency in self.depends_on(category):
            result_id = references.get(dependency)
            if not result_id:
                return False
            result = results_by_id.get(str(result_id))
            if not result:
                return False
            if str(result.get("calculation_state")) not in {
                CalculationResultState.CALCULATED.value,
                CalculationResultState.READY.value,
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }:
                return False
            if dependency == "DEVELOPMENT_LENGTH" and calculation_type == "LAP_LENGTH":
                if result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                    return False
                if result.get("result_value") is None:
                    return False
        return True

    def missing_dependencies(
        self,
        calculation_type: str,
        bar: dict[str, Any],
        results_by_id: dict[str, dict[str, Any]],
    ) -> List[str]:
        category = self.resolve_category(calculation_type=calculation_type)
        if not category:
            return []

        missing: List[str] = []
        index = bar.get("calculation_index") or {}
        references = index.get("references") or {}
        for dependency in self.depends_on(category):
            result_id = references.get(dependency)
            result = results_by_id.get(str(result_id)) if result_id else None
            if not result_id or not result:
                missing.append(dependency)
                continue
            if dependency == "DEVELOPMENT_LENGTH" and calculation_type == "LAP_LENGTH":
                if result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                    missing.append(dependency)
                elif result.get("result_value") is None:
                    missing.append(dependency)
        return missing

    def ordered_categories(self) -> List[str]:
        return [
            category
            for category, _ in sorted(
                self._nodes.items(),
                key=lambda item: int(item[1].get("sequence", 0)),
            )
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": "CALC_DEPENDENCY_GRAPH",
            "nodes": {
                category: dict(spec)
                for category, spec in sorted(
                    self._nodes.items(),
                    key=lambda item: int(item[1].get("sequence", 0)),
                )
            },
            "ordered_categories": self.ordered_categories(),
            "metadata_only": True,
        }

    def topological_order(self) -> List[str]:
        return self.ordered_categories()

    def has_cycle(self) -> bool:
        visited: Set[str] = set()
        stack: Set[str] = set()

        def visit(category: str) -> bool:
            if category in stack:
                return True
            if category in visited:
                return False
            visited.add(category)
            stack.add(category)
            for dependency in self.depends_on(category):
                if visit(dependency):
                    return True
            stack.remove(category)
            return False

        return any(visit(category) for category in self._nodes)
