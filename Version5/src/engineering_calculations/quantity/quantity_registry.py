"""Engineering quantity registry — Phase I.13."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_calculations.quantity.quantity_types import (
    NAMESPACE_QUANTITY,
    QuantityState,
    format_quantity_id,
    format_quantity_registry_id,
)


class QuantityRegistry:
    """Sequence registry with O(1) lookups for quantity records."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_beam_summary: dict[str, str] = {}
        self._by_beam: dict[str, str] = {}
        self._by_beam_mark: dict[str, str] = {}
        self._by_fabrication_mark: dict[str, str] = {}
        self._by_quantity_state: dict[str, List[str]] = defaultdict(list)
        self._by_engineering_ready: dict[str, List[str]] = defaultdict(list)
        self._by_quality_ready: dict[str, List[str]] = defaultdict(list)

    def next_id(self) -> str:
        self._sequence += 1
        return format_quantity_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("quantity_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["quantity_id"] = record_id

        self._records[record_id] = record

        beam_summary_id = str(record.get("beam_summary_id", ""))
        beam_id = str(record.get("beam_id", ""))
        beam_mark = str(record.get("beam_mark", ""))
        state = str(record.get("quantity_state", record.get("status", "")))

        if beam_summary_id:
            self._by_beam_summary[beam_summary_id] = record_id
        if beam_id:
            self._by_beam[beam_id] = record_id
        if beam_mark:
            self._by_beam_mark[beam_mark] = record_id
        if state and record_id not in self._by_quantity_state[state]:
            self._by_quantity_state[state].append(record_id)

        eng_key = str(bool(record.get("engineering_ready")))
        qual_key = str(bool(record.get("quality_ready")))
        if record_id not in self._by_engineering_ready[eng_key]:
            self._by_engineering_ready[eng_key].append(record_id)
        if record_id not in self._by_quality_ready[qual_key]:
            self._by_quality_ready[qual_key].append(record_id)

        for fabrication_mark in record.get("fabrication_marks") or []:
            self._by_fabrication_mark[str(fabrication_mark)] = record_id

        return record_id

    def record(self, quantity_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(quantity_id)

    def record_by_beam_summary(self, beam_summary_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_beam_summary.get(beam_summary_id)
        return self._records.get(record_id) if record_id else None

    def record_by_beam(self, beam_id: str) -> Optional[dict[str, Any]]:
        record_id = self._by_beam.get(beam_id)
        return self._records.get(record_id) if record_id else None

    def record_by_beam_mark(self, beam_mark: str) -> Optional[dict[str, Any]]:
        record_id = self._by_beam_mark.get(beam_mark)
        return self._records.get(record_id) if record_id else None

    def record_by_fabrication_mark(self, fabrication_mark: str) -> Optional[dict[str, Any]]:
        record_id = self._by_fabrication_mark.get(fabrication_mark)
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
        by_beam_summary: dict[str, int] = defaultdict(int)
        by_beam: dict[str, int] = defaultdict(int)
        by_beam_mark: dict[str, int] = defaultdict(int)
        by_fabrication_mark: dict[str, int] = defaultdict(int)
        by_quantity_state: dict[str, int] = defaultdict(int)
        by_engineering_ready: dict[str, int] = defaultdict(int)
        by_quality_ready: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("quantity_state", QuantityState.UNKNOWN.value))
            by_state[state] += 1
            by_quantity_state[state] += 1

            beam_summary_id = str(record.get("beam_summary_id", ""))
            if beam_summary_id:
                by_beam_summary[beam_summary_id] += 1
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                by_beam[beam_id] += 1
            beam_mark = str(record.get("beam_mark", ""))
            if beam_mark:
                by_beam_mark[beam_mark] += 1

            eng_key = str(bool(record.get("engineering_ready")))
            by_engineering_ready[eng_key] += 1
            qual_key = str(bool(record.get("quality_ready")))
            by_quality_ready[qual_key] += 1

            for mark in record.get("fabrication_marks") or []:
                by_fabrication_mark[str(mark)] += 1

        state_counts = {
            "ready": by_state.get(QuantityState.READY.value, 0),
            "deferred": by_state.get(QuantityState.DEFERRED.value, 0),
            "blocked": by_state.get(QuantityState.BLOCKED.value, 0),
            "empty": by_state.get(QuantityState.EMPTY.value, 0),
            "unknown": by_state.get(QuantityState.UNKNOWN.value, 0),
        }

        return {
            "namespace": NAMESPACE_QUANTITY,
            "phase": "Phase I.13",
            "registry_id": format_quantity_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("quantity_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_beam_summary": dict(by_beam_summary),
            "results_by_beam": dict(by_beam),
            "results_by_beam_mark": dict(by_beam_mark),
            "results_by_fabrication_mark": dict(by_fabrication_mark),
            "results_by_quantity_state": dict(by_quantity_state),
            "results_by_engineering_ready": dict(by_engineering_ready),
            "results_by_quality_ready": dict(by_quality_ready),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }
