"""Bar identity registry — Phase I.8."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_calculations.bar_identity.bar_identity_types import (
    NAMESPACE_BAR_IDENTITY,
    BarIdentityState,
    format_bar_identity_record_id,
    format_bar_identity_registry_id,
)


class BarIdentityRegistry:
    """Sequence registry with O(1) lookups for bar identity determinations."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_result: dict[str, str] = {}
        self._by_bar: dict[str, str] = {}
        self._by_engineering_bar: dict[str, str] = {}
        self._by_engineering_group: dict[str, List[str]] = defaultdict(list)
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._by_role: dict[str, List[str]] = defaultdict(list)
        self._by_diameter: dict[str, List[str]] = defaultdict(list)
        self._by_shape_code: dict[str, List[str]] = defaultdict(list)
        self._by_bar_mark: dict[str, str] = {}
        self._by_state: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_bar_identity_record_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("bar_identity_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["bar_identity_id"] = record_id

        self._records[record_id] = record

        result_id = str(record.get("result_id", ""))
        bar_id = str(record.get("bar_id", ""))
        engineering_bar_id = str(record.get("engineering_bar_id", ""))
        engineering_group_id = str(record.get("engineering_group_id", ""))
        beam_id = str(record.get("beam_id", ""))
        role = str(record.get("reinforcement_role", ""))
        diameter = str(record.get("bar_diameter_mm", ""))
        shape_code = str(record.get("shape_code", ""))
        bar_mark = str(record.get("engineering_bar_mark", ""))
        state = str(record.get("determination_state", ""))

        if result_id:
            self._by_result[result_id] = record_id
        if bar_id:
            self._by_bar[bar_id] = record_id
        if engineering_bar_id:
            self._by_engineering_bar[engineering_bar_id] = record_id
        if engineering_group_id and record_id not in self._by_engineering_group[engineering_group_id]:
            self._by_engineering_group[engineering_group_id].append(record_id)
        if beam_id and record_id not in self._by_beam[beam_id]:
            self._by_beam[beam_id].append(record_id)
        if role and record_id not in self._by_role[role]:
            self._by_role[role].append(record_id)
        if diameter and record_id not in self._by_diameter[diameter]:
            self._by_diameter[diameter].append(record_id)
        if shape_code and record_id not in self._by_shape_code[shape_code]:
            self._by_shape_code[shape_code].append(record_id)
        if bar_mark:
            self._by_bar_mark[bar_mark] = record_id
        if state and record_id not in self._by_state[state]:
            self._by_state[state].append(record_id)

        return record_id

    def record(self, bar_identity_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(bar_identity_id)

    def record_by_bar(self, bar_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_bar.get(bar_id)
        return self._records.get(record_id) if record_id else None

    def record_by_engineering_bar(self, engineering_bar_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_engineering_bar.get(engineering_bar_id)
        return self._records.get(record_id) if record_id else None

    def records_by_group(self, engineering_group_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_engineering_group.get(engineering_group_id, []))

    def records_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_beam.get(beam_id, []))

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
        by_role: dict[str, int] = defaultdict(int)
        by_diameter: dict[str, int] = defaultdict(int)
        by_shape_code: dict[str, int] = defaultdict(int)
        by_group: dict[str, int] = defaultdict(int)
        by_source: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("determination_state", BarIdentityState.DEFERRED.value))
            by_state[state] += 1
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                by_beam[beam_id] += 1
            role = str(record.get("reinforcement_role", ""))
            if role:
                by_role[role] += 1
            diameter = str(record.get("bar_diameter_mm", ""))
            if diameter:
                by_diameter[diameter] += 1
            shape_code = str(record.get("shape_code", ""))
            if shape_code:
                by_shape_code[shape_code] += 1
            group_id = str(record.get("engineering_group_id", ""))
            if group_id:
                by_group[group_id] += 1
            source = str(record.get("identity_rule_source", ""))
            if source:
                by_source[source] += 1

        state_counts = {
            "calculated": by_state.get(BarIdentityState.CALCULATED.value, 0),
            "deferred": by_state.get(BarIdentityState.DEFERRED.value, 0),
            "blocked": by_state.get(BarIdentityState.BLOCKED.value, 0),
            "failed": by_state.get(BarIdentityState.FAILED.value, 0),
        }

        return {
            "namespace": NAMESPACE_BAR_IDENTITY,
            "phase": "Phase I.8",
            "registry_id": format_bar_identity_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("bar_identity_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam": dict(by_beam),
            "results_by_role": dict(by_role),
            "results_by_diameter": dict(by_diameter),
            "results_by_shape_code": dict(by_shape_code),
            "results_by_group": dict(by_group),
            "results_by_rule_source": dict(by_source),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }

    def _collect(self, record_ids: List[str]) -> List[dict[str, Any]]:
        return [self._records[record_id] for record_id in record_ids if record_id in self._records]
