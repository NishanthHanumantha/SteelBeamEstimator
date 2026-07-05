"""Beam reinforcement schedule registry — Phase I.15."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_calculations.beam_schedule.beam_schedule_types import (
    NAMESPACE_BEAM_SCHEDULE,
    ScheduleState,
    format_beam_schedule_id,
    format_beam_schedule_registry_id,
    format_schedule_row_id,
)


class BeamScheduleRegistry:
    """Sequence registry with O(1) lookups for beam schedule records."""

    def __init__(self) -> None:
        self._sequence = 0
        self._row_sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_beam: dict[str, str] = {}
        self._by_beam_mark: dict[str, str] = {}
        self._by_role: dict[str, List[str]] = defaultdict(list)
        self._by_diameter: dict[str, List[str]] = defaultdict(list)
        self._by_fabrication_mark: dict[str, List[str]] = defaultdict(list)
        self._by_engineering_ready: dict[str, List[str]] = defaultdict(list)
        self._by_quality_ready: dict[str, List[str]] = defaultdict(list)

    def next_schedule_id(self) -> str:
        self._sequence += 1
        return format_beam_schedule_id(self._sequence)

    def next_row_id(self) -> str:
        self._row_sequence += 1
        return format_schedule_row_id(self._row_sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("beam_schedule_id") or "")
        if not record_id:
            record_id = self.next_schedule_id()
            record["beam_schedule_id"] = record_id

        for row in record.get("rows") or []:
            if not row.get("row_id"):
                row["row_id"] = self.next_row_id()

        self._records[record_id] = record

        beam_id = str(record.get("beam_id", ""))
        beam_mark = str(record.get("beam_mark", ""))
        if beam_id:
            self._by_beam[beam_id] = record_id
        if beam_mark:
            self._by_beam_mark[beam_mark] = record_id

        eng_key = str(bool(record.get("engineering_ready")))
        qual_key = str(bool(record.get("quality_ready")))
        if record_id not in self._by_engineering_ready[eng_key]:
            self._by_engineering_ready[eng_key].append(record_id)
        if record_id not in self._by_quality_ready[qual_key]:
            self._by_quality_ready[qual_key].append(record_id)

        for row in record.get("rows") or []:
            role = str(row.get("role") or "")
            diameter = str(row.get("diameter_mm", ""))
            fabrication_mark = str(row.get("fabrication_mark") or "")
            if role and record_id not in self._by_role[role]:
                self._by_role[role].append(record_id)
            if diameter and record_id not in self._by_diameter[diameter]:
                self._by_diameter[diameter].append(record_id)
            if fabrication_mark and record_id not in self._by_fabrication_mark[fabrication_mark]:
                self._by_fabrication_mark[fabrication_mark].append(record_id)

        return record_id

    def record(self, beam_schedule_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(beam_schedule_id)

    def record_by_beam(self, beam_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_beam.get(beam_id)
        return self._records.get(record_id) if record_id else None

    def record_by_beam_mark(self, beam_mark: str) -> Optional[dict[str, Any]]:
        record_id = self._by_beam_mark.get(beam_mark)
        return self._records.get(record_id) if record_id else None

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
        by_beam_mark: dict[str, int] = defaultdict(int)
        by_role: dict[str, int] = defaultdict(int)
        by_diameter: dict[str, int] = defaultdict(int)
        by_fabrication_mark: dict[str, int] = defaultdict(int)
        by_engineering_ready: dict[str, int] = defaultdict(int)
        by_quality_ready: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("schedule_state", ScheduleState.UNKNOWN.value))
            by_state[state] += 1
            by_beam[str(record.get("beam_id", ""))] += 1
            by_beam_mark[str(record.get("beam_mark", ""))] += 1
            by_engineering_ready[str(bool(record.get("engineering_ready")))] += 1
            by_quality_ready[str(bool(record.get("quality_ready")))] += 1
            for row in record.get("rows") or []:
                by_role[str(row.get("role") or "")] += 1
                by_diameter[str(row.get("diameter_mm", ""))] += 1
                if row.get("fabrication_mark"):
                    by_fabrication_mark[str(row.get("fabrication_mark"))] += 1

        return {
            "namespace": NAMESPACE_BEAM_SCHEDULE,
            "phase": "Phase I.15",
            "registry_id": format_beam_schedule_registry_id(),
            "determination_count": len(records),
            "determination_ids": sorted(str(item.get("beam_schedule_id", "")) for item in records),
            "results_by_state": dict(by_state),
            "state_counts": dict(by_state),
            "results_by_beam": dict(by_beam),
            "results_by_beam_mark": dict(by_beam_mark),
            "results_by_role": dict(by_role),
            "results_by_diameter": dict(by_diameter),
            "results_by_fabrication_mark": dict(by_fabrication_mark),
            "results_by_engineering_ready": dict(by_engineering_ready),
            "results_by_quality_ready": dict(by_quality_ready),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }
