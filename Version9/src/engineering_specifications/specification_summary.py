"""Engineering Specification summary — Phase H.1."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_specifications.specification_types import (
    STATUS_COMPLETE,
    STATUS_CONFLICT,
    STATUS_DEFERRED,
    STATUS_PARTIAL,
)


class SpecificationSummary:
    """Build project-level engineering specification summary."""

    @staticmethod
    def build(
        engineering_objects: List[dict[str, Any]],
        specifications: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        lifecycle_totals: Dict[str, int] = {}
        property_counts: List[int] = []
        resolved_counts: List[int] = []
        deferred_counts: List[int] = []
        unknown_counts: List[int] = []
        conflict_counts: List[int] = []
        incomplete_specs: List[dict[str, Any]] = []

        for spec in specifications:
            spec_type = str(spec.get("reinforcement_type", "UNKNOWN"))
            by_type[spec_type] = by_type.get(spec_type, 0) + 1
            status = str(spec.get("specification_status", "UNKNOWN"))
            by_status[status] = by_status.get(status, 0) + 1

            props = spec.get("resolved_properties", [])
            property_counts.append(len(props))
            status_summary = spec.get("property_status_summary", {})
            resolved_counts.append(int(status_summary.get("resolved", 0)))
            deferred_counts.append(int(status_summary.get("deferred", 0)))
            unknown_counts.append(int(status_summary.get("unknown", 0)))
            conflict_counts.append(int(status_summary.get("conflict", 0)))

            for lifecycle, count in (spec.get("property_lifecycle_summary") or {}).items():
                lifecycle_totals[str(lifecycle)] = lifecycle_totals.get(str(lifecycle), 0) + int(
                    count
                )

            if status in {STATUS_PARTIAL, STATUS_CONFLICT, STATUS_DEFERRED}:
                incomplete_specs.append(
                    {
                        "specification_id": spec.get("specification_id"),
                        "engineering_object_id": spec.get("engineering_object_id"),
                        "reinforcement_type": spec_type,
                        "specification_status": status,
                        "unknown_count": status_summary.get("unknown", 0),
                        "deferred_count": status_summary.get("deferred", 0),
                        "conflict_count": status_summary.get("conflict", 0),
                    }
                )

        incomplete_specs.sort(
            key=lambda item: (
                -int(item.get("unknown_count", 0)),
                -int(item.get("deferred_count", 0)),
                str(item.get("specification_id", "")),
            )
        )

        avg_properties = (
            round(sum(property_counts) / len(property_counts), 2) if property_counts else 0.0
        )
        avg_resolved = (
            round(sum(resolved_counts) / len(resolved_counts), 2) if resolved_counts else 0.0
        )
        avg_deferred = (
            round(sum(deferred_counts) / len(deferred_counts), 2) if deferred_counts else 0.0
        )
        avg_unknown = (
            round(sum(unknown_counts) / len(unknown_counts), 2) if unknown_counts else 0.0
        )

        return {
            "phase": "Phase H.1",
            "status": "SPECIFICATIONS_CREATED",
            "engineering_object_count": len(engineering_objects),
            "specifications_created": len(specifications),
            "processed_object_count": registry.get("processed_object_count", 0),
            "skipped_object_count": registry.get("skipped_object_count", 0),
            "specifications_by_type": by_type,
            "specification_status": {
                STATUS_COMPLETE: by_status.get(STATUS_COMPLETE, 0),
                STATUS_PARTIAL: by_status.get(STATUS_PARTIAL, 0),
                STATUS_CONFLICT: by_status.get(STATUS_CONFLICT, 0),
                STATUS_DEFERRED: by_status.get(STATUS_DEFERRED, 0),
            },
            "average_properties_per_specification": avg_properties,
            "average_resolved_properties": avg_resolved,
            "average_deferred_properties": avg_deferred,
            "average_unknown_properties": avg_unknown,
            "lifecycle_distribution": lifecycle_totals,
            "conflict_statistics": {
                "specifications_with_conflicts": by_status.get(STATUS_CONFLICT, 0),
                "total_conflict_properties": sum(conflict_counts),
                "average_conflict_properties": round(
                    sum(conflict_counts) / len(conflict_counts), 2
                )
                if conflict_counts
                else 0.0,
            },
            "deferred_property_statistics": {
                "specifications_deferred": by_status.get(STATUS_DEFERRED, 0),
                "total_deferred_properties": sum(deferred_counts),
                "average_deferred_properties": avg_deferred,
            },
            "property_completeness": {
                "complete": by_status.get(STATUS_COMPLETE, 0),
                "partial": by_status.get(STATUS_PARTIAL, 0),
                "conflict": by_status.get(STATUS_CONFLICT, 0),
                "deferred": by_status.get(STATUS_DEFERRED, 0),
            },
            "top_incomplete_specifications": incomplete_specs[:10],
            "registry_counts": {
                "specification_count": registry.get("specification_count", 0),
                "processed_object_count": registry.get("processed_object_count", 0),
            },
            "validation_result": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
