"""Lap length registry — Phase I.5."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.engineering_calculations.lap_length_types import (
    NAMESPACE_LAP_LENGTH,
    LapLengthState,
)


def format_lap_length_id(sequence: int) -> str:
    return f"LAP_LENGTH::{sequence:06d}"


def format_lap_length_registry_id() -> str:
    return "LAP_LENGTH_REGISTRY"


class LapLengthRegistry:
    """Sequence registry with O(1) lookups for lap length determinations."""

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
        self._by_lap_length: dict[str, List[str]] = defaultdict(list)
        self._by_lap_factor: dict[str, List[str]] = defaultdict(list)
        self._by_state: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_lap_length_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("lap_length_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["lap_length_id"] = record_id

        self._records[record_id] = record

        result_id = str(record.get("result_id", ""))
        bar_id = str(record.get("bar_id", ""))
        beam_id = str(record.get("beam_id", ""))
        context_id = str(record.get("context_id", ""))
        diameter = str(record.get("bar_diameter_mm", ""))
        steel_grade = str(record.get("steel_grade", ""))
        concrete_grade = str(record.get("concrete_grade", ""))
        development_length = record.get("development_length_mm")
        lap_length = record.get("lap_length_mm")
        lap_factor = record.get("lap_factor")
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
        if development_length is not None and record_id not in self._by_development_length[str(development_length)]:
            self._by_development_length[str(development_length)].append(record_id)
        if lap_length is not None and record_id not in self._by_lap_length[str(lap_length)]:
            self._by_lap_length[str(lap_length)].append(record_id)
        if lap_factor is not None and record_id not in self._by_lap_factor[str(lap_factor)]:
            self._by_lap_factor[str(lap_factor)].append(record_id)
        if state and record_id not in self._by_state[state]:
            self._by_state[state].append(record_id)

        return record_id

    def record(self, lap_length_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(lap_length_id)

    def record_by_result(self, result_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_result.get(result_id)
        return self._records.get(record_id) if record_id else None

    def record_by_bar(self, bar_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_bar.get(bar_id)
        return self._records.get(record_id) if record_id else None

    def records_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_beam.get(beam_id, []))

    def records_by_diameter(self, diameter_mm: int | str) -> List[dict[str, Any]]:
        return self._collect(self._by_diameter.get(str(diameter_mm), []))

    def records_by_development_length(self, development_length_mm: int | float) -> List[dict[str, Any]]:
        return self._collect(self._by_development_length.get(str(development_length_mm), []))

    def records_by_lap_length(self, lap_length_mm: int | float) -> List[dict[str, Any]]:
        return self._collect(self._by_lap_length.get(str(lap_length_mm), []))

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
        by_diameter: dict[str, int] = defaultdict(int)
        by_steel: dict[str, int] = defaultdict(int)
        by_concrete: dict[str, int] = defaultdict(int)
        by_factor: dict[str, int] = defaultdict(int)
        by_source: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("determination_state", LapLengthState.DEFERRED.value))
            by_state[state] += 1
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                by_beam[beam_id] += 1
            diameter = str(record.get("bar_diameter_mm", ""))
            if diameter:
                by_diameter[diameter] += 1
            steel = str(record.get("steel_grade", ""))
            if steel:
                by_steel[steel] += 1
            concrete = str(record.get("concrete_grade", ""))
            if concrete:
                by_concrete[concrete] += 1
            factor = record.get("lap_factor")
            if factor is not None:
                by_factor[str(factor)] += 1
            source = str(record.get("lap_rule_source", ""))
            if source:
                by_source[source] += 1

        state_counts = {
            "calculated": by_state.get(LapLengthState.CALCULATED.value, 0),
            "deferred": by_state.get(LapLengthState.DEFERRED.value, 0),
            "blocked": by_state.get(LapLengthState.BLOCKED.value, 0),
            "failed": by_state.get(LapLengthState.FAILED.value, 0),
        }

        return {
            "namespace": NAMESPACE_LAP_LENGTH,
            "phase": "Phase I.5",
            "registry_id": format_lap_length_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("lap_length_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam": dict(by_beam),
            "results_by_diameter": dict(by_diameter),
            "results_by_steel_grade": dict(by_steel),
            "results_by_concrete_grade": dict(by_concrete),
            "results_by_lap_factor": dict(by_factor),
            "results_by_rule_source": dict(by_source),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }

    def _collect(self, record_ids: List[str]) -> List[dict[str, Any]]:
        return [self._records[record_id] for record_id in record_ids if record_id in self._records]
