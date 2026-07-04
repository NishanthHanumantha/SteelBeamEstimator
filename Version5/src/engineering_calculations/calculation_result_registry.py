"""Calculation result registry — Phase I.2.2."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.engineering_calculations.calculation_result_types import (
    NAMESPACE_CALCULATION_RESULT,
    CalculationResultState,
)


def format_calculation_result_id(sequence: int) -> str:
    return f"CALC_RESULT::{sequence:06d}"


def format_calculation_result_registry_id() -> str:
    return "CALC_RESULT_REGISTRY"


class CalculationResultRegistry:
    """Sequence registry with O(1) lookups for calculation results."""

    def __init__(self) -> None:
        self._sequence = 0
        self._results: dict[str, dict[str, Any]] = {}
        self._by_context: dict[str, List[str]] = defaultdict(list)
        self._by_bar: dict[str, List[str]] = defaultdict(list)
        self._by_specification: dict[str, List[str]] = defaultdict(list)
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._by_calculation_type: dict[str, List[str]] = defaultdict(list)
        self._by_state: dict[str, List[str]] = defaultdict(list)
        self._by_bar_and_type: dict[str, str] = {}
        self._processed_bar_ids: List[str] = []

    def next_id(self) -> str:
        self._sequence += 1
        return format_calculation_result_id(self._sequence)

    def register(self, result: dict[str, Any]) -> str:
        result_id = str(result.get("result_id") or "")
        if not result_id:
            result_id = self.next_id()
            result["result_id"] = result_id

        self._results[result_id] = result

        context_id = str(result.get("input_context_id", ""))
        bar_id = str(result.get("input_bar_id", ""))
        spec_id = str(result.get("input_specification_id", ""))
        beam_id = str(result.get("input_beam_id", ""))
        calc_type = str(result.get("calculation_type", ""))
        state = str(result.get("calculation_state", ""))

        if context_id and result_id not in self._by_context[context_id]:
            self._by_context[context_id].append(result_id)
        if bar_id and result_id not in self._by_bar[bar_id]:
            self._by_bar[bar_id].append(result_id)
        if spec_id and result_id not in self._by_specification[spec_id]:
            self._by_specification[spec_id].append(result_id)
        if beam_id and result_id not in self._by_beam[beam_id]:
            self._by_beam[beam_id].append(result_id)
        if calc_type and result_id not in self._by_calculation_type[calc_type]:
            self._by_calculation_type[calc_type].append(result_id)
        if state and result_id not in self._by_state[state]:
            self._by_state[state].append(result_id)
        if bar_id and calc_type:
            self._by_bar_and_type[f"{bar_id}::{calc_type}"] = result_id

        return result_id

    def mark_processed(self, bar_id: str) -> None:
        if bar_id and bar_id not in self._processed_bar_ids:
            self._processed_bar_ids.append(bar_id)

    def result(self, result_id: str) -> Optional[dict[str, Any]]:
        return self._results.get(result_id)

    def result_by_bar_and_type(
        self,
        bar_id: str,
        calculation_type: str,
    ) -> Optional[dict[str, Any]]:
        result_id = self._by_bar_and_type.get(f"{bar_id}::{calculation_type}")
        return self._results.get(result_id) if result_id else None

    def results_by_context(self, context_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_context.get(context_id, []))

    def results_by_bar(self, bar_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_bar.get(bar_id, []))

    def results_by_specification(self, specification_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_specification.get(specification_id, []))

    def results_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_beam.get(beam_id, []))

    def results_by_calculation_type(self, calculation_type: str) -> List[dict[str, Any]]:
        return self._collect(self._by_calculation_type.get(calculation_type, []))

    def results_by_state(self, state: str) -> List[dict[str, Any]]:
        return self._collect(self._by_state.get(state, []))

    def get_ready_results(self) -> List[dict[str, Any]]:
        return self.results_by_state(CalculationResultState.READY.value)

    def get_deferred_results(self) -> List[dict[str, Any]]:
        return self.results_by_state(CalculationResultState.DEFERRED.value)

    def get_blocked_results(self) -> List[dict[str, Any]]:
        return self.results_by_state(CalculationResultState.BLOCKED.value)

    def get_failed_results(self) -> List[dict[str, Any]]:
        return self.results_by_state(CalculationResultState.FAILED.value)

    def all_results(self) -> List[dict[str, Any]]:
        return list(self._results.values())

    @property
    def processed_bar_ids(self) -> List[str]:
        return list(self._processed_bar_ids)

    def _collect(self, result_ids: List[str]) -> List[dict[str, Any]]:
        return [
            self._results[result_id]
            for result_id in result_ids
            if result_id in self._results
        ]

    @staticmethod
    def build_project_registry(
        results: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        processed_bar_ids: List[str],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_state: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_beam: Dict[str, int] = {}

        for result in results:
            state = str(result.get("calculation_state", "UNKNOWN"))
            calc_type = str(result.get("calculation_type", "UNKNOWN"))
            beam = str(result.get("input_beam_id", ""))
            by_state[state] = by_state.get(state, 0) + 1
            by_type[calc_type] = by_type.get(calc_type, 0) + 1
            if beam:
                by_beam[beam] = by_beam.get(beam, 0) + 1

        return {
            "namespace": NAMESPACE_CALCULATION_RESULT,
            "phase": "Phase I.2.2",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_id": format_calculation_result_registry_id(),
            "result_count": len(results),
            "result_ids": [item.get("result_id") for item in results],
            "bar_count": len(bars),
            "processed_bar_ids": list(processed_bar_ids),
            "results_by_state": by_state,
            "results_by_calculation_type": by_type,
            "results_by_beam": by_beam,
            "state_counts": {
                "ready": by_state.get(CalculationResultState.READY.value, 0),
                "deferred": by_state.get(CalculationResultState.DEFERRED.value, 0),
                "blocked": by_state.get(CalculationResultState.BLOCKED.value, 0),
                "failed": by_state.get(CalculationResultState.FAILED.value, 0),
                "calculated": by_state.get(CalculationResultState.CALCULATED.value, 0),
            },
        }
