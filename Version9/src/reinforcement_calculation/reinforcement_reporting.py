"""Reinforcement calculation reporting — Phase I.2."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement_calculation.reinforcement_exporter import ReinforcementExporter
from src.reinforcement_calculation.reinforcement_readiness_summary import (
    ReinforcementReadinessSummary,
)
from src.reinforcement_calculation.reinforcement_summary import ReinforcementSummary


class ReinforcementReporting:
    """Single source of truth for reinforcement validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        groups = model.get("reinforcement_groups", [])
        registry = model.get("reinforcement_registry", {})
        model["reinforcement_validation"] = validation
        model["reinforcement_summary"] = ReinforcementSummary.build(
            model.get("engineering_specifications", []),
            bars,
            groups,
            registry,
            validation,
        )
        model["reinforcement_reporting"] = ReinforcementReporting.build(
            bars,
            groups,
            model["reinforcement_summary"],
        )

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase I.2",
            "bar_count": len(bars),
            "group_count": len(groups),
            "role_distribution": summary.get("role_distribution", {}),
            "diameter_distribution": summary.get("diameter_distribution", {}),
            "steel_grade_distribution": summary.get("steel_grade_distribution", {}),
            "coverage": summary.get("coverage", {}),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }


class ReinforcementReadinessReporting:
    """Reporting for calculation readiness evaluation."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        bars = model.get("reinforcement_bars", [])
        groups = model.get("reinforcement_groups", [])
        registry = model.get("reinforcement_registry", {})

        model["reinforcement_readiness"] = ReinforcementExporter.export_readiness(bars, groups)
        model["reinforcement_readiness_validation"] = validation
        model["reinforcement_readiness_summary"] = ReinforcementReadinessSummary.build(
            bars,
            groups,
            registry,
            validation,
        )
        model["reinforcement_readiness_reporting"] = ReinforcementReadinessReporting.build(
            model["reinforcement_readiness_summary"]
        )

    @staticmethod
    def build(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Phase I.2.1",
            "ready_count": summary.get("ready_count", 0),
            "deferred_count": summary.get("deferred_count", 0),
            "blocked_count": summary.get("blocked_count", 0),
            "defer_reasons": summary.get("defer_reasons", {}),
            "readiness_coverage": summary.get("readiness_coverage", {}),
            "validation_summary": summary.get("validation_summary", {}),
            "registry_statistics": summary.get("registry_statistics", {}),
        }
