"""Engineering quantity reporting — Phase I.13."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.quantity.quantity_summary import QuantitySummary


class QuantityReporting:
    """Single source of truth for quantity validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        beams = model.get("beams", [])
        summary_records = model.get("beam_summary_results", [])
        quantity_records = model.get("quantity_results", [])
        registry = model.get("quantity_registry", {})
        model["quantity_validation"] = validation
        model["quantity_summary"] = QuantitySummary.build(
            beams,
            summary_records,
            quantity_records,
            registry,
            validation,
        )
        model["quantity_reporting"] = QuantityReporting.build(
            model["quantity_summary"],
            validation,
        )

    @staticmethod
    def build(summary: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.13",
            "status": validation.get("status", "SKIP"),
            "total_beams": summary.get("total_beams", 0),
            "total_summaries": summary.get("total_summaries", 0),
            "total_quantities": summary.get("total_quantities", 0),
            "ready_quantities": summary.get("ready_quantities", 0),
            "deferred_quantities": summary.get("deferred_quantities", 0),
            "blocked_quantities": summary.get("blocked_quantities", 0),
            "empty_quantities": summary.get("empty_quantities", 0),
            "unknown_quantities": summary.get("unknown_quantities", 0),
            "total_steel_weight_kg": summary.get("total_steel_weight_kg", 0.0),
            "total_cut_length_mm": summary.get("total_cut_length_mm", 0),
            "total_bars": summary.get("total_bars", 0),
            "average_steel_weight_kg": summary.get("average_steel_weight_kg", 0.0),
            "average_cut_length_mm": summary.get("average_cut_length_mm", 0.0),
            "average_bars": summary.get("average_bars", 0.0),
            "beam_quantity_report": summary.get("beam_quantity_report", []),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
            "checks_passed": validation.get("summary", {}).get("passed", 0),
            "checks_failed": validation.get("summary", {}).get("failed", 0),
            "checks_total": validation.get("summary", {}).get("total_checks", 0),
        }
