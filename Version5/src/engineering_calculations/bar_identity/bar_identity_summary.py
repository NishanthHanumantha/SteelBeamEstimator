"""Bar identity summary — Phase I.8."""

from __future__ import annotations

from collections import Counter
from typing import Any, List

from src.engineering_calculations.bar_identity.bar_identity_types import (
    CREATED_PHASE,
    BarIdentityState,
)


class BarIdentitySummary:
    """Build project-level bar identity determination summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        identity_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated = [
            item for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
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
        shape_dist = Counter(
            str(item.get("shape_code"))
            for item in calculated
            if item.get("shape_code")
        )
        source_dist = Counter(
            str(item.get("identity_rule_source"))
            for item in calculated
            if item.get("identity_rule_source")
        )
        group_ids = {
            str(item.get("engineering_group_id"))
            for item in calculated
            if item.get("engineering_group_id")
        }
        engineering_ids = {
            str(item.get("engineering_bar_id"))
            for item in calculated
            if item.get("engineering_bar_id")
        }
        duplicate_bars = sum(
            1 for item in calculated if item.get("is_duplicate")
        )
        grouped_bars = sum(
            1
            for item in calculated
            if int(item.get("group_member_count") or 0) > 1
        )

        return {
            "phase": "Phase I.8",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "determination_count": len(identity_records),
            "results_calculated": len(calculated),
            "deferred_results": sum(
                1
                for item in identity_records
                if item.get("determination_state") == BarIdentityState.DEFERRED.value
            ),
            "blocked_results": sum(
                1
                for item in identity_records
                if item.get("determination_state") == BarIdentityState.BLOCKED.value
            ),
            "failed_results": sum(
                1
                for item in identity_records
                if item.get("determination_state") == BarIdentityState.FAILED.value
            ),
            "grouped_bars": grouped_bars,
            "unique_groups": len(group_ids),
            "unique_engineering_identities": len(engineering_ids),
            "duplicate_bars": duplicate_bars,
            "role_distribution": dict(role_dist),
            "diameter_distribution": dict(sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))),
            "beam_distribution": dict(beam_dist),
            "shape_code_distribution": dict(shape_dist),
            "rule_source_distribution": dict(source_dist),
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_group": registry.get("results_by_group", {}),
                "results_by_shape_code": registry.get("results_by_shape_code", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
            "metadata_enabled": True,
        }
