"""Material quantification registry — Phase I.14."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.engineering_calculations.material_quantification.material_types import (
    MaterialState,
    NAMESPACE_MATERIAL,
    format_material_id,
    format_material_registry_id,
)


class MaterialRegistry:
    """Sequence registry with O(1) lookups for material records."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_material_type: dict[str, List[str]] = defaultdict(list)
        self._by_steel_grade: dict[str, List[str]] = defaultdict(list)
        self._by_diameter: dict[str, List[str]] = defaultdict(list)
        self._by_material_state: dict[str, List[str]] = defaultdict(list)
        self._by_engineering_ready: dict[str, List[str]] = defaultdict(list)
        self._by_quality_ready: dict[str, List[str]] = defaultdict(list)
        self._by_beam: dict[str, str] = {}
        self._by_beam_mark: dict[str, str] = {}
        self._by_fabrication_mark: dict[str, str] = {}

    def next_id(self) -> str:
        self._sequence += 1
        return format_material_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("material_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["material_id"] = record_id

        self._records[record_id] = record

        material_type = str(record.get("material_type", ""))
        steel_grade = str(record.get("steel_grade", ""))
        diameter = str(record.get("diameter_mm", ""))
        state = str(record.get("material_state", record.get("status", "")))

        if material_type and record_id not in self._by_material_type.setdefault(material_type, []):
            self._by_material_type[material_type].append(record_id)
        if steel_grade and record_id not in self._by_steel_grade[steel_grade]:
            self._by_steel_grade[steel_grade].append(record_id)
        if diameter and record_id not in self._by_diameter[diameter]:
            self._by_diameter[diameter].append(record_id)
        if state and record_id not in self._by_material_state[state]:
            self._by_material_state[state].append(record_id)

        eng_key = str(bool(record.get("engineering_ready")))
        qual_key = str(bool(record.get("quality_ready")))
        if record_id not in self._by_engineering_ready[eng_key]:
            self._by_engineering_ready[eng_key].append(record_id)
        if record_id not in self._by_quality_ready[qual_key]:
            self._by_quality_ready[qual_key].append(record_id)

        for beam_id in record.get("beam_ids") or []:
            if beam_id:
                self._by_beam[str(beam_id)] = record_id
        for beam_mark in record.get("beam_marks") or []:
            if beam_mark:
                self._by_beam_mark[str(beam_mark)] = record_id
        for fabrication_mark in record.get("fabrication_marks") or []:
            if fabrication_mark:
                self._by_fabrication_mark[str(fabrication_mark)] = record_id

        return record_id

    def record(self, material_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(material_id)

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
        by_material_type: dict[str, int] = defaultdict(int)
        by_steel_grade: dict[str, int] = defaultdict(int)
        by_diameter: dict[str, int] = defaultdict(int)
        by_material_state: dict[str, int] = defaultdict(int)
        by_engineering_ready: dict[str, int] = defaultdict(int)
        by_quality_ready: dict[str, int] = defaultdict(int)
        by_beam: dict[str, int] = defaultdict(int)
        by_beam_mark: dict[str, int] = defaultdict(int)
        by_fabrication_mark: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("material_state", MaterialState.UNKNOWN.value))
            by_state[state] += 1
            by_material_state[state] += 1
            by_material_type[str(record.get("material_type", ""))] += 1
            by_steel_grade[str(record.get("steel_grade", ""))] += 1
            by_diameter[str(record.get("diameter_mm", ""))] += 1
            by_engineering_ready[str(bool(record.get("engineering_ready")))] += 1
            by_quality_ready[str(bool(record.get("quality_ready")))] += 1
            for beam_id in record.get("beam_ids") or []:
                by_beam[str(beam_id)] += 1
            for beam_mark in record.get("beam_marks") or []:
                by_beam_mark[str(beam_mark)] += 1
            for mark in record.get("fabrication_marks") or []:
                by_fabrication_mark[str(mark)] += 1

        state_counts = {
            "ready": by_state.get(MaterialState.READY.value, 0),
            "deferred": by_state.get(MaterialState.DEFERRED.value, 0),
            "blocked": by_state.get(MaterialState.BLOCKED.value, 0),
            "empty": by_state.get(MaterialState.EMPTY.value, 0),
            "unknown": by_state.get(MaterialState.UNKNOWN.value, 0),
        }

        return {
            "namespace": NAMESPACE_MATERIAL,
            "phase": "Phase I.14",
            "registry_id": format_material_registry_id(),
            "determination_count": len(records),
            "determination_ids": [record.get("material_id") for record in records],
            "results_by_state": dict(by_state),
            "state_counts": state_counts,
            "results_by_material_type": dict(by_material_type),
            "results_by_steel_grade": dict(by_steel_grade),
            "results_by_diameter": dict(by_diameter),
            "results_by_material_state": dict(by_material_state),
            "results_by_engineering_ready": dict(by_engineering_ready),
            "results_by_quality_ready": dict(by_quality_ready),
            "results_by_beam": dict(by_beam),
            "results_by_beam_mark": dict(by_beam_mark),
            "results_by_fabrication_mark": dict(by_fabrication_mark),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }
