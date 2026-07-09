"""Development length registry — Phase I.3."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.engineering_calculations.development_length_types import (
    NAMESPACE_DEV_LENGTH,
    DevelopmentLengthState,
)


def format_dev_length_id(sequence: int) -> str:
    return f"DEV_LENGTH::{sequence:06d}"


def format_dev_length_registry_id() -> str:
    return "DEV_LENGTH_REGISTRY"


class DevelopmentLengthRegistry:
    """Sequence registry with O(1) lookups for development length determinations."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_result: dict[str, str] = {}
        self._by_bar: dict[str, str] = {}
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._by_context: dict[str, List[str]] = defaultdict(list)
        self._by_diameter: dict[str, List[str]] = defaultdict(list)
        self._by_steel_grade: dict[str, List[str]] = defaultdict(list)
        self._by_concrete_grade: dict[str, List[str]] = defaultdict(list)
        self._by_development_length: dict[str, List[str]] = defaultdict(list)
        self._by_state: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_dev_length_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("dev_length_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["dev_length_id"] = record_id

        self._records[record_id] = record

        result_id = str(record.get("result_id", ""))
        bar_id = str(record.get("bar_id", ""))
        beam_id = str(record.get("beam_id", ""))
        context_id = str(record.get("context_id", ""))
        diameter = str(record.get("bar_diameter_mm", ""))
        steel_grade = str(record.get("steel_grade", ""))
        concrete_grade = str(record.get("concrete_grade", ""))
        ld_value = record.get("development_length_mm")
        state = str(record.get("determination_state", ""))

        if result_id:
            self._by_result[result_id] = record_id
        if bar_id:
            self._by_bar[bar_id] = record_id
        if beam_id and record_id not in self._by_beam[beam_id]:
            self._by_beam[beam_id].append(record_id)
        if context_id and record_id not in self._by_context[context_id]:
            self._by_context[context_id].append(record_id)
        if diameter and record_id not in self._by_diameter[diameter]:
            self._by_diameter[diameter].append(record_id)
        if steel_grade and record_id not in self._by_steel_grade[steel_grade]:
            self._by_steel_grade[steel_grade].append(record_id)
        if concrete_grade and record_id not in self._by_concrete_grade[concrete_grade]:
            self._by_concrete_grade[concrete_grade].append(record_id)
        if ld_value is not None and record_id not in self._by_development_length[str(ld_value)]:
            self._by_development_length[str(ld_value)].append(record_id)
        if state and record_id not in self._by_state[state]:
            self._by_state[state].append(record_id)

        return record_id

    def record(self, dev_length_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(dev_length_id)

    def record_by_result(self, result_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_result.get(result_id)
        return self._records.get(record_id) if record_id else None

    def record_by_bar(self, bar_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_bar.get(bar_id)
        return self._records.get(record_id) if record_id else None

    def records_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_beam.get(beam_id, []))

    def records_by_context(self, context_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_context.get(context_id, []))

    def records_by_diameter(self, diameter_mm: int | str) -> List[dict[str, Any]]:
        return self._collect(self._by_diameter.get(str(diameter_mm), []))

    def records_by_steel_grade(self, steel_grade: str) -> List[dict[str, Any]]:
        return self._collect(self._by_steel_grade.get(str(steel_grade), []))

    def records_by_concrete_grade(self, concrete_grade: str) -> List[dict[str, Any]]:
        return self._collect(self._by_concrete_grade.get(str(concrete_grade), []))

    def records_by_development_length(self, ld_mm: int | float) -> List[dict[str, Any]]:
        return self._collect(self._by_development_length.get(str(ld_mm), []))

    def records_by_state(self, state: str) -> List[dict[str, Any]]:
        return self._collect(self._by_state.get(state, []))

    def all_records(self) -> List[dict[str, Any]]:
        return list(self._records.values())

    @staticmethod
    def build_project_registry(
        records: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        by_state: dict[str, int] = defaultdict(int)
        by_beam: dict[str, int] = defaultdict(int)
        by_steel: dict[str, int] = defaultdict(int)
        by_concrete: dict[str, int] = defaultdict(int)
        by_table: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("determination_state", DevelopmentLengthState.DEFERRED.value))
            by_state[state] += 1
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                by_beam[beam_id] += 1
            steel = str(record.get("steel_grade", ""))
            if steel:
                by_steel[steel] += 1
            concrete = str(record.get("concrete_grade", ""))
            if concrete:
                by_concrete[concrete] += 1
            table = str(record.get("development_length_table", ""))
            if table:
                by_table[table] += 1

        state_counts = {
            "calculated": by_state.get(DevelopmentLengthState.CALCULATED.value, 0),
            "deferred": by_state.get(DevelopmentLengthState.DEFERRED.value, 0),
            "blocked": by_state.get(DevelopmentLengthState.BLOCKED.value, 0),
            "failed": by_state.get(DevelopmentLengthState.FAILED.value, 0),
        }

        return {
            "namespace": NAMESPACE_DEV_LENGTH,
            "phase": "Phase I.3",
            "registry_id": format_dev_length_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("dev_length_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam": dict(by_beam),
            "results_by_steel_grade": dict(by_steel),
            "results_by_concrete_grade": dict(by_concrete),
            "results_by_table": dict(by_table),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }

    def _collect(self, record_ids: List[str]) -> List[dict[str, Any]]:
        return [self._records[record_id] for record_id in record_ids if record_id in self._records]
