"""Engineering geometry association type constants — Phase H.2."""

from __future__ import annotations

from typing import FrozenSet

PREFIX_GEOMETRY_ASSOCIATION = "GEOM_ASSOC"
PREFIX_GEOMETRY_REGISTRY = "GEOM_ASSOC_REGISTRY"

CREATED_PHASE = "H.2"
REFERENCE_CONTRACT_VERSION = "H.1.1"

STATUS_VALID = "VALID"
STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_MISSING_BEAM = "MISSING_BEAM"
STATUS_MISSING_GEOMETRY = "MISSING_GEOMETRY"
STATUS_INVALID_REFERENCE = "INVALID_REFERENCE"
STATUS_AMBIGUOUS = "AMBIGUOUS"

VALID_ASSOCIATION_STATUSES: FrozenSet[str] = frozenset({
    STATUS_VALID,
    STATUS_UNRESOLVED,
    STATUS_MISSING_BEAM,
    STATUS_MISSING_GEOMETRY,
    STATUS_INVALID_REFERENCE,
    STATUS_AMBIGUOUS,
})

GEOMETRY_OWNED_VALUE_KEYS: FrozenSet[str] = frozenset({
    "clear_span",
    "effective_span",
    "coordinates",
    "centerline",
    "start_point",
    "end_point",
    "length_mm",
    "station_mm",
    "geometry",
    "polyline",
    "beam_axis",
    "beam_vector",
    "value",
    "width",
    "depth",
})

ASSOCIATION_REFERENCE_FIELDS: FrozenSet[str] = frozenset({
    "beam_geometry_id",
    "beam_section_id",
    "clear_span_id",
    "effective_span_id",
    "stationing_id",
    "coordinate_system_id",
    "support_start_id",
    "support_end_id",
    "knowledge_graph_node_id",
})

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "drawing_id",
    "drawing_set_id",
    "floor_id",
    "project_id",
    "registry_id",
    "association_count",
    "association_ids",
    "specification_count",
    "processed_specification_ids",
    "associations_by_status",
    "associations_by_beam",
    "associations",
})
