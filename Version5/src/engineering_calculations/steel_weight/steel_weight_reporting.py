"""Steel weight reporting — Phase I.11."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.steel_weight.steel_weight_summary import SteelWeightSummary


class SteelWeightReporting:
    """Single source of truth for steel weight validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        weight_records = model.get("steel_weight_results", [])
        registry = model.get("steel_weight_registry", {})
        model["steel_weight_validation"] = validation
        model["steel_weight_summary"] = SteelWeightSummary.build(
            bars,
            weight_records,
            registry,
            validation,
        )
        model["steel_weight_reporting"] = SteelWeightReporting.build(
            model["steel_weight_summary"],
            validation,
        )

    @staticmethod
    def build(summary: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.11",
            "status": validation.get("status", "SKIP"),
            "bar_count": summary.get("bar_count", 0),
            "calculated": summary.get("calculated", 0),
            "deferred": summary.get("deferred", 0),
            "blocked": summary.get("blocked", 0),
            "failed": summary.get("failed", 0),
            "total_steel_weight_kg": summary.get("total_steel_weight_kg", 0.0),
            "average_bar_weight_kg": summary.get("average_bar_weight_kg", 0.0),
            "weight_by_beam": summary.get("weight_by_beam", {}),
            "weight_by_diameter": summary.get("weight_by_diameter", {}),
            "weight_by_role": summary.get("weight_by_role", {}),
            "weight_by_shape": summary.get("weight_by_shape", {}),
            "weight_by_fabrication_state": summary.get("weight_by_fabrication_state", {}),
            "weight_by_fabrication_mark": summary.get("weight_by_fabrication_mark", {}),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
            "checks_passed": validation.get("summary", {}).get("passed", 0),
            "checks_failed": validation.get("summary", {}).get("failed", 0),
            "checks_total": validation.get("summary", {}).get("total_checks", 0),
        }
