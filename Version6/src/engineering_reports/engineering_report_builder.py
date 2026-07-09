"""Engineering report model builder — Phase I.16."""

from __future__ import annotations

from typing import Any, List

from src.engineering_reports.engineering_report_types import (
    CREATED_PHASE,
    DETERMINATION_METHOD,
    MODEL_VERSION,
    REPORT_TYPE_BEAM_REINFORCEMENT_SCHEDULE,
)


class EngineeringReportBuilder:
    """Copy BeamSchedule records into presentation-neutral report models."""

    @staticmethod
    def build_reports(
        beam_schedule_records: List[dict[str, Any]],
        quantity_records: List[dict[str, Any]] | None = None,
        project_workspace: dict[str, Any] | None = None,
        drawing_models: List[dict[str, Any]] | None = None,
        generation_timestamp: str = "",
    ) -> List[dict[str, Any]]:
        quantity_by_beam = EngineeringReportBuilder._index_by_beam(quantity_records or [])
        workspace = project_workspace or {}
        drawing = drawing_models[0] if drawing_models else {}

        reports: List[dict[str, Any]] = []
        for schedule in sorted(
            beam_schedule_records,
            key=lambda item: str(item.get("beam_id", "")),
        ):
            beam_id = str(schedule.get("beam_id", ""))
            if not beam_id:
                continue
            quantity = quantity_by_beam.get(beam_id, {})
            reports.append(
                EngineeringReportBuilder._build_report(
                    schedule,
                    quantity,
                    workspace,
                    drawing,
                    generation_timestamp,
                )
            )
        return reports

    @staticmethod
    def _index_by_beam(records: List[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        mapping: dict[str, dict[str, Any]] = {}
        for record in records:
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                mapping[beam_id] = record
        return mapping

    @staticmethod
    def _build_report(
        schedule: dict[str, Any],
        quantity: dict[str, Any],
        workspace: dict[str, Any],
        drawing: dict[str, Any],
        generation_timestamp: str,
    ) -> dict[str, Any]:
        schedule_state = schedule.get("schedule_state") or schedule.get("status")
        rows = [EngineeringReportBuilder._copy_schedule_row(row) for row in (schedule.get("rows") or [])]

        steel_grade = quantity.get("steel_grade")
        concrete_grade = workspace.get("concrete_grade")
        drawing_number = drawing.get("drawing_number")

        return {
            "report_id": None,
            "beam_schedule_id": schedule.get("beam_schedule_id"),
            "beam_id": schedule.get("beam_id"),
            "beam_mark": schedule.get("beam_mark"),
            "report_state": schedule_state,
            "engineering_ready": schedule.get("engineering_ready"),
            "quality_ready": schedule.get("quality_ready"),
            "completion": dict(schedule.get("completion") or {}),
            "quality": dict(schedule.get("quality") or {}),
            "calculation_provenance": dict(
                schedule.get("calculation_provenance") or schedule.get("provenance") or {}
            ),
            "provenance": dict(schedule.get("provenance") or schedule.get("calculation_provenance") or {}),
            "trace": list(schedule.get("trace") or []),
            "traceability": dict(schedule.get("traceability") or {}),
            "report_metadata": {
                "determination_method": DETERMINATION_METHOD,
                "source_phase": CREATED_PHASE,
                "report_type": REPORT_TYPE_BEAM_REINFORCEMENT_SCHEDULE,
                "dependency_graph_consulted": True,
            },
            "sections": {
                "header": {
                    "beam_mark": schedule.get("beam_mark"),
                    "beam_section": dict(schedule.get("beam_section") or {}),
                    "clear_span_mm": schedule.get("clear_span_mm"),
                    "effective_span_mm": schedule.get("effective_span_mm"),
                    "engineering_state": schedule.get("engineering_state"),
                },
                "project_information": {
                    "steel_grade": steel_grade,
                    "concrete_grade": concrete_grade,
                    "drawing_number": drawing_number,
                    "model_version": MODEL_VERSION,
                    "phase": CREATED_PHASE,
                },
                "schedule_table": rows,
                "summary": {
                    "row_count": schedule.get("row_count", len(rows)),
                    "total_bars": schedule.get("total_bars"),
                    "total_cut_length_mm": schedule.get("total_cut_length_mm"),
                    "total_steel_weight_kg": schedule.get("total_steel_weight_kg"),
                },
                "validation": {
                    "engineering_ready": schedule.get("engineering_ready"),
                    "quality_ready": schedule.get("quality_ready"),
                    "schedule_state": schedule_state,
                    "completion": dict(schedule.get("completion") or {}),
                    "quality": dict(schedule.get("quality") or {}),
                },
                "footer": {
                    "generation_phase": CREATED_PHASE,
                    "model_version": MODEL_VERSION,
                    "generation_timestamp": generation_timestamp or None,
                    "determination_method": DETERMINATION_METHOD,
                },
            },
            "status": schedule_state,
        }

    @staticmethod
    def _copy_schedule_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "row_id": row.get("row_id"),
            "role": row.get("role"),
            "display_order": row.get("display_order"),
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
            "source_bar_ids": list(row.get("source_bar_ids") or []),
        }
