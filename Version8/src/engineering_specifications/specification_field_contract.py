"""Specification field ownership contract — Phase H.1.1."""

from __future__ import annotations

from typing import FrozenSet

# Category A — engineering intent owned by EngineeringSpecification.
SPECIFICATION_OWNED_TOP_LEVEL_FIELDS: FrozenSet[str] = frozenset({
    "specification_id",
    "engineering_object_id",
    "beam_id",
    "reinforcement_role",
    "reinforcement_type",
    "specification_status",
    "resolved_property_ids",
    "resolved_properties",
    "quantity",
    "diameter",
    "bar_type",
    "spacing",
    "bar_mark",
    "shape_code",
    "hook",
    "hook_direction",
    "level",
    "zone",
    "callout",
    "notes",
    "property_lifecycle_summary",
    "property_status_summary",
    "resolution_summary",
    "traceability",
    "created_timestamp",
    "metadata",
})

# Category B — geometry owned exclusively by Phase F / Geometry Association.
GEOMETRY_OWNED_FIELDS: FrozenSet[str] = frozenset({
    "beam_length",
    "clear_span",
    "effective_span",
    "beam_axis",
    "coordinates",
    "start_support",
    "end_support",
    "stationing",
    "beam_section_geometry",
    "geometry_points",
    "polyline",
    "beam_vector",
    "coordinate_system",
    "beam_geometry",
    "geometry_reference",
    "support_geometry",
    "section_geometry",
    "axis_vector",
    "centerline",
    "start_station",
    "end_station",
    "offset_geometry",
    "position_geometry",
})

# Calculated engineering values — owned by Phase I+, never embedded in specifications.
CALCULATED_ENGINEERING_FIELDS: FrozenSet[str] = frozenset({
    "bar_length",
    "cut_length",
    "development_length",
    "lap_length",
    "anchorage",
    "curtailment",
    "hook_length",
    "fabrication_length",
    "total_bar_length",
    "steel_weight",
    "steel_quantity",
})

FORBIDDEN_SPECIFICATION_EMBEDDED_FIELDS: FrozenSet[str] = (
    GEOMETRY_OWNED_FIELDS | CALCULATED_ENGINEERING_FIELDS | frozenset({"geometry"})
)

SPECIFICATION_REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
    "registry_id",
    "specification_count",
    "specification_ids",
    "engineering_object_count",
    "processed_object_count",
    "skipped_object_count",
    "processed_object_ids",
    "skipped_object_ids",
    "specifications_by_type",
    "specifications_by_status",
    "specifications_by_beam",
    "specifications",
})
