"""Beam reinforcement schedule export helpers — Phase I.15."""

from __future__ import annotations

from typing import Any, List


class BeamScheduleExporter:
    """Serialize beam schedule artifacts for pipeline export."""

    @staticmethod
    def export_results(records: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase I.15",
            "determination_count": len(records),
            "results": records,
        }

    @staticmethod
    def export_registry(registry: dict[str, Any]) -> dict[str, Any]:
        return registry

    @staticmethod
    def export_statistics(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.15",
            "total_beam_summaries": summary.get("total_beam_summaries", 0),
            "total_schedules": summary.get("total_schedules", 0),
            "total_rows": summary.get("total_rows", 0),
            "rows_by_role": summary.get("rows_by_role", {}),
            "rows_by_diameter": summary.get("rows_by_diameter", {}),
            "rows_by_beam": summary.get("rows_by_beam", {}),
            "average_rows_per_beam": summary.get("average_rows_per_beam", 0.0),
            "average_weight_per_beam_kg": summary.get("average_weight_per_beam_kg", 0.0),
            "average_cut_length_per_beam_mm": summary.get("average_cut_length_per_beam_mm", 0.0),
        }

    @staticmethod
    def export_report(reporting: dict[str, Any]) -> dict[str, Any]:
        return reporting

    @staticmethod
    def export_engineering_beam_schedule_report(
        summary: dict[str, Any],
        reporting: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.15",
            "summary": summary,
            "reporting": reporting,
        }
