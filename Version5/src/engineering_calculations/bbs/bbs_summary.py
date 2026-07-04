"""BBS summary — Phase I.10."""

from __future__ import annotations

from collections import Counter
from typing import Any, List

from src.engineering_calculations.bar_group.bar_group_types import BarGroupState
from src.engineering_calculations.bbs.bbs_types import CREATED_PHASE, BbsState


class BbsSummary:
    """Build project-level BBS foundation summary."""

    @staticmethod
    def build(
        bars: List[dict[str, Any]],
        group_records: List[dict[str, Any]],
        bbs_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated_groups = [
            item
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        calculated_schedules = [
            item
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
        ]
        member_counts = [
            int(item.get("member_count") or len(item.get("member_bar_ids") or []))
            for item in calculated_schedules
            if int(item.get("member_count") or len(item.get("member_bar_ids") or [])) > 0
        ]
        fabrication_marks = {
            str(item.get("fabrication_mark"))
            for item in calculated_schedules
            if item.get("fabrication_mark")
        }
        signatures = {
            str(item.get("engineering_signature"))
            for item in calculated_schedules
            if item.get("engineering_signature")
        }
        fab_state_dist = Counter(
            str(item.get("fabrication_state"))
            for item in bbs_records
            if item.get("fabrication_state")
        )
        role_dist = Counter(
            role
            for item in calculated_schedules
            for role in (item.get("member_roles") or ([item.get("role")] if item.get("role") else []))
        )
        diameter_dist = Counter(
            str(item.get("diameter"))
            for item in calculated_schedules
            if item.get("diameter") is not None
        )
        beam_dist = Counter(
            beam
            for item in calculated_schedules
            for beam in (item.get("member_beams") or [])
        )
        shape_dist = Counter(
            str(item.get("shape_code"))
            for item in calculated_schedules
            if item.get("shape_code")
        )
        source_dist = Counter(
            str(item.get("rule_source"))
            for item in calculated_schedules
            if item.get("rule_source")
        )

        return {
            "phase": "Phase I.10",
            "framework_phase": CREATED_PHASE,
            "bar_count": len(bars),
            "calculated_groups": len(calculated_groups),
            "bbs_records": len(bbs_records),
            "determination_count": len(bbs_records),
            "results_calculated": len(calculated_schedules),
            "deferred_results": sum(
                1 for item in bbs_records if item.get("determination_state") == BbsState.DEFERRED.value
            ),
            "blocked_results": sum(
                1 for item in bbs_records if item.get("determination_state") == BbsState.BLOCKED.value
            ),
            "failed_results": sum(
                1 for item in bbs_records if item.get("determination_state") == BbsState.FAILED.value
            ),
            "duplicate_groups": sum(
                1
                for item in calculated_schedules
                if int(item.get("member_count") or len(item.get("member_bar_ids") or [])) > 1
            ),
            "largest_schedule": max(member_counts) if member_counts else 0,
            "average_members_per_schedule": (
                round(sum(member_counts) / len(member_counts), 2) if member_counts else 0.0
            ),
            "unique_fabrication_marks": len(fabrication_marks),
            "unique_engineering_signatures": len(signatures),
            "role_distribution": dict(role_dist),
            "diameter_distribution": dict(
                sorted(diameter_dist.items(), key=lambda kv: float(kv[0]))
            ),
            "beam_distribution": dict(beam_dist),
            "shape_distribution": dict(shape_dist),
            "fabrication_state_distribution": dict(fab_state_dist),
            "rule_source_distribution": dict(source_dist),
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
                "results_by_fabrication_mark": registry.get("results_by_fabrication_mark", {}),
                "results_by_signature": registry.get("results_by_signature", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
            "metadata_enabled": True,
        }
