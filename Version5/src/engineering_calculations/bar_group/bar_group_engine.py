"""Bar group determination engine — Phase I.9."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.bar_group.bar_group_determiner import BarGroupDeterminer
from src.engineering_calculations.bar_group.bar_group_registry import BarGroupRegistry
from src.engineering_calculations.bar_group.bar_group_types import (
    CALCULATION_TYPE,
    BarGroupState,
)
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_builder import CalculationResultBuilder
from src.engineering_calculations.calculation_result_registry import CalculationResultRegistry
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.general_notes.engineering_rule_cache import EngineeringRuleCache


class BarGroupEngine:
    """Aggregate engineering-identical bars into reusable engineering groups."""

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
        identity_records: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        bar_by_id = {str(item.get("bar_id", "")): item for item in bars}
        identity_records_by_bar = {
            str(item.get("bar_id", "")): item
            for item in identity_records
            if item.get("bar_id")
        }

        result_registry = CalculationResultRegistry()
        self._initialize_registry_sequence(result_registry, results)
        for result in results:
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_registry.register(result)

        updated_results = self._ensure_bar_group_results(
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
        result_index: dict[str, int] = {}
        for index, result in enumerate(updated_results):
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_index[result_id] = index

        calculated_identity_records = [
            item
            for item in identity_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        primary_context = contexts[0] if contexts else {}
        determiner = BarGroupDeterminer(
            self._cache,
            self._dependency_graph,
            results_by_id,
            identity_records_by_bar,
        )
        resolved_rule = determiner.resolve_rule(primary_context)
        memberships = determiner.classify_memberships(
            calculated_identity_records,
            primary_context,
        )

        registry = BarGroupRegistry()
        group_records: List[dict[str, Any]] = []
        processed_bars: set[str] = set()

        for group_sequence, membership in enumerate(memberships, start=1):
            member_results = [
                item
                for item in updated_results
                if item.get("calculation_type") == CALCULATION_TYPE
                and str(item.get("input_bar_id", "")) in membership.member_bar_ids
            ]
            representative_bar = bar_by_id.get(membership.member_bar_ids[0], {})
            context = context_by_spec.get(
                str(representative_bar.get("specification_id", "")),
                primary_context,
            )
            updated_member_results, record = determiner.determine_group(
                membership,
                group_sequence,
                member_results,
                context,
                resolved_rule,
            )
            record["bar_group_id"] = registry.next_id()
            record["group_id"] = record["bar_group_id"]
            registry.register(record)
            group_records.append(record)

            for updated in updated_member_results:
                result_id = str(updated.get("result_id", ""))
                if result_id in result_index:
                    updated_results[result_index[result_id]] = updated
                processed_bars.add(str(updated.get("input_bar_id", "")))

        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        for bar in sorted_bars:
            bar_id = str(bar.get("bar_id", ""))
            if bar_id in processed_bars:
                continue
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            group_result = next(
                (
                    item
                    for item in updated_results
                    if item.get("calculation_type") == CALCULATION_TYPE
                    and str(item.get("input_bar_id", "")) == bar_id
                ),
                None,
            )
            if not group_result:
                continue
            state = str(group_result.get("calculation_state", ""))
            if state in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }:
                updated, record = determiner.determine_preserved(
                    group_result,
                    context,
                    bar,
                    state,
                )
                record["bar_group_id"] = registry.next_id()
                record["group_id"] = record["bar_group_id"]
                registry.register(record)
                group_records.append(record)
                result_id = str(updated.get("result_id", ""))
                if result_id in result_index:
                    updated_results[result_index[result_id]] = updated

        primary = drawing_models[0] if drawing_models else {}
        project_registry = BarGroupRegistry.build_project_registry(
            group_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        exports = {
            "engineering_calculation_results": updated_results,
            "bar_group_results": group_records,
            "bar_group_registry": project_registry,
        }
        return updated_results, exports

    def _ensure_bar_group_results(
        self,
        results: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        registry: CalculationResultRegistry,
    ) -> List[dict[str, Any]]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        bars_with_group = {
            str(item.get("input_bar_id", ""))
            for item in results
            if item.get("calculation_type") == CALCULATION_TYPE
        }
        updated_results = list(results)
        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        for bar in sorted_bars:
            bar_id = str(bar.get("bar_id", ""))
            if bar_id in bars_with_group:
                continue
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            readiness = bar.get("calculation_readiness") or {}
            result = self._result_builder.build(
                context,
                bar,
                readiness,
                CalculationType.BAR_GROUP,
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
        group_records: List[dict[str, Any]],
        group_registry: dict[str, Any],
        calc_registry: dict[str, Any],
    ) -> dict[str, Any]:
        synced_registry = BarGroupEngine.sync_calculation_result_registry(
            results,
            calc_registry,
        )
        return {
            "engineering_calculation_results": results,
            "calculation_result_registry": synced_registry,
            "bar_group_results": group_records,
            "bar_group_registry": group_registry,
        }
