"""Geometry reference interfaces — Phase H.1.1 (IDs only, no values)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, FrozenSet, Iterable


REFERENCE_INTERFACE_NAMES: FrozenSet[str] = frozenset({
    "GeometryReference",
    "BeamGeometryReference",
    "SupportReference",
    "CoordinateReference",
    "SectionReference",
})


@dataclass(frozen=True)
class GeometryReference:
    """Base geometry lookup reference."""

    geometry_id: str = ""


@dataclass(frozen=True)
class BeamGeometryReference:
    """Beam-level geometry references resolved in Phase H.2."""

    beam_geometry_id: str = ""
    clear_span_id: str = ""
    effective_span_id: str = ""
    beam_section_id: str = ""
    stationing_id: str = ""
    coordinate_system_id: str = ""
    support_start_id: str = ""
    support_end_id: str = ""


@dataclass(frozen=True)
class SupportReference:
    """Support face / bearing reference."""

    support_id: str = ""
    support_face_id: str = ""


@dataclass(frozen=True)
class CoordinateReference:
    """Engineering coordinate frame reference."""

    coordinate_system_id: str = ""
    origin_reference_id: str = ""


@dataclass(frozen=True)
class SectionReference:
    """Beam section geometry reference."""

    beam_section_id: str = ""
    section_profile_id: str = ""


def reference_to_dict(reference: Any) -> Dict[str, str]:
    """Serialize a reference interface to an ID-only dictionary."""
    return {field.name: str(getattr(reference, field.name) or "") for field in fields(reference)}


def build_geometry_reference(geometry_id: str = "") -> Dict[str, str]:
    return reference_to_dict(GeometryReference(geometry_id=geometry_id))


def build_beam_geometry_reference(
    beam_geometry_id: str = "",
    clear_span_id: str = "",
    effective_span_id: str = "",
    beam_section_id: str = "",
    stationing_id: str = "",
    coordinate_system_id: str = "",
    support_start_id: str = "",
    support_end_id: str = "",
) -> Dict[str, str]:
    return reference_to_dict(
        BeamGeometryReference(
            beam_geometry_id=beam_geometry_id,
            clear_span_id=clear_span_id,
            effective_span_id=effective_span_id,
            beam_section_id=beam_section_id,
            stationing_id=stationing_id,
            coordinate_system_id=coordinate_system_id,
            support_start_id=support_start_id,
            support_end_id=support_end_id,
        )
    )


def build_support_reference(
    support_id: str = "",
    support_face_id: str = "",
) -> Dict[str, str]:
    return reference_to_dict(
        SupportReference(support_id=support_id, support_face_id=support_face_id)
    )


def build_coordinate_reference(
    coordinate_system_id: str = "",
    origin_reference_id: str = "",
) -> Dict[str, str]:
    return reference_to_dict(
        CoordinateReference(
            coordinate_system_id=coordinate_system_id,
            origin_reference_id=origin_reference_id,
        )
    )


def build_section_reference(
    beam_section_id: str = "",
    section_profile_id: str = "",
) -> Dict[str, str]:
    return reference_to_dict(
        SectionReference(
            beam_section_id=beam_section_id,
            section_profile_id=section_profile_id,
        )
    )


def validate_reference_dict(reference: Dict[str, Any]) -> bool:
    """Return True when every reference value is an ID string (or empty)."""
    for value in reference.values():
        if value is None:
            continue
        if not isinstance(value, str):
            return False
        if value and not _looks_like_reference_id(value):
            return False
    return True


def validate_reference_interfaces(interfaces: Iterable[Dict[str, Any]]) -> bool:
    return all(validate_reference_dict(item) for item in interfaces)


def _looks_like_reference_id(value: str) -> bool:
    if not value:
        return True
    if "::" in value:
        return True
    return value.isupper() or value.replace("_", "").isalnum()
