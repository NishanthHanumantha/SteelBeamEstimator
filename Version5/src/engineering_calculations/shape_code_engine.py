"""Shape code determination engine — Phase I.7."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_builder import CalculationResultBuilder
from src.engineering_calculations.calculation_result_registry import CalculationResultRegistry
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.shape_code_determiner import ShapeCodeDeterminer
from src.engineering_calculations.shape_code_registry import ShapeCodeRegistry
from src.engineering_calculations.shape_code_types import CALCULATION_TYPE
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class ShapeCodeEngine:
    """Determine shape code for READY SHAPE_CODE calculation results."""

    def __init__(
        self,
        rules_path: Path | None = None,
        dependency_graph: CalculationDependencyGraph | None = None,
    ) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._dependency_graph = dependency_graph or CalculationDependencyGraph.from_spec()
        self._result_builder = CalculationResultBuilder()

    def determine(
        self,
        results: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        context_by_id = {str(item.get("context_id", "")): item for item in contexts}
        bar_by_id = {str(item.get("bar_id", "")): item for item in bars}
        result_registry = CalculationResultRegistry()
        self._initialize_registry_sequence(result_registry, results)
        for result in results:
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_registry.register(result)

        updated_results = self._ensure_shape_code_results(
            results,
            bars,
            contexts,
            result_registry,
        )
        results_by_id = {
            str(item.get("result_id", "")): item
            for item in updated_results
            if item.get("result_id")
        }
        registry = ShapeCodeRegistry()
        determiner = ShapeCodeDeterminer(
            self._cache,
            self._dependency_graph,
            results_by_id,
        )

        result_index: dict[str, int] = {}
        for index, result in enumerate(updated_results):
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_index[result_id] = index

        shape_records: List[dict[str, Any]] = []
        for result in updated_results:
            if result.get("calculation_type") != CALCULATION_TYPE:
                continue

            bar = bar_by_id.get(str(result.get("input_bar_id", "")), {})
            context = context_by_id.get(str(result.get("input_context_id", "")), {})
            updated, record = determiner.determine(result, context, bar)

            shape_code_id = registry.next_id()
            record["shape_code_id"] = shape_code_id
            registry.register(record)
            shape_records.append(record)

            result_id = str(result.get("result_id", ""))
            if result_id in result_index:
                updated_results[result_index[result_id]] = updated

        primary = drawing_models[0] if drawing_models else {}
        project_registry = ShapeCodeRegistry.build_project_registry(
            shape_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        exports = {
            "engineering_calculation_results": updated_results,
            "shape_code_results": shape_records,
            "shape_code_registry": project_registry,
        }
        return updated_results, exports

    def _ensure_shape_code_results(
        self,
        results: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        registry: CalculationResultRegistry,
    ) -> List[dict[str, Any]]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        bars_with_shape = {
            str(item.get("input_bar_id", ""))
            for item in results
            if item.get("calculation_type") == CALCULATION_TYPE
        }
        updated_results = list(results)
        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        for bar in sorted_bars:
            bar_id = str(bar.get("bar_id", ""))
            if bar_id in bars_with_shape:
                continue
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            readiness = bar.get("calculation_readiness") or {}
            result = self._result_builder.build(
                context,
                bar,
                readiness,
                CalculationType.SHAPE_CODE,
                registry=registry,
            )
            registry.register(result)
            updated_results.append(result)
        return updated_results

    @staticmethod
    def _initialize_registry_sequence(
        registry: CalculationResultRegistry,
        results: List[dict[str, Any]],
    ) -> None:
        max_sequence = 0
        for result in results:
            result_id = str(result.get("result_id", ""))
            if "::" not in result_id:
                continue
            try:
                max_sequence = max(max_sequence, int(result_id.rsplit("::", 1)[-1]))
            except ValueError:
                continue
        registry._sequence = max_sequence

    @staticmethod
    def sync_calculation_result_registry(
        results: List[dict[str, Any]],
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        updated = dict(registry)
        by_state: dict[str, int] = defaultdict(int)
        for result in results:
            by_state[str(result.get("calculation_state", ""))] += 1

        state_counts = {
            "ready": by_state.get(CalculationResultState.READY.value, 0),
            "deferred": by_state.get(CalculationResultState.DEFERRED.value, 0),
            "blocked": by_state.get(CalculationResultState.BLOCKED.value, 0),
            "failed": by_state.get(CalculationResultState.FAILED.value, 0),
            "calculated": by_state.get(CalculationResultState.CALCULATED.value, 0),
        }
        updated["results_by_state"] = dict(by_state)
        updated["state_counts"] = state_counts
        return updated

    @staticmethod
    def build_project_exports(
        results: List[dict[str, Any]],
        shape_records: List[dict[str, Any]],
        shape_registry: dict[str, Any],
        calc_registry: dict[str, Any],
    ) -> dict[str, Any]:
        synced_registry = ShapeCodeEngine.sync_calculation_result_registry(
            results,
            calc_registry,
        )
        return {
            "engineering_calculation_results": results,
            "calculation_result_registry": synced_registry,
            "shape_code_results": shape_records,
            "shape_code_registry": shape_registry,
        }
