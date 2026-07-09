"""Excel export registry — Phase I.17."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, List, Optional

from src.excel_export.excel_export_types import (
    NAMESPACE_EXCEL_EXPORT,
    ExportState,
    format_excel_export_id,
    format_excel_export_registry_id,
)


class ExcelExportRegistry:
    """Sequence registry with O(1) lookups for excel export records."""

    def __init__(self) -> None:
        self._sequence = 0
        self._records: dict[str, dict[str, Any]] = {}
        self._by_template: dict[str, str] = {}

    def next_id(self) -> str:
        self._sequence += 1
        return format_excel_export_id(self._sequence)

    def register(self, record: dict[str, Any]) -> str:
        record_id = str(record.get("export_id") or "")
        if not record_id:
            record_id = self.next_id()
            record["export_id"] = record_id

        self._records[record_id] = record
        template_key = str(record.get("template_path", ""))
        if template_key:
            self._by_template[template_key] = record_id
        return record_id

    def record(self, export_id: str) -> Optional[dict[str, Any]]:
        return self._records.get(export_id)

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
        by_template: dict[str, int] = defaultdict(int)

        for record in records:
            state = str(record.get("status", ExportState.UNKNOWN.value))
            by_state[state] += 1
            template_key = "template" if record.get("template_used") else "fallback"
            by_template[template_key] += 1

        return {
            "namespace": NAMESPACE_EXCEL_EXPORT,
            "phase": "Phase I.17",
            "registry_id": format_excel_export_registry_id(),
            "determination_count": len(records),
            "determination_ids": sorted(str(item.get("export_id", "")) for item in records),
            "results_by_state": dict(by_state),
            "state_counts": dict(by_state),
            "results_by_template": dict(by_template),
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
        }
