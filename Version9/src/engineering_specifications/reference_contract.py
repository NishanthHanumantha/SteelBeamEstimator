"""Engineering reference contract — Phase H.1.1."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_specifications.reference_interfaces import (
    REFERENCE_INTERFACE_NAMES,
    build_beam_geometry_reference,
    build_coordinate_reference,
    build_geometry_reference,
    build_section_reference,
    build_support_reference,
)
from src.engineering_specifications.specification_field_contract import (
    CALCULATED_ENGINEERING_FIELDS,
    GEOMETRY_OWNED_FIELDS,
    SPECIFICATION_OWNED_TOP_LEVEL_FIELDS,
)

CONTRACT_VERSION = "H.1.1"
CONTRACT_PHASE = "Phase H.1.1"


def build_reference_contract() -> Dict[str, Any]:
    """Formal contract for geometry access across future engineering phases."""
    return {
        "phase": CONTRACT_PHASE,
        "contract_version": CONTRACT_VERSION,
        "principle": (
            "EngineeringSpecification contains engineering meaning only. "
            "Geometry remains a single source of truth in Phase F and "
            "Geometry Association (Phase H.2). Future phases resolve geometry "
            "through immutable IDs, never duplicated values."
        ),
        "architecture_flow": [
            "Drawing Entities",
            "Semantic Roles",
            "Engineering Objects",
            "Resolved Properties",
            "Engineering Specifications (reference-ready)",
            "Geometry Association",
            "Beam Geometry",
            "Engineering Calculations",
        ],
        "reference_flow": [
            "EngineeringSpecification",
            "GeometryAssociation",
            "BeamGeometry",
            "EngineeringCalculation",
        ],
        "specification_owned_fields": sorted(SPECIFICATION_OWNED_TOP_LEVEL_FIELDS),
        "geometry_owned_fields": sorted(GEOMETRY_OWNED_FIELDS),
        "calculated_engineering_fields": sorted(CALCULATED_ENGINEERING_FIELDS),
        "reference_interfaces": sorted(REFERENCE_INTERFACE_NAMES),
        "reference_interface_examples": {
            "GeometryReference": build_geometry_reference(),
            "BeamGeometryReference": build_beam_geometry_reference(),
            "SupportReference": build_support_reference(),
            "CoordinateReference": build_coordinate_reference(),
            "SectionReference": build_section_reference(),
        },
        "rules": [
            "Specifications must never embed geometry values.",
            "GeometryAssociation stores ID references only.",
            "Calculation engines retrieve geometry through references.",
            "Phase F beam geometry outputs remain authoritative.",
            "No span, coordinate, or section duplication in specifications.",
        ],
        "future_integration": {
            "geometry_association_phase": "H.2",
            "geometry_source_phase": "F",
            "calculation_phase": "I",
        },
    }


def assert_specification_reference_integrity(specification: Dict[str, Any]) -> List[str]:
    """Return violation messages when a specification embeds forbidden fields."""
    violations: List[str] = []
    for field_name in specification:
        if field_name in GEOMETRY_OWNED_FIELDS | CALCULATED_ENGINEERING_FIELDS:
            violations.append(f"forbidden embedded field: {field_name}")
    return violations
