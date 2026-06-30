"""Engineering Semantic Role model — semantic meaning without engineering decisions."""

from __future__ import annotations

from src.reinforcement.engineering_semantic_role_types import priority_for_role_type

PREFIX_SEMANTIC_ROLE = "SEM_ROLE"
PREFIX_SEM_ROLE_REGISTRY = "SEM_ROLE_REGISTRY"

ENGINEERING_STATUS_ROLE_CLASSIFIED = "ROLE_CLASSIFIED"
CREATED_PHASE_G50 = "G.5.0"


def format_semantic_role_id(sequence: int) -> str:
    return f"{PREFIX_SEMANTIC_ROLE}::{sequence:06d}"


def format_semantic_role_registry_id(beam_mark: str) -> str:
    return f"{PREFIX_SEM_ROLE_REGISTRY}::{beam_mark.upper()}"


def semantic_roles_applied(model: dict[str, Any]) -> bool:
    if model.get("engineering_semantic_role_registry"):
        return True
    contexts = model.get("engineering_reinforcement_contexts", [])
    if contexts and contexts[0].get("semantic_role_registry"):
        return True
    return bool(
        model.get("workspace_manager", {}).get("engineering_semantic_role_complete")
    )


def build_semantic_role(
    semantic_role_id: str,
    role_type: str,
    owner_context_id: str,
    detail_context_id: str = "",
    drawing_id: str = "",
    drawing_set_id: str = "",
    beam_match_id: str = "",
    geometry_asset_ids: Optional[List[str]] = None,
    text_asset_ids: Optional[List[str]] = None,
    leader_asset_ids: Optional[List[str]] = None,
    block_asset_ids: Optional[List[str]] = None,
    source_geometry_ids: Optional[List[str]] = None,
    classification_source: str = "INFERRED",
    classification_confidence: float = 0.0,
    lifecycle: str = "CLASSIFIED",
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "semantic_role_id": semantic_role_id,
        "role_type": role_type,
        "owner_context_id": owner_context_id,
        "detail_context_id": detail_context_id,
        "drawing_id": drawing_id,
        "drawing_set_id": drawing_set_id,
        "beam_match_id": beam_match_id,
        "geometry_asset_ids": list(geometry_asset_ids or []),
        "text_asset_ids": list(text_asset_ids or []),
        "leader_asset_ids": list(leader_asset_ids or []),
        "block_asset_ids": list(block_asset_ids or []),
        "source_geometry_ids": list(source_geometry_ids or geometry_asset_ids or []),
        "classification_source": classification_source,
        "classification_confidence": classification_confidence,
        "engineering_status": ENGINEERING_STATUS_ROLE_CLASSIFIED,
        "engineering_priority": priority_for_role_type(role_type),
        "lifecycle": lifecycle,
        "future_engineering_object_id": None,
        "metadata": {
            "created_phase": CREATED_PHASE_G50,
            **(metadata or {}),
        },
    }


def semantic_role_registry_section(
    beam_mark: str,
    role_count: int = 0,
    role_ids: Optional[List[str]] = None,
) -> dict[str, Any]:
    return {
        "registry_id": format_semantic_role_registry_id(beam_mark),
        "role_count": role_count if role_ids is None else len(role_ids),
        "semantic_role_ids": list(role_ids or []),
    }


def semantic_roles_section(
    beam_mark: str,
    role_ids: Optional[List[str]] = None,
) -> List[str]:
    return list(role_ids or [])
