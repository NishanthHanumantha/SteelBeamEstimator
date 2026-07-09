"""Engineering report reporting — Phase I.16."""

from __future__ import annotations

from typing import Any, List

from src.engineering_reports.engineering_report_summary import EngineeringReportSummary


class EngineeringReportReporting:
    """Single source of truth for engineering report validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        model["engineering_report_validation"] = validation
        model["engineering_report_summary"] = EngineeringReportSummary.build(
            model.get("beam_schedule_results", []),
            model.get("engineering_report_results", []),
            model.get("engineering_report_registry", {}),
            validation,
        )
        model["engineering_report_reporting"] = EngineeringReportReporting.build(
            model.get("engineering_report_results", []),
            model["engineering_report_summary"],
            validation,
        )

    @staticmethod
    def build(
        report_records: List[dict[str, Any]],
        summary: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        rows: List[dict[str, Any]] = []
        for report in sorted(report_records, key=lambda item: str(item.get("beam_id", ""))):
            sections = report.get("sections") or {}
            summary_section = sections.get("summary") or {}
            rows.append({
                "report_id": report.get("report_id"),
                "beam_id": report.get("beam_id"),
                "beam_mark": report.get("beam_mark"),
                "row_count": summary_section.get("row_count", 0),
                "total_weight_kg": summary_section.get("total_steel_weight_kg", 0.0),
                "total_cut_length_mm": summary_section.get("total_cut_length_mm", 0),
                "report_state": report.get("report_state"),
            })

        return {
            "phase": "Phase I.16",
            "status": validation.get("status", "SKIP"),
            "total_reports": summary.get("total_reports", 0),
            "total_rows": summary.get("total_rows", 0),
            "average_rows_per_report": summary.get("average_rows_per_report", 0.0),
            "report_rows": rows,
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
            "checks_passed": validation.get("summary", {}).get("passed", 0),
            "checks_failed": validation.get("summary", {}).get("failed", 0),
            "checks_total": validation.get("summary", {}).get("total_checks", 0),
        }
