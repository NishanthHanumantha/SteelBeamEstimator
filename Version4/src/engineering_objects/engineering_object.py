"""Engineering Object model — graph-instantiated entities."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.engineering_objects.engineering_object_types import (
    CREATED_PHASE,
    ENGINEERING_STATUS_OBJECT_CREATED,
    LIFECYCLE_OBJECT_CREATED,
)

PREFIX_OBJECT = "ENG_OBJ"
PREFIX_OBJECT_REGISTRY = "OBJ_REGISTRY"
PREFIX_GRAPH_NODE = "ENG_OBJ_NODE"


def format_object_id(sequence: int) -> str:
    return f"{PREFIX_OBJECT}::{sequence:06d}"


def format_object_registry_id(beam_mark: str) -> str:
    return f"{PREFIX_OBJECT_REGISTRY}::{beam_mark.upper()}"


def format_graph_node_id(object_id: str) -> str:
    return f"{PREFIX_GRAPH_NODE}::{object_id}"


def erc_engineering_object_ids(ctx: dict[str, Any]) -> List[str]:
    """Return object ID references from an ERC (list or legacy dict format)."""
    eng = ctx.get("engineering_objects")
    if isinstance(eng, list):
        return [item for item in eng if isinstance(item, str)]
    if isinstance(eng, dict):
        ids: List[str] = []
        for item in eng.get("objects", []):
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict):
                oid = item.get("object_id") or item.get("engineering_object_id")
                if oid:
                    ids.append(str(oid))
        return ids
    return []


def erc_engineering_object_count(ctx: dict[str, Any]) -> int:
    return len(erc_engineering_object_ids(ctx))


def erc_engineering_object_registry_section(ctx: dict[str, Any]) -> dict[str, Any]:
    section = ctx.get("engineering_object_registry")
    if isinstance(section, dict) and section.get("registry_id"):
        return section
    eng = ctx.get("engineering_objects")
    if isinstance(eng, dict) and eng.get("registry_id"):
        return eng
    return {}


def engineering_objects_applied(model: dict[str, Any]) -> bool:
    registry = model.get("engineering_object_registry", {})
    if registry.get("phase") == "Phase G.5.1" and registry.get("object_count", 0) > 0:
        return True
    if model.get("engineering_objects"):
        return True
    return bool(
        model.get("workspace_manager", {}).get("engineering_object_instantiation_complete")
    )


def build_engineering_object(
    object_id: str,
    object_type: str,
    owner_context_id: str,
    source_role_id: str,
    detail_context_id: str = "",
    drawing_id: str = "",
    drawing_set_id: str = "",
    source_relationship_ids: Optional[List[str]] = None,
    classification_source: str = "SEMANTIC_GRAPH",
    confidence: float = 0.0,
    engineering_status: str = ENGINEERING_STATUS_OBJECT_CREATED,
    lifecycle: str = LIFECYCLE_OBJECT_CREATED,
    notes: str = "",
    metadata: Optional[dict[str, Any]] = None,
    incoming_relationships: Optional[List[str]] = None,
    outgoing_relationships: Optional[List[str]] = None,
    incoming_relationship_ids: Optional[List[str]] = None,
    outgoing_relationship_ids: Optional[List[str]] = None,
    connected_object_ids: Optional[List[str]] = None,
    parent_group_ids: Optional[List[str]] = None,
    child_group_ids: Optional[List[str]] = None,
    annotation_ids: Optional[List[str]] = None,
) -> dict[str, Any]:
    in_rels = list(incoming_relationship_ids or incoming_relationships or [])
    out_rels = list(outgoing_relationship_ids or outgoing_relationships or [])
    return {
        "object_id": object_id,
        "engineering_object_id": object_id,
        "object_type": object_type,
        "owner_context_id": owner_context_id,
        "detail_context_id": detail_context_id,
        "drawing_id": drawing_id,
        "drawing_set_id": drawing_set_id,
        "source_role_id": source_role_id,
        "source_relationship_ids": list(source_relationship_ids or []),
        "classification_source": classification_source,
        "confidence": round(confidence, 4),
        "engineering_status": engineering_status,
        "lifecycle": lifecycle,
        "notes": notes,
        "graph_node_id": format_graph_node_id(object_id),
        "incoming_relationships": in_rels,
        "outgoing_relationships": out_rels,
        "incoming_relationship_ids": in_rels,
        "outgoing_relationship_ids": out_rels,
        "connected_object_ids": list(connected_object_ids or []),
        "parent_group_ids": list(parent_group_ids or []),
        "child_group_ids": list(child_group_ids or []),
        "annotation_ids": list(annotation_ids or []),
        "metadata": {
            "created_phase": CREATED_PHASE,
            **(metadata or {}),
        },
    }


def engineering_object_registry_section(
    beam_mark: str,
    object_ids: Optional[List[str]] = None,
) -> dict[str, Any]:
    ids = list(object_ids or [])
    return {
        "registry_id": format_object_registry_id(beam_mark),
        "object_count": len(ids),
        "objects": ids,
    }
