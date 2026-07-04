"""Bar group registry — Phase I.9."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_calculations.bar_group.bar_group_types import (
    NAMESPACE_BAR_GROUP,
    BarGroupState,
    format_bar_group_record_id,
    format_bar_group_registry_id,
)


class BarGroupRegistry:
    """Sequence registry with O(1) lookups for bar group determinations."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_engineering_group: dict[str, str] = {}
        self._by_signature: dict[str, str] = {}
        self._by_bar: dict[str, List[str]] = defaultdict(list)
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._by_state: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_bar_group_record_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("bar_group_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["bar_group_id"] = record_id

        self._records[record_id] = record

        engineering_group_id = str(record.get("engineering_group_id", ""))
        engineering_signature = str(record.get("engineering_signature", ""))
        state = str(record.get("determination_state", ""))

        if engineering_group_id:
            self._by_engineering_group[engineering_group_id] = record_id
        if engineering_signature:
            self._by_signature[engineering_signature] = record_id
        if state and record_id not in self._by_state[state]:
            self._by_state[state].append(record_id)

        for bar_id in record.get("member_bar_ids") or []:
            bar_key = str(bar_id)
            if record_id not in self._by_bar[bar_key]:
                self._by_bar[bar_key].append(record_id)
        for beam_id in record.get("member_beams") or []:
            beam_key = str(beam_id)
            if record_id not in self._by_beam[beam_key]:
                self._by_beam[beam_key].append(record_id)

        return record_id

    def record(self, bar_group_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(bar_group_id)

    def record_by_engineering_group(self, engineering_group_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_engineering_group.get(engineering_group_id)
        return self._records.get(record_id) if record_id else None

    def record_by_signature(self, engineering_signature: str) -> Optional[dict[str, Any]]:
        record_id = self._by_signature.get(engineering_signature)
        return self._records.get(record_id) if record_id else None

    def records_by_bar(self, bar_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_bar.get(bar_id, []))

    def records_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return self._collect(self._by_beam.get(beam_id, []))

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
        by_signature: dict[str, int] = defaultdict(int)
        by_source: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("determination_state", BarGroupState.DEFERRED.value))
            by_state[state] += 1
            source = str(record.get("rule_source", ""))
            if source:
                by_source[source] += 1
            signature = str(record.get("engineering_signature", ""))
            if signature:
                by_signature[signature] += 1
            for role in record.get("member_roles") or []:
                by_role[str(role)] += 1
            diameter = record.get("diameter")
            if diameter is not None:
                by_diameter[str(diameter)] += 1
            shape_code = record.get("shape_code")
            if shape_code:
                by_shape_code[str(shape_code)] += 1
            for beam_id in record.get("member_beams") or []:
                by_beam[str(beam_id)] += 1

        state_counts = {
            "calculated": by_state.get(BarGroupState.CALCULATED.value, 0),
            "deferred": by_state.get(BarGroupState.DEFERRED.value, 0),
            "blocked": by_state.get(BarGroupState.BLOCKED.value, 0),
            "failed": by_state.get(BarGroupState.FAILED.value, 0),
        }

        return {
            "namespace": NAMESPACE_BAR_GROUP,
            "phase": "Phase I.9",
            "registry_id": format_bar_group_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("bar_group_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam": dict(by_beam),
            "results_by_role": dict(by_role),
            "results_by_diameter": dict(by_diameter),
            "results_by_shape_code": dict(by_shape_code),
            "results_by_signature": dict(by_signature),
            "results_by_rule_source": dict(by_source),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }

    def _collect(self, record_ids: List[str]) -> List[dict[str, Any]]:
        return [self._records[record_id] for record_id in record_ids if record_id in self._records]
