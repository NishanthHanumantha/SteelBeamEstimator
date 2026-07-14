"""Geometry association summary — Phase H.2."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_geometry.geometry_types import (
    STATUS_AMBIGUOUS,
    STATUS_INVALID_REFERENCE,
    STATUS_MISSING_BEAM,
    STATUS_MISSING_GEOMETRY,
    STATUS_UNRESOLVED,
    STATUS_VALID,
)


class GeometryAssociationSummary:
    """Build project-level geometry association summary."""

    @staticmethod
    def build(
        specifications: List[dict[str, Any]],
        associations: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
        beam_count: int = 0,
    ) -> dict[str, Any]:
        by_status: Dict[str, int] = {}
        by_beam: Dict[str, int] = {}
        reference_counts: List[int] = []

        beam_coverage: set[str] = set()
        section_coverage: set[str] = set()
        support_coverage: set[str] = set()
        coordinate_coverage: set[str] = set()
        graph_coverage: set[str] = set()

        for assoc in associations:
            status = str(assoc.get("association_status", "UNKNOWN"))
            by_status[status] = by_status.get(status, 0) + 1
            beam = str(assoc.get("beam_id", ""))
            if beam:
                by_beam[beam] = by_beam.get(beam, 0) + 1

            refs = [
                assoc.get("beam_geometry_id"),
                assoc.get("beam_section_id"),
                assoc.get("clear_span_id"),
                assoc.get("effective_span_id"),
                assoc.get("stationing_id"),
                assoc.get("coordinate_system_id"),
                assoc.get("support_start_id"),
                assoc.get("support_end_id"),
                assoc.get("knowledge_graph_node_id"),
            ]
            reference_counts.append(sum(1 for ref in refs if ref))

            if assoc.get("beam_geometry_id"):
                beam_coverage.add(beam)
            if assoc.get("beam_section_id"):
                section_coverage.add(beam)
            if assoc.get("support_start_id") or assoc.get("support_end_id"):
                support_coverage.add(beam)
            if assoc.get("coordinate_system_id"):
                coordinate_coverage.add(beam)
            if assoc.get("knowledge_graph_node_id"):
                graph_coverage.add(beam)

        valid_count = by_status.get(STATUS_VALID, 0)
        success_rate = (
            round(valid_count / len(associations), 4) if associations else 0.0
        )
        avg_refs = (
            round(sum(reference_counts) / len(reference_counts), 2)
            if reference_counts
            else 0.0
        )

        return {
            "phase": "Phase H.2",
            "status": "ASSOCIATIONS_CREATED",
            "specifications_evaluated": len(specifications),
            "associations_created": len(associations),
            "association_success_rate": success_rate,
            "association_status": {
                STATUS_VALID: by_status.get(STATUS_VALID, 0),
                STATUS_UNRESOLVED: by_status.get(STATUS_UNRESOLVED, 0),
                STATUS_MISSING_BEAM: by_status.get(STATUS_MISSING_BEAM, 0),
                STATUS_MISSING_GEOMETRY: by_status.get(STATUS_MISSING_GEOMETRY, 0),
                STATUS_INVALID_REFERENCE: by_status.get(STATUS_INVALID_REFERENCE, 0),
                STATUS_AMBIGUOUS: by_status.get(STATUS_AMBIGUOUS, 0),
            },
            "beam_coverage": {
                "beams_with_geometry_reference": len(beam_coverage),
                "total_beams_in_model": beam_count,
            },
            "section_coverage": {
                "beams_with_section_reference": len(section_coverage),
            },
            "support_coverage": {
                "beams_with_support_reference": len(support_coverage),
            },
            "coordinate_coverage": {
                "beams_with_coordinate_reference": len(coordinate_coverage),
            },
            "knowledge_graph_coverage": {
                "beams_with_graph_reference": len(graph_coverage),
            },
            "missing_beam_count": by_status.get(STATUS_MISSING_BEAM, 0),
            "missing_geometry_count": by_status.get(STATUS_MISSING_GEOMETRY, 0),
            "ambiguous_associations": by_status.get(STATUS_AMBIGUOUS, 0),
            "registry_statistics": {
                "association_count": registry.get("association_count", 0),
                "processed_specification_count": len(
                    registry.get("processed_specification_ids", [])
                ),
            },
            "average_references_per_association": avg_refs,
            "validation_result": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
