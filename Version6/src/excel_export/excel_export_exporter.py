"""Excel export JSON export helpers — Phase I.17."""

from __future__ import annotations

from typing import Any, List


class ExcelExportExporter:
    """Serialize excel export artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.17",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.17",
            "workbook_count": summary.get("workbook_count", 0),
            "worksheet_count": summary.get("worksheet_count", 0),
            "rows_written": summary.get("rows_written", 0),
            "cells_written": summary.get("cells_written", 0),
            "inserted_rows": summary.get("inserted_rows", 0),
            "copied_styles": summary.get("copied_styles", 0),
            "template_used": summary.get("template_used", False),
            "successful_exports": summary.get("successful_exports", 0),
            "failed_exports": summary.get("failed_exports", 0),
            "fallback_exports": summary.get("fallback_exports", 0),
        }

    @staticmethod
    def export_report_bundle(
        summary: dict[str, Any],
        reporting: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.17",
            "summary": summary,
            "reporting": reporting,
        }
