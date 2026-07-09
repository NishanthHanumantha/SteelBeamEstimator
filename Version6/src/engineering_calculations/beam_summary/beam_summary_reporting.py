"""Beam summary reporting — Phase I.12."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.beam_summary.beam_summary_summary import BeamSummarySummary


class BeamSummaryReporting:
    """Single source of truth for beam summary validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        beams = model.get("beams", [])
        summary_records = model.get("beam_summary_results", [])
        registry = model.get("beam_summary_registry", {})
        model["beam_summary_validation"] = validation
        model["beam_summary_summary"] = BeamSummarySummary.build(
            beams,
            summary_records,
            registry,
            validation,
        )
        model["beam_summary_reporting"] = BeamSummaryReporting.build(
            model["beam_summary_summary"],
            validation,
        )

    @staticmethod
    def build(summary: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.12.2",
            "status": validation.get("status", "SKIP"),
            "total_beams": summary.get("total_beams", 0),
            "total_summaries": summary.get("total_summaries", 0),
            "total_bars": summary.get("total_bars", 0),
            "average_bars_per_beam": summary.get("average_bars_per_beam", 0.0),
            "average_steel_weight_kg": summary.get("average_steel_weight_kg", 0.0),
            "total_steel_weight_kg": summary.get("total_steel_weight_kg", 0.0),
            "largest_beam": summary.get("largest_beam"),
            "smallest_beam": summary.get("smallest_beam"),
            "beam_with_largest_steel_weight": summary.get("beam_with_largest_steel_weight"),
            "beam_with_longest_reinforcement": summary.get("beam_with_longest_reinforcement"),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "shape_distribution": summary.get("shape_distribution", {}),
            "role_distribution": summary.get("role_distribution", {}),
            "fabrication_state_distribution": summary.get("fabrication_state_distribution", {}),
            "engineering_state_distribution": summary.get("engineering_state_distribution", {}),
            "engineering_ready_beams": summary.get("engineering_ready_beams", 0),
            "partial_beams": summary.get("partial_beams", 0),
            "blocked_beams": summary.get("blocked_beams", 0),
            "empty_beams": summary.get("empty_beams", 0),
            "average_completion_percent": summary.get("average_completion_percent", 0.0),
            "beam_completion_report": summary.get("beam_completion_report", []),
            "average_confidence_score": summary.get("average_confidence_score", 0.0),
            "quality_grade_distribution": summary.get("quality_grade_distribution", {}),
            "quality_ready_beams": summary.get("quality_ready_beams", 0),
            "highest_confidence_beam": summary.get("highest_confidence_beam"),
            "lowest_confidence_beam": summary.get("lowest_confidence_beam"),
            "beam_quality_report": summary.get("beam_quality_report", []),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
            "checks_passed": validation.get("summary", {}).get("passed", 0),
            "checks_failed": validation.get("summary", {}).get("failed", 0),
            "checks_total": validation.get("summary", {}).get("total_checks", 0),
        }
