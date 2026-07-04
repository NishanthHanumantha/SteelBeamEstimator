"""BBS reporting — Phase I.10."""

from __future__ import annotations

from typing import Any

from src.engineering_calculations.bbs.bbs_summary import BbsSummary


class BbsReporting:
    """Single source of truth for BBS validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        group_records = model.get("bar_group_results", [])
        bbs_records = model.get("bbs_results", [])
        registry = model.get("bbs_registry", {})
        model["bbs_validation"] = validation
        model["bbs_summary"] = BbsSummary.build(
            bars,
            group_records,
            bbs_records,
            registry,
            validation,
        )
        model["bbs_reporting"] = BbsReporting.build(
            model["bbs_summary"],
            validation,
        )

    @staticmethod
    def build(summary: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.10",
            "status": validation.get("status", "SKIP"),
            "bar_count": summary.get("bar_count", 0),
            "calculated_groups": summary.get("calculated_groups", 0),
            "bbs_records": summary.get("bbs_records", 0),
            "deferred_results": summary.get("deferred_results", 0),
            "blocked_results": summary.get("blocked_results", 0),
            "failed_results": summary.get("failed_results", 0),
            "duplicate_groups": summary.get("duplicate_groups", 0),
            "largest_schedule": summary.get("largest_schedule", 0),
            "average_members_per_schedule": summary.get("average_members_per_schedule", 0),
            "unique_fabrication_marks": summary.get("unique_fabrication_marks", 0),
            "unique_engineering_signatures": summary.get("unique_engineering_signatures", 0),
            "role_distribution": summary.get("role_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "beam_distribution": summary.get("beam_distribution", {}),
            "shape_distribution": summary.get("shape_distribution", {}),
            "fabrication_state_distribution": summary.get("fabrication_state_distribution", {}),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
            "checks_passed": validation.get("summary", {}).get("passed", 0),
            "checks_failed": validation.get("summary", {}).get("failed", 0),
            "checks_total": validation.get("summary", {}).get("total_checks", 0),
        }
