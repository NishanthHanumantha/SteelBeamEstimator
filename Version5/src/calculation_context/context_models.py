"""Engineering Calculation Context model — Phase I.1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.calculation_context.calculation_context_types import (
    CONTEXT_VERSION,
    CREATED_PHASE,
)


def calculation_contexts_applied(model: dict[str, Any]) -> bool:
    registry = model.get("calculation_context_registry", {})
    if registry.get("phase") == "Phase I.1" and registry.get("context_count", 0) >= 0:
        return True
    if model.get("calculation_contexts") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("calculation_context_complete"))


def build_engineering_calculation_context(
    context_id: str,
    specification_id: str,
    association_id: str,
    engineering_object_id: str,
    beam_id: str,
    drawing_id: str,
    project_id: str,
    phase: str,
    geometry_association_id: str,
    beam_geometry_id: str,
    beam_section_id: str,
    length_model_id: str,
    coordinate_system_id: str,
    support_model_id: str,
    knowledge_graph_node_id: str,
    beam_width_mm: Any,
    beam_depth_mm: Any,
    clear_span_mm: Any,
    effective_span_mm: Any,
    beam_length_mm: Any,
    beam_orientation: Any,
    station_start: Any,
    station_end: Any,
    concrete_grade: Any,
    steel_grade: Any,
    cover_top_mm: Any,
    cover_bottom_mm: Any,
    cover_side_mm: Any,
    development_length_table: dict[str, Any],
    hook_rule: dict[str, Any],
    lap_rule: dict[str, Any],
    bend_rule: dict[str, Any],
    anchorage_rule: dict[str, Any],
    splice_rule: dict[str, Any],
    estimator_rules: dict[str, Any],
    calculation_status: str,
    traceability: dict[str, Any],
    created_timestamp: Optional[str] = None,
    context_version: str = CONTEXT_VERSION,
) -> dict[str, Any]:
    """Build an immutable engineering calculation context record."""
    return {
        "context_id": context_id,
        "specification_id": specification_id,
        "association_id": association_id,
        "engineering_object_id": engineering_object_id,
        "beam_id": beam_id,
        "drawing_id": drawing_id,
        "project_id": project_id,
        "phase": phase,
        "geometry_association_id": geometry_association_id,
        "beam_geometry_id": beam_geometry_id,
        "beam_section_id": beam_section_id,
        "length_model_id": length_model_id,
        "coordinate_system_id": coordinate_system_id,
        "support_model_id": support_model_id,
        "knowledge_graph_node_id": knowledge_graph_node_id,
        "beam_width_mm": beam_width_mm,
        "beam_depth_mm": beam_depth_mm,
        "clear_span_mm": clear_span_mm,
        "effective_span_mm": effective_span_mm,
        "beam_length_mm": beam_length_mm,
        "beam_orientation": beam_orientation,
        "station_start": station_start,
        "station_end": station_end,
        "concrete_grade": concrete_grade,
        "steel_grade": steel_grade,
        "cover_top_mm": cover_top_mm,
        "cover_bottom_mm": cover_bottom_mm,
        "cover_side_mm": cover_side_mm,
        "development_length_table": dict(development_length_table),
        "hook_rule": dict(hook_rule),
        "lap_rule": dict(lap_rule),
        "bend_rule": dict(bend_rule),
        "anchorage_rule": dict(anchorage_rule),
        "splice_rule": dict(splice_rule),
        "estimator_rules": dict(estimator_rules),
        "calculation_status": calculation_status,
        "context_version": context_version,
        "created_timestamp": created_timestamp
        or datetime.now(timezone.utc).isoformat(),
        "traceability": dict(traceability),
        "metadata": {
            "created_phase": CREATED_PHASE,
        },
    }
