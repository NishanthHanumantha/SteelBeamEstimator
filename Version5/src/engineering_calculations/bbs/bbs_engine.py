"""BBS determination engine — Phase I.10."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.bar_group.bar_group_types import BarGroupState
from src.engineering_calculations.bbs.bbs_determiner import BbsDeterminer
from src.engineering_calculations.bbs.bbs_registry import BbsRegistry
from src.engineering_calculations.bbs.bbs_types import CALCULATION_TYPE
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


class BbsEngine:
    """Transform engineering bar groups into fabrication schedule records."""

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
        group_records: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]] | None = None,
        project_id: str = "",
    ) -> Tuple[List[dict[str, Any]], dict[str, Any]]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        bar_by_id = {str(item.get("bar_id", "")): item for item in bars}
        group_records_by_id = {
            str(item.get("bar_group_id", "")): item
            for item in group_records
            if item.get("bar_group_id")
        }

        result_registry = CalculationResultRegistry()
        self._initialize_registry_sequence(result_registry, results)
        for result in results:
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_registry.register(result)

        updated_results = self._ensure_bbs_results(
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

        primary_context = contexts[0] if contexts else {}
        determiner = BbsDeterminer(
            self._cache,
            self._dependency_graph,
            results_by_id,
            group_records_by_id,
        )
        resolved_rule = determiner.resolve_rule(primary_context)
        memberships = determiner.classify_memberships(group_records, primary_context)

        registry = BbsRegistry()
        bbs_records: List[dict[str, Any]] = []
        processed_bars: set[str] = set()
        processed_groups: set[str] = set()

        for schedule_position, membership in enumerate(memberships, start=1):
            group_record = group_records_by_id.get(membership.bar_group_id, {})
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
            updated_member_results, record = determiner.determine_schedule(
                membership,
                schedule_position,
                member_results,
                group_record,
                context,
                resolved_rule,
            )
            record["bbs_id"] = registry.next_id()
            registry.register(record)
            bbs_records.append(record)
            processed_groups.add(membership.bar_group_id)

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
            group_record = next(
                (
                    item
                    for item in group_records
                    if str(item.get("bar_id", "")) == bar_id
                    and item.get("determination_state")
                    in {BarGroupState.DEFERRED.value, BarGroupState.BLOCKED.value}
                ),
                None,
            )
            if not group_record:
                continue
            group_key = str(group_record.get("bar_group_id", ""))
            if group_key in processed_groups:
                continue
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            member_results = [
                item
                for item in updated_results
                if item.get("calculation_type") == CALCULATION_TYPE
                and str(item.get("input_bar_id", "")) == bar_id
            ]
            state = str(member_results[0].get("calculation_state", "")) if member_results else ""
            if state in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }:
                updated, record = determiner.determine_preserved(
                    group_record,
                    member_results,
                    context,
                    bar,
                    state,
                )
                record["bbs_id"] = registry.next_id()
                registry.register(record)
                bbs_records.append(record)
                processed_groups.add(group_key)
                for item in updated:
                    result_id = str(item.get("result_id", ""))
                    if result_id in result_index:
                        updated_results[result_index[result_id]] = item

        primary = drawing_models[0] if drawing_models else {}
        project_registry = BbsRegistry.build_project_registry(
            bbs_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        exports = {
            "engineering_calculation_results": updated_results,
            "bbs_results": bbs_records,
            "bbs_registry": project_registry,
        }
        return updated_results, exports

    def _ensure_bbs_results(
        self,
        results: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        registry: CalculationResultRegistry,
    ) -> List[dict[str, Any]]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        bars_with_bbs = {
            str(item.get("input_bar_id", ""))
            for item in results
            if item.get("calculation_type") == CALCULATION_TYPE
        }
        updated_results = list(results)
        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        for bar in sorted_bars:
            bar_id = str(bar.get("bar_id", ""))
            if bar_id in bars_with_bbs:
                continue
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            readiness = bar.get("calculation_readiness") or {}
            result = self._result_builder.build(
                context,
                bar,
                readiness,
                CalculationType.BBS,
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
        bbs_records: List[dict[str, Any]],
        bbs_registry: dict[str, Any],
        calc_registry: dict[str, Any],
    ) -> dict[str, Any]:
        synced_registry = BbsEngine.sync_calculation_result_registry(
            results,
            calc_registry,
        )
        return {
            "engineering_calculation_results": results,
            "calculation_result_registry": synced_registry,
            "bbs_results": bbs_records,
            "bbs_registry": bbs_registry,
        }
