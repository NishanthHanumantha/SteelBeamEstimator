"""Calculation index builder — Phase I.4.5."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from src.engineering_calculations.calculation_index.calculation_index import CalculationIndex
from src.engineering_calculations.calculation_index.calculation_index_registry import (
    CalculationIndexRegistry,
)
from src.engineering_calculations.calculation_index.calculation_index_types import (
    CALCULATION_TYPE_TO_INDEX_CATEGORY,
)


def calculation_index_applied(model: dict[str, Any]) -> bool:
    registry = model.get("calculation_index_registry", {})
    if registry.get("phase") == "Phase I.4.5" and registry.get("index_count", 0) >= 0:
        return True
    if model.get("calculation_indexes") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("calculation_index_complete"))


class CalculationIndexBuilder:
    """Build reference-only calculation indexes for every reinforcement bar."""

    def build(
        self,
        bars: List[dict[str, Any]],
        results: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        registry = CalculationIndexRegistry()
        results_by_bar: dict[str, dict[str, str]] = defaultdict(dict)

        for result in results:
            bar_id = str(result.get("input_bar_id", ""))
            calc_type = str(result.get("calculation_type", ""))
            result_id = str(result.get("result_id", ""))
            category = CALCULATION_TYPE_TO_INDEX_CATEGORY.get(calc_type)
            if not bar_id or not result_id or not category:
                continue
            results_by_bar[bar_id][category] = result_id

        updated_bars: List[dict[str, Any]] = []
        indexes: List[dict[str, Any]] = []

        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        for bar in sorted_bars:
            bar_id = str(bar.get("bar_id", ""))
            references = dict(sorted(results_by_bar.get(bar_id, {}).items()))
            index_id = registry.next_id()
            index = CalculationIndex(index_id, bar_id, references)
            index_dict = index.to_dict()
            registry.register(index_dict)
            indexes.append(index_dict)

            updated_bar = dict(bar)
            updated_bar["calculation_index"] = index_dict
            updated_bars.append(updated_bar)

        primary = drawing_models[0] if drawing_models else {}
        project_registry = CalculationIndexRegistry.build_project_registry(
            indexes,
            result_count=len(results),
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        exports = {
            "reinforcement_bars": updated_bars,
            "calculation_indexes": indexes,
            "calculation_index_registry": project_registry,
        }
        return updated_bars, exports
