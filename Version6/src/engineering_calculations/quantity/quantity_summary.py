"""Engineering quantity summary — Phase I.13."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.quantity.quantity_types import CREATED_PHASE, QuantityState


class QuantitySummary:
    """Build project-level quantity statistics."""

    @staticmethod
    def build(
        beams: List[dict[str, Any]],
        summary_records: List[dict[str, Any]],
        quantity_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        weights = [float(item.get("steel_weight_kg") or 0.0) for item in quantity_records]
        cut_lengths = [int(item.get("cut_length_mm") or 0) for item in quantity_records]
        bar_counts = [int(item.get("bar_count") or 0) for item in quantity_records]
        record_count = len(quantity_records)

        ready_quantities = sum(
            1 for item in quantity_records
            if item.get("quantity_state") == QuantityState.READY.value
        )
        deferred_quantities = sum(
            1 for item in quantity_records
            if item.get("quantity_state") == QuantityState.DEFERRED.value
        )
        blocked_quantities = sum(
            1 for item in quantity_records
            if item.get("quantity_state") == QuantityState.BLOCKED.value
        )
        empty_quantities = sum(
            1 for item in quantity_records
            if item.get("quantity_state") == QuantityState.EMPTY.value
        )
        unknown_quantities = sum(
            1 for item in quantity_records
            if item.get("quantity_state") == QuantityState.UNKNOWN.value
        )

        beam_quantity_report: list[dict[str, Any]] = []
        for record in quantity_records:
            beam_quantity_report.append({
                "beam_id": record.get("beam_id"),
                "beam_mark": record.get("beam_mark"),
                "quantity_state": record.get("quantity_state"),
                "steel_weight_kg": record.get("steel_weight_kg"),
                "cut_length_mm": record.get("cut_length_mm"),
                "bar_count": record.get("bar_count"),
                "engineering_ready": bool(record.get("engineering_ready")),
                "quality_ready": bool(record.get("quality_ready")),
            })

        return {
            "phase": "Phase I.13",
            "framework_phase": CREATED_PHASE,
            "total_beams": len(beams),
            "total_summaries": len(summary_records),
            "total_quantities": record_count,
            "ready_quantities": ready_quantities,
            "deferred_quantities": deferred_quantities,
            "blocked_quantities": blocked_quantities,
            "empty_quantities": empty_quantities,
            "unknown_quantities": unknown_quantities,
            "total_steel_weight_kg": round(sum(weights), 3),
            "total_cut_length_mm": sum(cut_lengths),
            "total_bars": sum(bar_counts),
            "average_steel_weight_kg": round(sum(weights) / record_count, 3) if record_count else 0.0,
            "average_cut_length_mm": round(sum(cut_lengths) / record_count, 3) if record_count else 0.0,
            "average_bars": round(sum(bar_counts) / record_count, 2) if record_count else 0.0,
            "beam_quantity_report": beam_quantity_report,
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
