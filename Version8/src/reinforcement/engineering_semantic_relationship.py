"""Engineering Semantic Relationship model — connects semantic roles within an ERC."""

from __future__ import annotations

from typing import Any, List, Optional

PREFIX_SEM_REL = "SEM_REL"
PREFIX_SEM_REL_REGISTRY = "SEM_REL_REGISTRY"

ENGINEERING_STATUS_RELATIONSHIP_CLASSIFIED = "RELATIONSHIP_CLASSIFIED"
CREATED_PHASE_G501 = "G.5.0.1"


def format_semantic_relationship_id(sequence: int) -> str:
    return f"{PREFIX_SEM_REL}::{sequence:06d}"


def format_semantic_relationship_registry_id(beam_mark: str) -> str:
    return f"{PREFIX_SEM_REL_REGISTRY}::{beam_mark.upper()}"


def semantic_relationships_applied(model: dict[str, Any]) -> bool:
    if model.get("engineering_semantic_relationship_registry"):
        return True
    contexts = model.get("engineering_reinforcement_contexts", [])
    if contexts and contexts[0].get("semantic_relationship_registry"):
        return True
    return bool(
        model.get("workspace_manager", {}).get("engineering_semantic_relationship_complete")
    )


def build_semantic_relationship(
    relationship_id: str,
    relationship_type: str,
    source_role_id: str,
    target_role_id: str,
    owner_context_id: str,
    detail_context_id: str = "",
    drawing_id: str = "",
    drawing_set_id: str = "",
    classification_source: str = "INFERRED",
    confidence: float = 0.0,
    lifecycle: str = "CLASSIFIED",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "relationship_id": relationship_id,
        "relationship_type": relationship_type,
        "source_role_id": source_role_id,
        "target_role_id": target_role_id,
        "owner_context_id": owner_context_id,
        "detail_context_id": detail_context_id,
        "drawing_id": drawing_id,
        "drawing_set_id": drawing_set_id,
        "classification_source": classification_source,
        "confidence": confidence,
        "engineering_status": ENGINEERING_STATUS_RELATIONSHIP_CLASSIFIED,
        "lifecycle": lifecycle,
        "notes": notes,
        "metadata": {
            "created_phase": CREATED_PHASE_G501,
        },
    }


def semantic_relationship_registry_section(
    beam_mark: str,
    relationship_ids: Optional[List[str]] = None,
) -> dict[str, Any]:
    return {
        "registry_id": format_semantic_relationship_registry_id(beam_mark),
        "relationship_count": len(relationship_ids or []),
        "relationship_ids": list(relationship_ids or []),
    }
