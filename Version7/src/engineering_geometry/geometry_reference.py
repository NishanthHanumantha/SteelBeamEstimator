"""Geometry reference ID formatters — Phase H.2."""

from __future__ import annotations

from src.framing.engineering_ids import (
    beam_id,
    ecs_id,
    length_id,
    section_id,
    support_structural_id,
)


def format_geometry_association_id(sequence: int) -> str:
    return f"GEOM_ASSOC::{sequence:06d}"


def format_geometry_registry_id() -> str:
    return "GEOM_ASSOC_REGISTRY"


def format_beam_geometry_id(beam_mark: str) -> str:
    return beam_id(beam_mark)


def format_beam_section_id(beam_mark: str) -> str:
    return section_id(beam_mark)


def format_clear_span_id(beam_mark: str) -> str:
    return f"CLEAR_SPAN::{beam_mark.upper()}"


def format_effective_span_id(beam_mark: str) -> str:
    return f"EFF_SPAN::{beam_mark.upper()}"


def format_stationing_id(beam_mark: str) -> str:
    return f"STATION::{beam_mark.upper()}"


def format_coordinate_system_id(beam_mark: str) -> str:
    return ecs_id(beam_mark)


def format_support_start_id(beam_mark: str) -> str:
    return f"SUPPORT::{beam_mark.upper()}_START"


def format_support_end_id(beam_mark: str) -> str:
    return f"SUPPORT::{beam_mark.upper()}_END"


def format_knowledge_graph_node_id(beam_mark: str) -> str:
    return beam_id(beam_mark)


def resolve_support_reference_id(
    support_type: str,
    support_id: str | None,
    fallback_id: str,
) -> str:
    resolved = support_structural_id(support_type, support_id)
    if resolved:
        return resolved
    return fallback_id
