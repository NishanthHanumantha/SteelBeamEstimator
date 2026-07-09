"""Beam reinforcement schedule reporting — Phase I.15."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.beam_schedule.beam_schedule_summary import BeamScheduleSummary


class BeamScheduleReporting:
    """Single source of truth for beam schedule validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        model["beam_schedule_validation"] = validation
        model["beam_schedule_summary"] = BeamScheduleSummary.build(
            model.get("beam_summary_results", []),
            model.get("quantity_results", []),
            model.get("material_results", []),
            model.get("beam_schedule_results", []),
            model.get("beam_schedule_registry", {}),
            validation,
        )
        model["beam_schedule_reporting"] = BeamScheduleReporting.build(
            model.get("beam_schedule_results", []),
            model["beam_schedule_summary"],
            validation,
        )

    @staticmethod
    def build(
        schedule_records: List[dict[str, Any]],
        summary: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        per_beam_rows: List[dict[str, Any]] = []
        for schedule in sorted(schedule_records, key=lambda item: str(item.get("beam_id", ""))):
            beam_header = {
                "beam_id": schedule.get("beam_id"),
                "beam_mark": schedule.get("beam_mark"),
                "beam_section": schedule.get("beam_section"),
                "clear_span_mm": schedule.get("clear_span_mm"),
                "effective_span_mm": schedule.get("effective_span_mm"),
            }
            for row in schedule.get("rows") or []:
                per_beam_rows.append({
                    **beam_header,
                    "role": row.get("role"),
                    "description": row.get("description"),
                    "diameter_mm": row.get("diameter_mm"),
                    "spacing_mm": row.get("spacing_mm"),
                    "bar_count": row.get("bar_count"),
                    "development_length_mm": row.get("development_length_mm"),
                    "cut_length_mm": row.get("cut_length_mm"),
                    "total_length_mm": row.get("total_length_mm"),
                    "steel_weight_kg": row.get("steel_weight_kg"),
                    "fabrication_mark": row.get("fabrication_mark"),
                    "shape_code": row.get("shape_code"),
                })

        return {
            "phase": "Phase I.15",
            "status": validation.get("status", "SKIP"),
            "total_schedules": summary.get("total_schedules", 0),
            "total_rows": summary.get("total_rows", 0),
            "rows_by_role": summary.get("rows_by_role", {}),
            "rows_by_diameter": summary.get("rows_by_diameter", {}),
            "rows_by_beam": summary.get("rows_by_beam", {}),
            "average_rows_per_beam": summary.get("average_rows_per_beam", 0.0),
            "average_weight_per_beam_kg": summary.get("average_weight_per_beam_kg", 0.0),
            "average_cut_length_per_beam_mm": summary.get("average_cut_length_per_beam_mm", 0.0),
            "per_beam_schedule_rows": per_beam_rows,
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
            "checks_passed": validation.get("summary", {}).get("passed", 0),
            "checks_failed": validation.get("summary", {}).get("failed", 0),
            "checks_total": validation.get("summary", {}).get("total_checks", 0),
        }
