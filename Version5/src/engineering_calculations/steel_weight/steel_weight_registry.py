"""Steel weight registry — Phase I.11."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_calculations.steel_weight.steel_weight_types import (
    NAMESPACE_WEIGHT,
    SteelWeightState,
    format_weight_record_id,
    format_weight_registry_id,
)


class SteelWeightRegistry:
    """Sequence registry with O(1) lookups for steel weight records."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_bar: dict[str, str] = {}
        self._by_identity: dict[str, str] = {}
        self._by_engineering_group: dict[str, List[str]] = defaultdict(list)
        self._by_fabrication_mark: dict[str, str] = {}
        self._by_bbs: dict[str, str] = {}
        self._by_beam: dict[str, List[str]] = defaultdict(list)
        self._by_state: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_weight_record_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("weight_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["weight_id"] = record_id

        self._records[record_id] = record

        bar_id = str(record.get("bar_id", ""))
        identity_id = str(record.get("bar_identity_id", ""))
        engineering_group_id = str(record.get("engineering_group_id", ""))
        fabrication_mark = str(record.get("fabrication_mark", ""))
        bbs_id = str(record.get("bbs_id", ""))
        beam_id = str(record.get("beam_id", ""))
        state = str(record.get("status", ""))

        if bar_id:
            self._by_bar[bar_id] = record_id
        if identity_id:
            self._by_identity[identity_id] = record_id
        if engineering_group_id and record_id not in self._by_engineering_group[engineering_group_id]:
            self._by_engineering_group[engineering_group_id].append(record_id)
        if fabrication_mark:
            self._by_fabrication_mark[fabrication_mark] = record_id
        if bbs_id:
            self._by_bbs[bbs_id] = record_id
        if beam_id and record_id not in self._by_beam[beam_id]:
            self._by_beam[beam_id].append(record_id)
        if state and record_id not in self._by_state[state]:
            self._by_state[state].append(record_id)

        return record_id

    def record(self, weight_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(weight_id)

    def record_by_bar(self, bar_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_bar.get(bar_id)
        return self._records.get(record_id) if record_id else None

    def record_by_identity(self, bar_identity_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_identity.get(bar_identity_id)
        return self._records.get(record_id) if record_id else None

    def records_by_engineering_group(self, engineering_group_id: str) -> List[dict[str, Any]]:
        return [
            self._records[record_id]
            for record_id in self._by_engineering_group.get(engineering_group_id, [])
            if record_id in self._records
        ]

    def record_by_fabrication_mark(self, fabrication_mark: str) -> Optional[dict[str, Any]]:
        record_id = self._by_fabrication_mark.get(fabrication_mark)
        return self._records.get(record_id) if record_id else None

    def record_by_bbs(self, bbs_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_bbs.get(bbs_id)
        return self._records.get(record_id) if record_id else None

    def records_by_beam(self, beam_id: str) -> List[dict[str, Any]]:
        return [
            self._records[record_id]
            for record_id in self._by_beam.get(beam_id, [])
            if record_id in self._records
        ]

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
        by_fabrication_state: dict[str, int] = defaultdict(int)
        by_fabrication_mark: dict[str, int] = defaultdict(int)
        by_engineering_group: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("status", SteelWeightState.DEFERRED.value))
            by_state[state] += 1
            role = record.get("role")
            if role:
                by_role[str(role)] += 1
            diameter = record.get("diameter")
            if diameter is not None:
                by_diameter[str(diameter)] += 1
            shape_code = record.get("shape_code")
            if shape_code:
                by_shape_code[str(shape_code)] += 1
            fab_state = record.get("fabrication_state")
            if fab_state:
                by_fabrication_state[str(fab_state)] += 1
            fab_mark = record.get("fabrication_mark")
            if fab_mark:
                by_fabrication_mark[str(fab_mark)] += 1
            group_id = record.get("engineering_group_id")
            if group_id:
                by_engineering_group[str(group_id)] += 1
            beam_id = record.get("beam_id")
            if beam_id:
                by_beam[str(beam_id)] += 1

        state_counts = {
            "calculated": by_state.get(SteelWeightState.CALCULATED.value, 0),
            "deferred": by_state.get(SteelWeightState.DEFERRED.value, 0),
            "blocked": by_state.get(SteelWeightState.BLOCKED.value, 0),
            "failed": by_state.get(SteelWeightState.FAILED.value, 0),
        }

        return {
            "namespace": NAMESPACE_WEIGHT,
            "phase": "Phase I.11",
            "registry_id": format_weight_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("weight_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam": dict(by_beam),
            "results_by_role": dict(by_role),
            "results_by_diameter": dict(by_diameter),
            "results_by_shape_code": dict(by_shape_code),
            "results_by_fabrication_state": dict(by_fabrication_state),
            "results_by_fabrication_mark": dict(by_fabrication_mark),
            "results_by_engineering_group": dict(by_engineering_group),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }
