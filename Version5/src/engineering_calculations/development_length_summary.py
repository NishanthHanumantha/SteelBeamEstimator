"""Development length summary — Phase I.3."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from src.engineering_calculations.development_length_types import (
    CREATED_PHASE,
    DevelopmentLengthState,
)


class DevelopmentLengthSummary:
    """Build project-level development length determination summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        dev_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated = [
            item for item in dev_records
            if item.get("determination_state") == DevelopmentLengthState.CALCULATED.value
        ]
        deferred = [
            item for item in dev_records
            if item.get("determination_state") == DevelopmentLengthState.DEFERRED.value
        ]
        ld_values = [
            float(item["development_length_mm"])
            for item in calculated
            if item.get("development_length_mm") is not None
        ]

        diameter_dist = Counter(
            str(item.get("bar_diameter_mm"))
            for item in calculated
            if item.get("bar_diameter_mm") is not None
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
        table_dist = Counter(
            str(item.get("development_length_table"))
            for item in calculated
            if item.get("development_length_table")
        )
        ld_distribution = Counter(str(int(value)) for value in ld_values)

        return {
            "phase": "Phase I.3",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "determination_count": len(dev_records),
            "results_calculated": len(calculated),
            "deferred_results": len(deferred),
            "blocked_results": sum(
                1
                for item in dev_records
                if item.get("determination_state") == DevelopmentLengthState.BLOCKED.value
            ),
            "failed_results": sum(
                1
                for item in dev_records
                if item.get("determination_state") == DevelopmentLengthState.FAILED.value
            ),
            "development_length_distribution": dict(sorted(ld_distribution.items(), key=lambda kv: int(kv[0]))),
            "diameter_distribution": dict(sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))),
            "steel_grade_distribution": dict(steel_dist),
            "concrete_grade_distribution": dict(concrete_dist),
            "lookup_table_usage": dict(table_dist),
            "average_development_length_mm": round(sum(ld_values) / len(ld_values), 2) if ld_values else 0.0,
            "min_development_length_mm": min(ld_values) if ld_values else None,
            "max_development_length_mm": max(ld_values) if ld_values else None,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_steel_grade": registry.get("results_by_steel_grade", {}),
                "results_by_concrete_grade": registry.get("results_by_concrete_grade", {}),
                "results_by_table": registry.get("results_by_table", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
            "metadata_enabled": True,
        }
