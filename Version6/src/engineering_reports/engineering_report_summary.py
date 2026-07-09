"""Engineering report summary — Phase I.16."""

from __future__ import annotations

from typing import Any, List

from src.engineering_reports.engineering_report_types import CREATED_PHASE


class EngineeringReportSummary:
    """Build project-level engineering report statistics."""

    @staticmethod
    def build(
        beam_schedule_records: List[dict[str, Any]],
        report_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        _ = beam_schedule_records
        total_rows = sum(
            len((item.get("sections") or {}).get("schedule_table") or [])
            for item in report_records
        )
        report_count = len(report_records)
        return {
            "phase": "Phase I.16",
            "framework_phase": CREATED_PHASE,
            "total_schedules": len(beam_schedule_records),
            "total_reports": report_count,
            "total_rows": total_rows,
            "average_rows_per_report": round(total_rows / report_count, 2) if report_count else 0.0,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
