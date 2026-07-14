"""Engineering Specification reporting — Phase H.1."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_specifications.specification_summary import SpecificationSummary
from src.engineering_specifications.specification_types import (
    STATUS_COMPLETE,
    STATUS_CONFLICT,
    STATUS_DEFERRED,
    STATUS_PARTIAL,
)


class SpecificationReporting:
    """Single source of truth for specification validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        specifications = model.get("engineering_specifications", [])
        registry = model.get("specification_registry", {})
        model["specification_validation"] = validation
        model["specification_summary"] = SpecificationSummary.build(
            model.get("engineering_objects", []),
            specifications,
            registry,
            validation,
        )
        model["specification_reporting"] = SpecificationReporting.build(
            specifications,
            registry,
            model["specification_summary"],
        )

    @staticmethod
    def build(
        specifications: List[dict[str, Any]],
        registry: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        status_distribution = summary.get("specification_status", {})
        type_distribution = summary.get("specifications_by_type", {})
        lifecycle_coverage = summary.get("lifecycle_distribution", {})

        return {
            "phase": "Phase H.1",
            "specification_count": len(specifications),
            "status_distribution": status_distribution,
            "type_distribution": type_distribution,
            "lifecycle_coverage": lifecycle_coverage,
            "deferred_property_statistics": summary.get("deferred_property_statistics", {}),
            "conflict_statistics": summary.get("conflict_statistics", {}),
            "property_completeness": summary.get("property_completeness", {}),
            "top_incomplete_specifications": summary.get("top_incomplete_specifications", []),
            "registry_summary": {
                "specification_count": registry.get("specification_count", 0),
                "processed_object_count": registry.get("processed_object_count", 0),
                "skipped_object_count": registry.get("skipped_object_count", 0),
            },
            "status_labels": {
                "complete": STATUS_COMPLETE,
                "partial": STATUS_PARTIAL,
                "conflict": STATUS_CONFLICT,
                "deferred": STATUS_DEFERRED,
            },
        }
