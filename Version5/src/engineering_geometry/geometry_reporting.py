"""Geometry association reporting — Phase H.2."""

from __future__ import annotations

from typing import Any, List

from src.engineering_geometry.geometry_summary import GeometryAssociationSummary


class GeometryAssociationReporting:
    """Single source of truth for geometry association validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        associations = model.get("geometry_associations", [])
        registry = model.get("geometry_registry", {})
        model["geometry_validation"] = validation
        model["geometry_summary"] = GeometryAssociationSummary.build(
            model.get("engineering_specifications", []),
            associations,
            registry,
            validation,
            beam_count=len(model.get("beams", [])),
        )
        model["geometry_reporting"] = GeometryAssociationReporting.build(
            associations,
            registry,
            model["geometry_summary"],
        )

    @staticmethod
    def build(
        associations: List[dict[str, Any]],
        registry: dict[str, Any],
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "phase": "Phase H.2",
            "association_count": len(associations),
            "association_statistics": summary.get("association_status", {}),
            "coverage": {
                "beam_coverage": summary.get("beam_coverage", {}),
                "section_coverage": summary.get("section_coverage", {}),
                "support_coverage": summary.get("support_coverage", {}),
                "coordinate_coverage": summary.get("coordinate_coverage", {}),
                "knowledge_graph_coverage": summary.get("knowledge_graph_coverage", {}),
            },
            "missing_references": {
                "missing_beam_count": summary.get("missing_beam_count", 0),
                "missing_geometry_count": summary.get("missing_geometry_count", 0),
                "ambiguous_associations": summary.get("ambiguous_associations", 0),
            },
            "association_status": summary.get("association_status", {}),
            "registry_health": summary.get("registry_statistics", {}),
            "reference_completeness": {
                "average_references_per_association": summary.get(
                    "average_references_per_association", 0.0
                ),
                "association_success_rate": summary.get("association_success_rate", 0.0),
            },
            "registry_summary": {
                "association_count": registry.get("association_count", 0),
                "processed_specification_count": len(
                    registry.get("processed_specification_ids", [])
                ),
            },
        }
