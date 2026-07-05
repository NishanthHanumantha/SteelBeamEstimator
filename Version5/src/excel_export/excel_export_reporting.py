"""Excel export reporting — Phase I.17."""

from __future__ import annotations

from typing import Any, List

from src.excel_export.excel_export_summary import ExcelExportSummary


class ExcelExportReporting:
    """Single source of truth for excel export validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        model["excel_export_validation"] = validation
        model["excel_export_summary"] = ExcelExportSummary.build(
            model.get("engineering_report_results", []),
            model.get("excel_export_results", []),
            model.get("excel_export_registry", {}),
            validation,
        )
        model["excel_export_reporting"] = ExcelExportReporting.build(
            model.get("excel_export_results", []),
            model["excel_export_summary"],
            validation,
        )

    @staticmethod
    def build(
        export_records: List[dict[str, Any]],
        summary: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        rows: List[dict[str, Any]] = []
        for export in export_records:
            rows.append({
                "export_id": export.get("export_id"),
                "output_path": export.get("output_path"),
                "template_used": export.get("template_used"),
                "template_path": export.get("template_path"),
                "worksheet_name": export.get("worksheet_name"),
                "rows_written": export.get("rows_written", 0),
                "cells_written": export.get("cells_written", 0),
                "copied_styles": export.get("copied_styles", 0),
                "inserted_rows": export.get("inserted_rows", 0),
                "status": export.get("status"),
                "validation_status": export.get("validation_status"),
                "warnings": export.get("warnings", []),
                "errors": export.get("errors", []),
                "generation_time": export.get("generation_time"),
            })

        return {
            "phase": "Phase I.17",
            "status": validation.get("status", "SKIP"),
            "workbook_count": summary.get("workbook_count", 0),
            "worksheet_count": summary.get("worksheet_count", 0),
            "rows_written": summary.get("rows_written", 0),
            "cells_written": summary.get("cells_written", 0),
            "inserted_rows": summary.get("inserted_rows", 0),
            "copied_styles": summary.get("copied_styles", 0),
            "template_used": summary.get("template_used", False),
            "successful_exports": summary.get("successful_exports", 0),
            "failed_exports": summary.get("failed_exports", 0),
            "export_rows": rows,
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
            "checks_passed": validation.get("summary", {}).get("passed", 0),
            "checks_failed": validation.get("summary", {}).get("failed", 0),
            "checks_total": validation.get("summary", {}).get("total_checks", 0),
        }
