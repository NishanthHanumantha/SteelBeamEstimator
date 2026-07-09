"""Beam summary registry — Phase I.12."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_calculations.beam_summary.beam_summary_types import (
    BeamSummaryState,
    NAMESPACE_BEAM_SUMMARY,
    format_beam_summary_id,
    format_beam_summary_registry_id,
)


class BeamSummaryRegistry:
    """Sequence registry with O(1) lookups for beam summary records."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_beam: dict[str, str] = {}
        self._by_beam_mark: dict[str, str] = {}
        self._by_fabrication_mark: dict[str, str] = {}
        self._by_engineering_group: dict[str, str] = {}
        self._by_identity: dict[str, str] = {}
        self._by_bbs: dict[str, str] = {}
        self._by_shape_code: dict[str, str] = {}
        self._by_diameter: dict[str, str] = {}
        self._by_role: dict[str, str] = {}
        self._by_state: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_beam_summary_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("beam_summary_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["beam_summary_id"] = record_id

        self._records[record_id] = record

        beam_id = str(record.get("beam_id", ""))
        beam_mark = str(record.get("beam_mark", ""))
        state = str(record.get("determination_state", record.get("status", "")))

        if beam_id:
            self._by_beam[beam_id] = record_id
        if beam_mark:
            self._by_beam_mark[beam_mark] = record_id
        if state and record_id not in self._by_state[state]:
            self._by_state[state].append(record_id)

        for fabrication_mark in record.get("fabrication_marks") or []:
            self._by_fabrication_mark[str(fabrication_mark)] = record_id
        for group_id in record.get("member_engineering_group_ids") or []:
            if group_id:
                self._by_engineering_group[str(group_id)] = record_id
        for identity_id in record.get("member_identity_ids") or []:
            if identity_id:
                self._by_identity[str(identity_id)] = record_id
        for bbs_id in record.get("member_bbs_ids") or []:
            if bbs_id:
                self._by_bbs[str(bbs_id)] = record_id
        for shape_code in record.get("shape_codes") or []:
            if shape_code:
                self._by_shape_code[str(shape_code)] = record_id
        for diameter in record.get("diameters") or []:
            self._by_diameter[str(diameter)] = record_id
        for role in record.get("roles") or []:
            if role:
                self._by_role[str(role)] = record_id

        return record_id

    def record(self, beam_summary_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(beam_summary_id)

    def record_by_beam(self, beam_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_beam.get(beam_id)
        return self._records.get(record_id) if record_id else None

    def record_by_beam_mark(self, beam_mark: str) -> Optional[dict[str, Any]]:
        record_id = self._by_beam_mark.get(beam_mark)
        return self._records.get(record_id) if record_id else None

    def record_by_fabrication_mark(self, fabrication_mark: str) -> Optional[dict[str, Any]]:
        record_id = self._by_fabrication_mark.get(fabrication_mark)
        return self._records.get(record_id) if record_id else None

    def record_by_engineering_group(self, engineering_group_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_engineering_group.get(engineering_group_id)
        return self._records.get(record_id) if record_id else None

    def record_by_identity(self, bar_identity_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_identity.get(bar_identity_id)
        return self._records.get(record_id) if record_id else None

    def record_by_bbs(self, bbs_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_bbs.get(bbs_id)
        return self._records.get(record_id) if record_id else None

    def record_by_shape_code(self, shape_code: str) -> Optional[dict[str, Any]]:
        record_id = self._by_shape_code.get(shape_code)
        return self._records.get(record_id) if record_id else None

    def record_by_diameter(self, diameter: str | int) -> Optional[dict[str, Any]]:
        record_id = self._by_diameter.get(str(diameter))
        return self._records.get(record_id) if record_id else None

    def record_by_role(self, role: str) -> Optional[dict[str, Any]]:
        record_id = self._by_role.get(role)
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
        by_fabrication_mark: dict[str, int] = defaultdict(int)
        by_shape_code: dict[str, int] = defaultdict(int)
        by_diameter: dict[str, int] = defaultdict(int)
        by_role: dict[str, int] = defaultdict(int)
        by_engineering_group: dict[str, int] = defaultdict(int)
        by_bbs: dict[str, int] = defaultdict(int)
        by_identity: dict[str, int] = defaultdict(int)
        by_fabrication_state: dict[str, int] = defaultdict(int)
        by_engineering_state: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("determination_state", BeamSummaryState.EMPTY.value))
            by_state[state] += 1
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                by_beam[beam_id] += 1
            beam_mark = str(record.get("beam_mark", ""))
            if beam_mark:
                by_beam_mark[beam_mark] += 1
            fab_state = str(record.get("fabrication_state", ""))
            if fab_state:
                by_fabrication_state[fab_state] += 1
            eng_state = str(record.get("engineering_state", ""))
            if eng_state:
                by_engineering_state[eng_state] += 1
            for mark in record.get("fabrication_marks") or []:
                by_fabrication_mark[str(mark)] += 1
            for shape in record.get("shape_codes") or []:
                by_shape_code[str(shape)] += 1
            for diameter in record.get("diameters") or []:
                by_diameter[str(diameter)] += 1
            for role in record.get("roles") or []:
                by_role[str(role)] += 1
            for group_id in record.get("member_engineering_group_ids") or []:
                by_engineering_group[str(group_id)] += 1
            for bbs_id in record.get("member_bbs_ids") or []:
                by_bbs[str(bbs_id)] += 1
            for identity_id in record.get("member_identity_ids") or []:
                by_identity[str(identity_id)] += 1

        state_counts = {
            "calculated": by_state.get(BeamSummaryState.CALCULATED.value, 0),
            "partial": by_state.get(BeamSummaryState.PARTIAL.value, 0),
            "blocked": by_state.get(BeamSummaryState.BLOCKED.value, 0),
            "empty": by_state.get(BeamSummaryState.EMPTY.value, 0),
        }

        return {
            "namespace": NAMESPACE_BEAM_SUMMARY,
            "phase": "Phase I.12",
            "registry_id": format_beam_summary_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("beam_summary_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam": dict(by_beam),
            "results_by_beam_mark": dict(by_beam_mark),
            "results_by_fabrication_mark": dict(by_fabrication_mark),
            "results_by_shape_code": dict(by_shape_code),
            "results_by_diameter": dict(by_diameter),
            "results_by_role": dict(by_role),
            "results_by_engineering_group": dict(by_engineering_group),
            "results_by_bbs": dict(by_bbs),
            "results_by_identity": dict(by_identity),
            "results_by_fabrication_state": dict(by_fabrication_state),
            "results_by_engineering_state": dict(by_engineering_state),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }
