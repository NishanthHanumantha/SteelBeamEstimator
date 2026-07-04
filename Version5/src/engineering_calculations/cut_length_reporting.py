"""Cut length reporting — Phase I.6."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.cut_length_summary import CutLengthSummary


class CutLengthReporting:
    """Single source of truth for cut length validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        cut_records = model.get("cut_length_results", [])
        registry = model.get("cut_length_registry", {})
        model["cut_length_validation"] = validation
        model["cut_length_summary"] = CutLengthSummary.build(
            bars,
            cut_records,
            registry,
            validation,
        )
        model["cut_length_reporting"] = CutLengthReporting.build(
            model["cut_length_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.6",
            "determination_count": summary.get("determination_count", 0),
            "results_calculated": summary.get("results_calculated", 0),
            "deferred_results": summary.get("deferred_results", 0),
            "blocked_results": summary.get("blocked_results", 0),
            "failed_results": summary.get("failed_results", 0),
            "cut_length_distribution": summary.get("cut_length_distribution", {}),
            "role_distribution": summary.get("role_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "beam_distribution": summary.get("beam_distribution", {}),
            "bar_type_distribution": summary.get("bar_type_distribution", {}),
            "rule_source_distribution": summary.get("rule_source_distribution", {}),
            "average_cut_length_mm": summary.get("average_cut_length_mm", 0.0),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
