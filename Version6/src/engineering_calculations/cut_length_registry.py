"""Cut length registry — Phase I.6."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_calculations.cut_length_types import (
    NAMESPACE_CUT_LENGTH,
    CutLengthState,
)


def format_cut_length_id(sequence: int) -> str:
    return f"CUT_LENGTH::{sequence:06d}"


def format_cut_length_registry_id() -> str:
    return "CUT_LENGTH_REGISTRY"


class CutLengthRegistry:
    """Sequence registry with O(1) lookups for cut length determinations."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_result: dict[str, str] = {}
        self._by_bar: dict[str, str] = {}
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._by_context: dict[str, List[str]] = defaultdict(list)
        self._by_specification: dict[str, List[str]] = defaultdict(list)
        self._by_diameter: dict[str, List[str]] = defaultdict(list)
        self._by_role: dict[str, List[str]] = defaultdict(list)
        self._by_bar_type: dict[str, List[str]] = defaultdict(list)
        self._by_cut_length: dict[str, List[str]] = defaultdict(list)
        self._by_state: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_cut_length_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("cut_length_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["cut_length_id"] = record_id

        self._records[record_id] = record

        result_id = str(record.get("result_id", ""))
        bar_id = str(record.get("bar_id", ""))
        beam_id = str(record.get("beam_id", ""))
        context_id = str(record.get("context_id", ""))
        specification_id = str(record.get("specification_id", ""))
        diameter = str(record.get("bar_diameter_mm", ""))
        role = str(record.get("reinforcement_role", ""))
        bar_type = str(record.get("bar_type", ""))
        cut_length = record.get("cut_length_mm")
        state = str(record.get("determination_state", ""))

        if result_id:
            self._by_result[result_id] = record_id
        if bar_id:
            self._by_bar[bar_id] = record_id
        if beam_id and record_id not in self._by_beam[beam_id]:
            self._by_beam[beam_id].append(record_id)
        if context_id and record_id not in self._by_context[context_id]:
            self._by_context[context_id].append(record_id)
        if specification_id and record_id not in self._by_specification[specification_id]:
            self._by_specification[specification_id].append(record_id)
        if diameter and record_id not in self._by_diameter[diameter]:
            self._by_diameter[diameter].append(record_id)
        if role and record_id not in self._by_role[role]:
            self._by_role[role].append(record_id)
        if bar_type and record_id not in self._by_bar_type[bar_type]:
            self._by_bar_type[bar_type].append(record_id)
        if cut_length is not None and record_id not in self._by_cut_length[str(cut_length)]:
            self._by_cut_length[str(cut_length)].append(record_id)
        if state and record_id not in self._by_state[state]:
            self._by_state[state].append(record_id)

        return record_id

    def record(self, cut_length_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(cut_length_id)

    def record_by_result(self, result_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_result.get(result_id)
        return self._records.get(record_id) if record_id else None

    def record_by_bar(self, bar_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_bar.get(bar_id)
        return self._records.get(record_id) if record_id else None

    def records_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_beam.get(beam_id, []))

    def records_by_role(self, role: str) -> List[dict[str, Any]]:
        return self._collect(self._by_role.get(role, []))

    def records_by_diameter(self, diameter_mm: int | str) -> List[dict[str, Any]]:
        return self._collect(self._by_diameter.get(str(diameter_mm), []))

    def records_by_cut_length(self, cut_length_mm: int | float) -> List[dict[str, Any]]:
        return self._collect(self._by_cut_length.get(str(cut_length_mm), []))

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
        by_role: dict[str, int] = defaultdict(int)
        by_bar_type: dict[str, int] = defaultdict(int)
        by_source: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("determination_state", CutLengthState.DEFERRED.value))
            by_state[state] += 1
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                by_beam[beam_id] += 1
            diameter = str(record.get("bar_diameter_mm", ""))
            if diameter:
                by_diameter[diameter] += 1
            role = str(record.get("reinforcement_role", ""))
            if role:
                by_role[role] += 1
            bar_type = str(record.get("bar_type", ""))
            if bar_type:
                by_bar_type[bar_type] += 1
            source = str(record.get("cut_rule_source", ""))
            if source:
                by_source[source] += 1

        state_counts = {
            "calculated": by_state.get(CutLengthState.CALCULATED.value, 0),
            "deferred": by_state.get(CutLengthState.DEFERRED.value, 0),
            "blocked": by_state.get(CutLengthState.BLOCKED.value, 0),
            "failed": by_state.get(CutLengthState.FAILED.value, 0),
        }

        return {
            "namespace": NAMESPACE_CUT_LENGTH,
            "phase": "Phase I.6",
            "registry_id": format_cut_length_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("cut_length_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam": dict(by_beam),
            "results_by_diameter": dict(by_diameter),
            "results_by_role": dict(by_role),
            "results_by_bar_type": dict(by_bar_type),
            "results_by_rule_source": dict(by_source),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }

    def _collect(self, record_ids: List[str]) -> List[dict[str, Any]]:
        return [self._records[record_id] for record_id in record_ids if record_id in self._records]
