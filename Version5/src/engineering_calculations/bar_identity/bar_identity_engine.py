"""Bar identity determination engine — Phase I.8."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.calculation_context.context_loader import DEFAULT_RULES_PATH
from src.engineering_calculations.bar_identity.bar_identity_determiner import BarIdentityDeterminer
from src.engineering_calculations.bar_identity.bar_identity_registry import BarIdentityRegistry
from src.engineering_calculations.bar_identity.bar_identity_types import CALCULATION_TYPE
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
from src.reinforcement_calculation.calculation_state import CalculationState


class BarIdentityEngine:
    """Determine bar identity for READY BAR_IDENTITY calculation results."""

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
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        bar_by_id = {str(item.get("bar_id", "")): item for item in bars}
        result_registry = CalculationResultRegistry()
        self._initialize_registry_sequence(result_registry, results)
        for result in results:
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_registry.register(result)

        updated_results = self._ensure_bar_identity_results(
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
        assignment_plan = self._build_assignment_plan(
            bars,
            context_by_spec,
            results_by_id,
        )
        registry = BarIdentityRegistry()
        determiner = BarIdentityDeterminer(
            self._cache,
            self._dependency_graph,
            results_by_id,
            assignment_plan,
        )

        result_index: dict[str, int] = {}
        for index, result in enumerate(updated_results):
            result_id = str(result.get("result_id", ""))
            if result_id:
                result_index[result_id] = index

        identity_records: List[dict[str, Any]] = []
        for result in updated_results:
            if result.get("calculation_type") != CALCULATION_TYPE:
                continue

            bar = bar_by_id.get(str(result.get("input_bar_id", "")), {})
            context = context_by_id.get(str(result.get("input_context_id", "")), {})
            updated, record = determiner.determine(result, context, bar)

            bar_identity_id = registry.next_id()
            record["bar_identity_id"] = bar_identity_id
            registry.register(record)
            identity_records.append(record)

            result_id = str(result.get("result_id", ""))
            if result_id in result_index:
                updated_results[result_index[result_id]] = updated

        primary = drawing_models[0] if drawing_models else {}
        project_registry = BarIdentityRegistry.build_project_registry(
            identity_records,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )

        exports = {
            "engineering_calculation_results": updated_results,
            "bar_identity_results": identity_records,
            "bar_identity_registry": project_registry,
        }
        return updated_results, exports

    def _build_assignment_plan(
        self,
        bars: List[dict[str, Any]],
        context_by_spec: dict[str, dict[str, Any]],
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        ready_entries: List[tuple[str, str, str]] = []
        for bar in bars:
            readiness = bar.get("calculation_readiness") or {}
            if readiness.get("calculation_state") != CalculationState.READY.value:
                continue
            bar_id = str(bar.get("bar_id", ""))
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            signature = BarIdentityDeterminer.build_equivalence_signature(
                bar,
                context,
                results_by_id,
            )
            ready_entries.append((signature, bar_id, bar_id))

        sorted_entries = sorted(ready_entries, key=lambda item: (item[0], item[1]))
        signature_counts = Counter(signature for signature, _, _ in sorted_entries)
        unique_signatures = sorted({signature for signature, _, _ in sorted_entries})
        group_sequence_by_signature = {
            signature: index + 1 for index, signature in enumerate(unique_signatures)
        }
        instance_counters: dict[str, int] = defaultdict(int)
        plan: dict[str, dict[str, Any]] = {}
        for identity_sequence, (signature, bar_id, _) in enumerate(sorted_entries, start=1):
            instance_counters[signature] += 1
            plan[bar_id] = {
                "equivalence_signature": signature,
                "identity_sequence": identity_sequence,
                "group_sequence": group_sequence_by_signature[signature],
                "instance_index_in_group": instance_counters[signature],
                "group_member_count": signature_counts[signature],
            }
        return plan

    def _ensure_bar_identity_results(
        self,
        results: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        registry: CalculationResultRegistry,
    ) -> List[dict[str, Any]]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        bars_with_identity = {
            str(item.get("input_bar_id", ""))
            for item in results
            if item.get("calculation_type") == CALCULATION_TYPE
        }
        updated_results = list(results)
        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        for bar in sorted_bars:
            bar_id = str(bar.get("bar_id", ""))
            if bar_id in bars_with_identity:
                continue
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            readiness = bar.get("calculation_readiness") or {}
            result = self._result_builder.build(
                context,
                bar,
                readiness,
                CalculationType.BAR_IDENTITY,
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
        identity_records: List[dict[str, Any]],
        identity_registry: dict[str, Any],
        calc_registry: dict[str, Any],
    ) -> dict[str, Any]:
        synced_registry = BarIdentityEngine.sync_calculation_result_registry(
            results,
            calc_registry,
        )
        return {
            "engineering_calculation_results": results,
            "calculation_result_registry": synced_registry,
            "bar_identity_results": identity_records,
            "bar_identity_registry": identity_registry,
        }
