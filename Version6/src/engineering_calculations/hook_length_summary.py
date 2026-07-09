"""Hook length summary — Phase I.4."""

from __future__ import annotations

from collections import Counter
from typing import Any, List

from src.engineering_calculations.hook_length_types import CREATED_PHASE, HookLengthState


class HookLengthSummary:
    """Build project-level hook length determination summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        hook_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated = [
            item for item in hook_records
            if item.get("determination_state") == HookLengthState.CALCULATED.value
        ]
        hook_values = [
            float(item["hook_length_mm"])
            for item in calculated
            if item.get("hook_length_mm") is not None
        ]

        angle_dist = Counter(
            str(item.get("hook_angle"))
            for item in calculated
            if item.get("hook_angle") is not None
        )
        diameter_dist = Counter(
            str(item.get("bar_diameter_mm"))
            for item in calculated
            if item.get("bar_diameter_mm") is not None
        )
        multiplier_dist = Counter(
            str(item.get("hook_multiplier"))
            for item in calculated
            if item.get("hook_multiplier") is not None
        )
        source_dist = Counter(
            str(item.get("hook_rule_source"))
            for item in calculated
            if item.get("hook_rule_source")
        )
        hook_distribution = Counter(str(int(value)) for value in hook_values)

        return {
            "phase": "Phase I.4",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "determination_count": len(hook_records),
            "results_calculated": len(calculated),
            "deferred_results": sum(
                1
                for item in hook_records
                if item.get("determination_state") == HookLengthState.DEFERRED.value
            ),
            "blocked_results": sum(
                1
                for item in hook_records
                if item.get("determination_state") == HookLengthState.BLOCKED.value
            ),
            "failed_results": sum(
                1
                for item in hook_records
                if item.get("determination_state") == HookLengthState.FAILED.value
            ),
            "hook_length_distribution": dict(sorted(hook_distribution.items(), key=lambda kv: int(kv[0]))),
            "hook_angle_distribution": dict(sorted(angle_dist.items(), key=lambda kv: int(kv[0]))),
            "diameter_distribution": dict(sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))),
            "multiplier_distribution": dict(sorted(multiplier_dist.items(), key=lambda kv: int(kv[0]))),
            "rule_source_distribution": dict(source_dist),
            "average_hook_length_mm": round(sum(hook_values) / len(hook_values), 2) if hook_values else 0.0,
            "min_hook_length_mm": min(hook_values) if hook_values else None,
            "max_hook_length_mm": max(hook_values) if hook_values else None,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_hook_angle": registry.get("results_by_hook_angle", {}),
                "results_by_hook_type": registry.get("results_by_hook_type", {}),
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
