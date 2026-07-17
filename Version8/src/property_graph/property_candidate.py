"""Property candidate model — Phase G.5.2."""

from __future__ import annotations

from typing import Any, List, Optional

from src.property_graph.property_graph_types import (
    CREATED_PHASE,
    STATUS_REGISTERED,
)

PREFIX_CANDIDATE = "PROP_CAND"
PREFIX_REGISTRY = "PROP_REGISTRY"


def format_candidate_id(sequence: int) -> str:
    return f"{PREFIX_CANDIDATE}::{sequence:06d}"


def format_property_registry_id(beam_mark: str) -> str:
    return f"{PREFIX_REGISTRY}::{beam_mark.upper()}"


def property_graph_applied(model: dict[str, Any]) -> bool:
    registry = model.get("property_registry", {})
    if registry.get("phase") == "Phase G.5.2" and registry.get("candidate_count", 0) > 0:
        return True
    if model.get("property_candidates"):
        return True
    return bool(model.get("workspace_manager", {}).get("property_graph_complete"))


def build_property_candidate(
    candidate_id: str,
    engineering_object_id: str,
    candidate_type: str,
    candidate_source_type: str,
    source_entity_id: str,
    source_relationship_id: str = "",
    confidence: float = 0.0,
    relationship_distance: int = 0,
    discovery_method: str = "UNKNOWN",
    status: str = STATUS_REGISTERED,
    owner_context_id: str = "",
    source_role_id: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "engineering_object_id": engineering_object_id,
        "candidate_type": candidate_type,
        "candidate_source_type": candidate_source_type,
        "source_entity_id": source_entity_id,
        "source_relationship_id": source_relationship_id,
        "confidence": round(confidence, 4),
        "relationship_distance": relationship_distance,
        "discovery_method": discovery_method,
        "status": status,
        "owner_context_id": owner_context_id,
        "source_role_id": source_role_id,
        "metadata": {
            "created_phase": CREATED_PHASE,
            **(metadata or {}),
        },
    }


def property_candidate_registry_section(
    beam_mark: str,
    candidate_ids: Optional[List[str]] = None,
) -> dict[str, Any]:
    ids = list(candidate_ids or [])
    return {
        "registry_id": format_property_registry_id(beam_mark),
        "candidate_count": len(ids),
        "candidate_ids": ids,
    }
