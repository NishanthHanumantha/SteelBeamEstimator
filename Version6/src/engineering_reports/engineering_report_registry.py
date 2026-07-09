"""Engineering report registry — Phase I.16."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_reports.engineering_report_types import (
    NAMESPACE_ENGINEERING_REPORT,
    ReportState,
    format_engineering_report_id,
    format_engineering_report_registry_id,
)


class EngineeringReportRegistry:
    """Sequence registry with O(1) lookups for engineering report records."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_beam: dict[str, str] = {}
        self._by_beam_mark: dict[str, str] = {}
        self._by_engineering_ready: dict[str, List[str]] = defaultdict(list)
        self._by_quality_ready: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_engineering_report_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("report_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["report_id"] = record_id

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

        return record_id

    def record(self, report_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(report_id)

    def record_by_beam(self, beam_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_beam.get(beam_id)
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
        by_engineering_ready: dict[str, int] = defaultdict(int)
        by_quality_ready: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("report_state", ReportState.UNKNOWN.value))
            by_state[state] += 1
            by_beam[str(record.get("beam_id", ""))] += 1
            by_beam_mark[str(record.get("beam_mark", ""))] += 1
            by_engineering_ready[str(bool(record.get("engineering_ready")))] += 1
            by_quality_ready[str(bool(record.get("quality_ready")))] += 1

        return {
            "namespace": NAMESPACE_ENGINEERING_REPORT,
            "phase": "Phase I.16",
            "registry_id": format_engineering_report_registry_id(),
            "determination_count": len(records),
            "determination_ids": sorted(str(item.get("report_id", "")) for item in records),
            "results_by_state": dict(by_state),
            "state_counts": dict(by_state),
            "results_by_beam": dict(by_beam),
            "results_by_beam_mark": dict(by_beam_mark),
            "results_by_engineering_ready": dict(by_engineering_ready),
            "results_by_quality_ready": dict(by_quality_ready),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }
