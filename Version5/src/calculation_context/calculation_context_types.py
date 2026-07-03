"""Engineering calculation context type constants — Phase I.1."""

from __future__ import annotations

from typing import FrozenSet

PREFIX_CALCULATION_CONTEXT = "CALC_CTX"
PREFIX_CALCULATION_CONTEXT_REGISTRY = "CALC_CTX_REGISTRY"
NAMESPACE_CALCULATION_CONTEXT = "CALCULATION_CONTEXT"

CREATED_PHASE = "I.1"
CONTEXT_VERSION = "I.1"

STATUS_COMPLETE = "COMPLETE"
STATUS_PARTIAL = "PARTIAL"
STATUS_INCOMPLETE = "INCOMPLETE"

VALID_CALCULATION_STATUSES: FrozenSet[str] = frozenset({
    STATUS_COMPLETE,
    STATUS_PARTIAL,
    STATUS_INCOMPLETE,
})

REFERENCE_FIELDS: FrozenSet[str] = frozenset({
    "geometry_association_id",
    "beam_geometry_id",
    "beam_section_id",
    "length_model_id",
    "coordinate_system_id",
    "support_model_id",
    "knowledge_graph_node_id",
})

SCALAR_GEOMETRY_FIELDS: FrozenSet[str] = frozenset({
    "beam_width_mm",
    "beam_depth_mm",
    "clear_span_mm",
    "effective_span_mm",
    "beam_length_mm",
    "beam_orientation",
    "station_start",
    "station_end",
})

MATERIAL_FIELDS: FrozenSet[str] = frozenset({
    "concrete_grade",
    "steel_grade",
    "cover_top_mm",
    "cover_bottom_mm",
    "cover_side_mm",
})

RULE_REFERENCE_FIELDS: FrozenSet[str] = frozenset({
    "development_length_table",
    "hook_rule",
    "lap_rule",
    "bend_rule",
    "anchorage_rule",
    "splice_rule",
    "estimator_rules",
})

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "context_count",
    "context_ids",
    "specification_count",
    "processed_specification_ids",
    "contexts_by_status",
    "contexts_by_beam",
})
