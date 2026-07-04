"""Lap length summary — Phase I.5."""

from __future__ import annotations

from collections import Counter
from typing import Any, List

from src.engineering_calculations.lap_length_types import CREATED_PHASE, LapLengthState


class LapLengthSummary:
    """Build project-level lap length determination summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        lap_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated = [
            item for item in lap_records
            if item.get("determination_state") == LapLengthState.CALCULATED.value
        ]
        lap_values = [
            float(item["lap_length_mm"])
            for item in calculated
            if item.get("lap_length_mm") is not None
        ]

        diameter_dist = Counter(
            str(item.get("bar_diameter_mm"))
            for item in calculated
            if item.get("bar_diameter_mm") is not None
        )
        factor_dist = Counter(
            str(item.get("lap_factor"))
            for item in calculated
            if item.get("lap_factor") is not None
        )
        steel_dist = Counter(
            str(item.get("steel_grade"))
            for item in calculated
            if item.get("steel_grade")
        )
        concrete_dist = Counter(
            str(item.get("concrete_grade"))
            for item in calculated
            if item.get("concrete_grade")
        )
        source_dist = Counter(
            str(item.get("lap_rule_source"))
            for item in calculated
            if item.get("lap_rule_source")
        )
        lap_distribution = Counter(str(int(value)) for value in lap_values)

        return {
            "phase": "Phase I.5",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "determination_count": len(lap_records),
            "results_calculated": len(calculated),
            "deferred_results": sum(
                1
                for item in lap_records
                if item.get("determination_state") == LapLengthState.DEFERRED.value
            ),
            "blocked_results": sum(
                1
                for item in lap_records
                if item.get("determination_state") == LapLengthState.BLOCKED.value
            ),
            "failed_results": sum(
                1
                for item in lap_records
                if item.get("determination_state") == LapLengthState.FAILED.value
            ),
            "lap_length_distribution": dict(sorted(lap_distribution.items(), key=lambda kv: int(kv[0]))),
            "diameter_distribution": dict(sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))),
            "lap_factor_distribution": dict(sorted(factor_dist.items(), key=lambda kv: float(kv[0]))),
            "steel_grade_distribution": dict(steel_dist),
            "concrete_grade_distribution": dict(concrete_dist),
            "rule_source_distribution": dict(source_dist),
            "average_lap_length_mm": round(sum(lap_values) / len(lap_values), 2) if lap_values else 0.0,
            "min_lap_length_mm": min(lap_values) if lap_values else None,
            "max_lap_length_mm": max(lap_values) if lap_values else None,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_diameter": registry.get("results_by_diameter", {}),
                "results_by_lap_factor": registry.get("results_by_lap_factor", {}),
                "results_by_rule_source": registry.get("results_by_rule_source", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
            "metadata_enabled": True,
        }
