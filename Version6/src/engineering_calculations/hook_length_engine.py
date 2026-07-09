"""Hook length determination engine — Phase I.4."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.hook_length_determiner import HookLengthDeterminer
from src.engineering_calculations.hook_length_registry import HookLengthRegistry
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class HookLengthEngine:
    """Determine hook length for READY HOOK calculation results."""

    def __init__(self, rules_path: Path | None = None) -> None:
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._cache = EngineeringRuleCache.get_instance(path)
        self._determiner = HookLengthDeterminer(self._cache)

    def determine(
        self,
        results: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        specifications: List[dict[str, Any]] | None = None,
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        context_by_id = {str(item.get("context_id", "")): item for item in contexts}
        bar_by_id = {str(item.get("bar_id", "")): item for item in bars}
        spec_by_id = {
            str(item.get("specification_id", "")): item for item in (specifications or [])
        }
        registry = HookLengthRegistry()

        updated_results: List[dict[str, Any]] = []
        hook_records: List[dict[str, Any]] = []
        result_index: dict[str, int] = {}

        for index, result in enumerate(results):
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_index[result_id] = index
            updated_results.append(result)

        for result in results:
            if result.get("calculation_type") != CalculationType.HOOK.value:
                continue

            bar = bar_by_id.get(str(result.get("input_bar_id", "")), {})
            context = context_by_id.get(str(result.get("input_context_id", "")), {})
            specification = spec_by_id.get(str(bar.get("specification_id", "")), {})
            updated, record = self._determiner.determine(result, context, bar, specification)

            hook_length_id = registry.next_id()
            record["hook_length_id"] = hook_length_id
            registry.register(record)
            hook_records.append(record)

            result_id = str(result.get("result_id", ""))
            if result_id in result_index:
                updated_results[result_index[result_id]] = updated

        primary = drawing_models[0] if drawing_models else {}
        project_registry = HookLengthRegistry.build_project_registry(
            hook_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        exports = {
            "engineering_calculation_results": updated_results,
            "hook_length_results": hook_records,
            "hook_length_registry": project_registry,
        }
        return updated_results, exports

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
        hook_records: List[dict[str, Any]],
        hook_registry: dict[str, Any],
        calc_registry: dict[str, Any],
    ) -> dict[str, Any]:
        synced_registry = HookLengthEngine.sync_calculation_result_registry(
            results,
            calc_registry,
        )
        return {
            "engineering_calculation_results": results,
            "calculation_result_registry": synced_registry,
            "hook_length_results": hook_records,
            "hook_length_registry": hook_registry,
        }
