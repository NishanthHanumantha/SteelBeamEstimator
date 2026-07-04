"""Cut length summary — Phase I.6."""

from __future__ import annotations

from collections import Counter
from typing import Any, List

from src.engineering_calculations.cut_length_types import CREATED_PHASE, CutLengthState


class CutLengthSummary:
    """Build project-level cut length determination summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        cut_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated = [
            item for item in cut_records
            if item.get("determination_state") == CutLengthState.CALCULATED.value
        ]
        cut_values = [
            float(item["cut_length_mm"])
            for item in calculated
            if item.get("cut_length_mm") is not None
        ]

        role_dist = Counter(
            str(item.get("reinforcement_role"))
            for item in calculated
            if item.get("reinforcement_role")
        )
        diameter_dist = Counter(
            str(item.get("bar_diameter_mm"))
            for item in calculated
            if item.get("bar_diameter_mm") is not None
        )
        beam_dist = Counter(
            str(item.get("beam_id"))
            for item in calculated
            if item.get("beam_id")
        )
        bar_type_dist = Counter(
            str(item.get("bar_type"))
            for item in calculated
            if item.get("bar_type")
        )
        source_dist = Counter(
            str(item.get("cut_rule_source"))
            for item in calculated
            if item.get("cut_rule_source")
        )
        cut_distribution = Counter(str(int(value)) for value in cut_values)

        return {
            "phase": "Phase I.6",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "determination_count": len(cut_records),
            "results_calculated": len(calculated),
            "deferred_results": sum(
                1
                for item in cut_records
                if item.get("determination_state") == CutLengthState.DEFERRED.value
            ),
            "blocked_results": sum(
                1
                for item in cut_records
                if item.get("determination_state") == CutLengthState.BLOCKED.value
            ),
            "failed_results": sum(
                1
                for item in cut_records
                if item.get("determination_state") == CutLengthState.FAILED.value
            ),
            "cut_length_distribution": dict(sorted(cut_distribution.items(), key=lambda kv: int(kv[0]))),
            "role_distribution": dict(role_dist),
            "diameter_distribution": dict(sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))),
            "beam_distribution": dict(beam_dist),
            "bar_type_distribution": dict(bar_type_dist),
            "rule_source_distribution": dict(source_dist),
            "average_cut_length_mm": round(sum(cut_values) / len(cut_values), 2) if cut_values else 0.0,
            "min_cut_length_mm": min(cut_values) if cut_values else None,
            "max_cut_length_mm": max(cut_values) if cut_values else None,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_role": registry.get("results_by_role", {}),
                "results_by_diameter": registry.get("results_by_diameter", {}),
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
