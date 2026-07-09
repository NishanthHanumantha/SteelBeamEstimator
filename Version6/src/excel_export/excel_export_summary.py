"""Excel export summary — Phase I.17."""

from __future__ import annotations

from typing import Any, List

from src.excel_export.excel_export_types import CREATED_PHASE, ExportState


class ExcelExportSummary:
    """Build project-level excel export statistics."""

    @staticmethod
    def build(
        report_records: List[dict[str, Any]],
        export_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        successful = sum(
            1 for item in export_records if item.get("status") == ExportState.SUCCESS.value
        )
        failed = sum(
            1 for item in export_records if item.get("status") == ExportState.FAILED.value
        )
        fallback = sum(
            1 for item in export_records if item.get("status") == ExportState.FALLBACK.value
        )
        export_record = export_records[0] if export_records else {}
        return {
            "phase": "Phase I.17",
            "framework_phase": CREATED_PHASE,
            "workbook_count": len(export_records),
            "worksheet_count": export_record.get("worksheet_count", 0),
            "rows_written": export_record.get("rows_written", 0),
            "cells_written": export_record.get("cells_written", 0),
            "inserted_rows": export_record.get("inserted_rows", 0),
            "copied_styles": export_record.get("copied_styles", 0),
            "exported_schedule_rows": export_record.get("exported_schedule_rows", 0),
            "template_used": export_record.get("template_used", False),
            "successful_exports": successful,
            "failed_exports": failed,
            "fallback_exports": fallback,
            "total_reports": len(report_records),
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_template": registry.get("results_by_template", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
