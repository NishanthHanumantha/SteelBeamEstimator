"""Bar group summary — Phase I.9."""

from __future__ import annotations

from collections import Counter
from typing import Any, List

from src.engineering_calculations.bar_group.bar_group_types import CREATED_PHASE, BarGroupState


class BarGroupSummary:
    """Build project-level bar group aggregation summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        identity_records: List[dict[str, Any]],
        group_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated_groups = [
            item
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        calculated_identities = [
            item
            for item in identity_records
            if item.get("determination_state") == "CALCULATED"
        ]
        member_counts = [
            int(item.get("member_count") or 0)
            for item in calculated_groups
            if int(item.get("member_count") or 0) > 0
        ]
        signatures = {
            str(item.get("engineering_signature"))
            for item in calculated_groups
            if item.get("engineering_signature")
        }
        duplicate_groups = sum(
            1 for item in calculated_groups if item.get("is_duplicate_group")
        )

        role_dist = Counter(
            role
            for item in calculated_groups
            for role in (item.get("member_roles") or [])
        )
        diameter_dist = Counter(
            str(item.get("diameter"))
            for item in calculated_groups
            if item.get("diameter") is not None
        )
        beam_dist = Counter(
            beam
            for item in calculated_groups
            for beam in (item.get("member_beams") or [])
        )
        shape_dist = Counter(
            str(item.get("shape_code"))
            for item in calculated_groups
            if item.get("shape_code")
        )
        cut_length_dist = Counter(
            str(item.get("cut_length"))
            for item in calculated_groups
            if item.get("cut_length") is not None
        )
        source_dist = Counter(
            str(item.get("rule_source"))
            for item in calculated_groups
            if item.get("rule_source")
        )

        return {
            "phase": "Phase I.9",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "calculated_identities": len(calculated_identities),
            "determination_count": len(group_records),
            "total_groups": len(calculated_groups),
            "results_calculated": len(calculated_groups),
            "deferred_results": sum(
                1
                for item in group_records
                if item.get("determination_state") == BarGroupState.DEFERRED.value
            ),
            "blocked_results": sum(
                1
                for item in group_records
                if item.get("determination_state") == BarGroupState.BLOCKED.value
            ),
            "failed_results": sum(
                1
                for item in group_records
                if item.get("determination_state") == BarGroupState.FAILED.value
            ),
            "duplicate_groups": duplicate_groups,
            "largest_group_size": max(member_counts) if member_counts else 0,
            "average_group_size": (
                round(sum(member_counts) / len(member_counts), 2) if member_counts else 0.0
            ),
            "unique_engineering_signatures": len(signatures),
            "role_distribution": dict(role_dist),
            "diameter_distribution": dict(
                sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))
            ),
            "beam_distribution": dict(beam_dist),
            "shape_distribution": dict(shape_dist),
            "cut_length_distribution": dict(cut_length_dist),
            "rule_source_distribution": dict(source_dist),
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_signature": registry.get("results_by_signature", {}),
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
