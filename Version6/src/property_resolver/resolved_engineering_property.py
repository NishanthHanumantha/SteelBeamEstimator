"""Resolved Engineering Property model — Phase G.5.3.2."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from src.property_resolver.property_resolver_types import CREATED_PHASE, PREFIX_RESOLVED


def format_resolved_property_id(sequence: int) -> str:
    return f"{PREFIX_RESOLVED}::{sequence:06d}"


def build_resolved_engineering_property(
    resolved_property_id: str,
    engineering_object_id: str,
    property_type: str,
    resolved_value: Any,
    unit: str,
    selected_property_id: str,
    selected_candidate_id: str,
    selected_source_entity: str,
    resolution_strategy: str,
    resolution_confidence: float,
    candidate_count: int,
    conflicting_values: Optional[List[Any]] = None,
    alternative_property_ids: Optional[List[str]] = None,
    parser_versions: Optional[List[str]] = None,
    resolution_notes: str = "",
    created_timestamp: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "resolved_property_id": resolved_property_id,
        "engineering_object_id": engineering_object_id,
        "property_type": property_type,
        "resolved_value": resolved_value,
        "unit": unit,
        "selected_property_id": selected_property_id,
        "selected_candidate_id": selected_candidate_id,
        "selected_source_entity": selected_source_entity,
        "resolution_strategy": resolution_strategy,
        "resolution_confidence": round(resolution_confidence, 4),
        "candidate_count": candidate_count,
        "conflicting_values": list(conflicting_values or []),
        "alternative_property_ids": list(alternative_property_ids or []),
        "parser_versions": sorted(set(parser_versions or [])),
        "resolution_notes": resolution_notes,
        "created_timestamp": created_timestamp
        or datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "created_phase": CREATED_PHASE,
        },
    }
