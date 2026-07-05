"""Beam reinforcement schedule summary — Phase I.15."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.beam_schedule.beam_schedule_types import CREATED_PHASE


class BeamScheduleSummary:
    """Build project-level beam schedule statistics."""

    @staticmethod
    def build(
        beam_summary_records: List[dict[str, Any]],
        quantity_records: List[dict[str, Any]],
        material_records: List[dict[str, Any]],
        schedule_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        _ = (quantity_records, material_records)
        total_rows = sum(len(item.get("rows") or []) for item in schedule_records)
        rows_by_role: dict[str, int] = {}
        rows_by_diameter: dict[str, int] = {}
        rows_by_beam: dict[str, int] = {}
        beam_weights: List[float] = []
        beam_cut_lengths: List[int] = []
        beam_row_counts: List[int] = []

        for schedule in schedule_records:
            beam_id = str(schedule.get("beam_id", ""))
            rows_by_beam[beam_id] = len(schedule.get("rows") or [])
            beam_weights.append(float(schedule.get("total_steel_weight_kg") or 0.0))
            beam_cut_lengths.append(int(schedule.get("total_cut_length_mm") or 0))
            beam_row_counts.append(len(schedule.get("rows") or []))
            for row in schedule.get("rows") or []:
                role = str(row.get("role") or "")
                rows_by_role[role] = rows_by_role.get(role, 0) + 1
                diameter = str(row.get("diameter_mm", ""))
                rows_by_diameter[diameter] = rows_by_diameter.get(diameter, 0) + 1

        schedule_count = len(schedule_records)
        return {
            "phase": "Phase I.15",
            "framework_phase": CREATED_PHASE,
            "total_beam_summaries": len(beam_summary_records),
            "total_schedules": schedule_count,
            "total_rows": total_rows,
            "rows_by_role": dict(sorted(rows_by_role.items())),
            "rows_by_diameter": dict(sorted(rows_by_diameter.items(), key=lambda item: float(item[0] or 0))),
            "rows_by_beam": dict(sorted(rows_by_beam.items())),
            "average_rows_per_beam": round(total_rows / schedule_count, 2) if schedule_count else 0.0,
            "average_weight_per_beam_kg": round(sum(beam_weights) / schedule_count, 3) if schedule_count else 0.0,
            "average_cut_length_per_beam_mm": round(sum(beam_cut_lengths) / schedule_count, 2) if schedule_count else 0.0,
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
