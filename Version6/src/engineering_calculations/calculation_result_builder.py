"""Calculation result builder — Phase I.2.2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_calculations.calculation_result_models import build_engineering_calculation_result
from src.engineering_calculations.calculation_result_registry import CalculationResultRegistry
from src.engineering_calculations.calculation_result_types import (
    FRAMEWORK_CALCULATION_TYPES,
    FRAMEWORK_ENGINE_NAME,
    RESULT_STATUS_FRAMEWORK_INITIALIZED,
    CalculationResultState,
    CalculationType,
)
from src.reinforcement_calculation.calculation_state import CalculationState, parse_calculation_state


class CalculationResultBuilder:
    """Initialize framework calculation results without performing engineering math."""

    def build(
        self,
        context: dict[str, Any],
        bar: dict[str, Any],
        readiness: dict[str, Any],
        calculation_type: CalculationType,
        group: Optional[dict[str, Any]] = None,
        registry: Optional[CalculationResultRegistry] = None,
        calculation_inputs: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        active_registry = registry or CalculationResultRegistry()
        result_state, notes = self._resolve_result_state(readiness)
        group_id = str((group or {}).get("group_id", ""))
        association_id = str(context.get("association_id", ""))

        result = build_engineering_calculation_result(
            result_id=active_registry.next_id(),
            engine_name=FRAMEWORK_ENGINE_NAME,
            calculation_type=calculation_type.value,
            calculation_state=result_state.value,
            input_context_id=str(context.get("context_id", bar.get("context_id", ""))),
            input_bar_id=str(bar.get("bar_id", "")),
            input_group_id=group_id,
            input_specification_id=str(bar.get("specification_id", "")),
            input_association_id=association_id,
            input_beam_id=str(bar.get("beam_id", "")),
            result_status=RESULT_STATUS_FRAMEWORK_INITIALIZED,
            result_value=None,
            result_unit="",
            result_metadata={
                "framework_only": True,
                "readiness_state": readiness.get("calculation_state"),
                "defer_reason": readiness.get("defer_reason", ""),
            },
            calculation_notes=notes,
            calculation_trace={
                "framework_phase": "I.2.2",
                "calculation_performed": False,
                "readiness_summary": readiness.get("upstream_status_summary", {}),
            },
            traceability=self._build_traceability(context, bar, group, readiness, calculation_type),
            calculation_inputs=calculation_inputs or {},
        )
        return result

    def build_framework_results(
        self,
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], CalculationResultRegistry]:
        registry = CalculationResultRegistry()
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        group_by_spec = {
            str(item.get("specification_id", "")): item for item in groups
        }

        results: List[dict[str, Any]] = []
        sorted_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        sorted_types = sorted(
            (calc_type.value for calc_type in FRAMEWORK_CALCULATION_TYPES),
        )

        for bar in sorted_bars:
            spec_id = str(bar.get("specification_id", ""))
            context = context_by_spec.get(spec_id, {})
            group = group_by_spec.get(spec_id, {})
            readiness = bar.get("calculation_readiness") or group.get("calculation_readiness") or {}

            for type_value in sorted_types:
                calc_type = CalculationType(type_value)
                result = self.build(
                    context,
                    bar,
                    readiness,
                    calc_type,
                    group=group,
                    registry=registry,
                )
                registry.register(result)
                results.append(result)

        return results, registry

    @staticmethod
    def build_project_exports(
        results: List[dict[str, Any]],
        registry: CalculationResultRegistry,
        bars: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        primary = drawing_models[0] if drawing_models else {}
        calculation_registry = CalculationResultRegistry.build_project_registry(
            results,
            bars,
            registry.processed_bar_ids,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return {
            "engineering_calculation_results": results,
            "calculation_result_registry": calculation_registry,
        }

    @staticmethod
    def _resolve_result_state(
        readiness: dict[str, Any],
    ) -> Tuple[CalculationResultState, str]:
        readiness_state = parse_calculation_state(readiness.get("calculation_state"))
        defer_reason = str(readiness.get("defer_reason") or "")

        if readiness_state == CalculationState.READY:
            return (
                CalculationResultState.READY,
                "Framework result initialized; awaiting engineering calculation.",
            )
        if readiness_state == CalculationState.BLOCKED:
            return (
                CalculationResultState.BLOCKED,
                defer_reason or "Calculation blocked by upstream business rule.",
            )
        if readiness_state == CalculationState.DEFERRED:
            return (
                CalculationResultState.DEFERRED,
                defer_reason or "Calculation deferred due to incomplete upstream inputs.",
            )
        return (
            CalculationResultState.DEFERRED,
            defer_reason or "Calculation deferred; readiness not established.",
        )

    @staticmethod
    def _build_traceability(
        context: dict[str, Any],
        bar: dict[str, Any],
        group: Optional[dict[str, Any]],
        readiness: dict[str, Any],
        calculation_type: CalculationType,
    ) -> dict[str, Any]:
        return {
            "lineage": [
                "Engineering Calculation Result Framework",
                "Calculation Readiness",
                "Reinforcement Calculation",
                "Engineering Calculation Context",
                "Engineering Specification",
            ],
            "calculation_type": calculation_type.value,
            "context_id": context.get("context_id"),
            "bar_id": bar.get("bar_id"),
            "group_id": (group or {}).get("group_id"),
            "specification_id": bar.get("specification_id"),
            "readiness_state": readiness.get("calculation_state"),
            "bar_traceability": bar.get("traceability", {}),
            "context_traceability": context.get("traceability", {}),
        }
