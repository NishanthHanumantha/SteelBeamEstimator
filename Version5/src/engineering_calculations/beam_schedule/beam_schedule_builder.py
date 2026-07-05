"""Beam reinforcement schedule builder — Phase I.15."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.engineering_calculations.beam_schedule.beam_schedule_types import (
    CREATED_PHASE,
    DETERMINATION_METHOD,
    ROLE_OTHER,
    ScheduleState,
    role_description,
    role_display_order,
    row_sort_key,
)
from src.engineering_calculations.steel_weight.steel_weight_types import SteelWeightState


class BeamScheduleBuilder:
    """Aggregate existing engineering outputs into per-beam schedule records."""

    @staticmethod
    def build_schedules(
        beam_summary_records: List[dict[str, Any]],
        quantity_records: List[dict[str, Any]],
        material_records: List[dict[str, Any]],
        steel_weight_records: List[dict[str, Any]],
        bar_group_records: List[dict[str, Any]] | None = None,
    ) -> List[dict[str, Any]]:
        _ = material_records
        quantity_by_beam = BeamScheduleBuilder._index_quantities(quantity_records)
        group_by_id = BeamScheduleBuilder._index_bar_groups(bar_group_records or [])
        weights_by_beam = BeamScheduleBuilder._index_steel_weights(steel_weight_records)

        schedules: List[dict[str, Any]] = []
        for summary in sorted(
            beam_summary_records,
            key=lambda item: str(item.get("beam_id", "")),
        ):
            beam_id = str(summary.get("beam_id", ""))
            if not beam_id:
                continue
            quantity = quantity_by_beam.get(beam_id, {})
            rows = BeamScheduleBuilder._build_rows(
                beam_id,
                weights_by_beam.get(beam_id, []),
                group_by_id,
            )
            schedule_state = BeamScheduleBuilder._resolve_schedule_state(summary, quantity, rows)
            schedules.append(
                BeamScheduleBuilder._build_schedule_record(
                    summary,
                    quantity,
                    rows,
                    schedule_state,
                )
            )
        return schedules

    @staticmethod
    def _index_quantities(
        quantity_records: List[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        mapping: dict[str, dict[str, Any]] = {}
        for record in quantity_records:
            beam_id = str(record.get("beam_id", ""))
            if beam_id:
                mapping[beam_id] = record
        return mapping

    @staticmethod
    def _index_bar_groups(
        bar_group_records: List[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        mapping: dict[str, dict[str, Any]] = {}
        for record in bar_group_records:
            group_id = str(record.get("engineering_group_id") or record.get("bar_group_id") or "")
            if group_id:
                mapping[group_id] = record
        return mapping

    @staticmethod
    def _index_steel_weights(
        steel_weight_records: List[dict[str, Any]],
    ) -> dict[str, List[dict[str, Any]]]:
        mapping: dict[str, List[dict[str, Any]]] = {}
        for record in steel_weight_records:
            if record.get("status") != SteelWeightState.CALCULATED.value:
                continue
            beam_id = str(record.get("beam_id") or "")
            if not beam_id:
                continue
            mapping.setdefault(beam_id, []).append(record)
        for beam_id in mapping:
            mapping[beam_id] = sorted(
                mapping[beam_id],
                key=lambda item: str(item.get("bar_id", "")),
            )
        return mapping

    @staticmethod
    def _build_rows(
        beam_id: str,
        weight_records: List[dict[str, Any]],
        group_by_id: dict[str, dict[str, Any]],
    ) -> List[dict[str, Any]]:
        grouped: dict[Tuple[str, int | None, str], List[dict[str, Any]]] = {}
        for record in weight_records:
            role = str(record.get("role") or ROLE_OTHER).upper()
            diameter_value = record.get("diameter")
            diameter_mm = int(float(diameter_value)) if diameter_value is not None else None
            fabrication_mark = str(record.get("fabrication_mark") or "")
            key = (role, diameter_mm, fabrication_mark)
            grouped.setdefault(key, []).append(record)

        rows: List[dict[str, Any]] = []
        for key in sorted(grouped.keys(), key=lambda item: row_sort_key({
            "role": item[0],
            "diameter_mm": item[1],
            "fabrication_mark": item[2],
        })):
            role, diameter_mm, fabrication_mark = key
            members = grouped[key]
            representative = members[0]
            group_record = group_by_id.get(str(representative.get("engineering_group_id") or ""), {})
            cut_lengths = [
                int(float(item.get("cut_length_mm") or item.get("cut_length") or 0))
                for item in members
            ]
            weights = [float(item.get("weight_kg") or 0.0) for item in members]
            development_length = BeamScheduleBuilder._copy_development_length(
                representative,
                group_record,
            )
            spacing_mm = BeamScheduleBuilder._copy_spacing(representative, group_record)
            cut_length_mm = cut_lengths[0] if cut_lengths else 0
            rows.append({
                "row_id": None,
                "beam_id": beam_id,
                "role": role,
                "display_order": role_display_order(role),
                "description": role_description(role),
                "diameter_mm": diameter_mm,
                "spacing_mm": spacing_mm,
                "bar_count": len(members),
                "development_length_mm": development_length,
                "cut_length_mm": cut_length_mm,
                "total_length_mm": sum(cut_lengths),
                "steel_weight_kg": round(sum(weights), 3),
                "fabrication_mark": fabrication_mark or None,
                "shape_code": representative.get("shape_code"),
                "source_bar_ids": sorted(str(item.get("bar_id", "")) for item in members if item.get("bar_id")),
            })
        return rows

    @staticmethod
    def _copy_development_length(
        weight_record: dict[str, Any],
        group_record: dict[str, Any],
    ) -> int | None:
        for source in (group_record, weight_record):
            value = source.get("development_length_mm")
            if value is None:
                value = source.get("development_length")
            if value is not None:
                return int(float(value))
        return None

    @staticmethod
    def _copy_spacing(
        weight_record: dict[str, Any],
        group_record: dict[str, Any],
    ) -> int | None:
        for source in (group_record, weight_record):
            for key in ("spacing_mm", "spacing"):
                value = source.get(key)
                if value is not None:
                    return int(float(value))
        return None

    @staticmethod
    def _resolve_schedule_state(
        summary: dict[str, Any],
        quantity: dict[str, Any],
        rows: List[dict[str, Any]],
    ) -> str:
        if not rows:
            if int(summary.get("bar_count") or 0) == 0:
                return ScheduleState.EMPTY.value
            quantity_state = str(quantity.get("quantity_state") or quantity.get("status") or "")
            if quantity_state in {
                ScheduleState.DEFERRED.value,
                ScheduleState.BLOCKED.value,
                ScheduleState.UNKNOWN.value,
            }:
                return quantity_state
            return ScheduleState.DEFERRED.value
        quantity_state = str(quantity.get("quantity_state") or quantity.get("status") or "")
        if quantity_state == ScheduleState.READY.value:
            return ScheduleState.READY.value
        if quantity_state == ScheduleState.BLOCKED.value:
            return ScheduleState.BLOCKED.value
        if quantity_state == ScheduleState.DEFERRED.value:
            return ScheduleState.DEFERRED.value
        if quantity_state == ScheduleState.EMPTY.value:
            return ScheduleState.EMPTY.value
        if rows:
            return ScheduleState.DEFERRED.value
        return ScheduleState.UNKNOWN.value

    @staticmethod
    def _build_schedule_record(
        summary: dict[str, Any],
        quantity: dict[str, Any],
        rows: List[dict[str, Any]],
        schedule_state: str,
    ) -> dict[str, Any]:
        completion = dict(summary.get("completion") or quantity.get("completion") or {})
        quality = dict(summary.get("quality") or quantity.get("quality") or {})
        provenance = dict(
            summary.get("calculation_provenance")
            or summary.get("provenance")
            or quantity.get("calculation_provenance")
            or {}
        )
        engineering_ready = bool(
            quantity.get("engineering_ready")
            if quantity
            else completion.get("engineering_ready")
        )
        quality_ready = bool(
            quantity.get("quality_ready")
            if quantity
            else quality.get("quality_ready")
        )
        total_weight_kg = round(sum(float(row.get("steel_weight_kg") or 0.0) for row in rows), 3)
        total_cut_length_mm = sum(int(row.get("total_length_mm") or 0) for row in rows)
        total_bars = sum(int(row.get("bar_count") or 0) for row in rows)

        return {
            "beam_schedule_id": None,
            "beam_id": summary.get("beam_id"),
            "beam_mark": summary.get("beam_mark"),
            "beam_summary_id": summary.get("beam_summary_id"),
            "quantity_id": quantity.get("quantity_id"),
            "beam_section": dict(summary.get("beam_section") or {}),
            "clear_span_mm": summary.get("clear_span_mm"),
            "effective_span_mm": summary.get("effective_span_mm"),
            "engineering_state": summary.get("engineering_state"),
            "engineering_ready": engineering_ready,
            "quality_ready": quality_ready,
            "schedule_state": schedule_state,
            "completion": completion,
            "quality": quality,
            "calculation_provenance": provenance,
            "provenance": provenance,
            "trace": list(summary.get("trace") or quantity.get("trace") or []),
            "traceability": dict(summary.get("traceability") or quantity.get("traceability") or {}),
            "total_steel_weight_kg": total_weight_kg,
            "total_cut_length_mm": total_cut_length_mm,
            "total_bars": total_bars,
            "row_count": len(rows),
            "rows": rows,
            "schedule_metadata": {
                "determination_method": DETERMINATION_METHOD,
                "source_phase": CREATED_PHASE,
                "dependency_graph_consulted": True,
            },
            "status": schedule_state,
        }
