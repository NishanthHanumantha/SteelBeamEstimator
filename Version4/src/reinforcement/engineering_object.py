"""Engineering Object base schema — BIM-like object model for reinforcement."""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, Optional

from src.reinforcement.engineering_object_types import G51_OBJECT_TYPES

PREFIX_ENG_OBJ = "ENG_OBJ"
PREFIX_ENG_OBJ_REGISTRY = "ENG_OBJ_REGISTRY"

ENGINEERING_STATUS_PLACEHOLDER = "PLACEHOLDER"
ENGINEERING_STATUS_OBJECT_CREATED = "OBJECT_CREATED"
CREATED_PHASE_G42 = "G.4.2"
CREATED_PHASE_G51 = "G.5.1"

OBJECT_TYPE_BAR = "BAR"
OBJECT_TYPE_STIRRUP = "STIRRUP"
OBJECT_TYPE_HOOK = "HOOK"
OBJECT_TYPE_LAP_SPLICE = "LAP_SPLICE"
OBJECT_TYPE_DEVELOPMENT_LENGTH = "DEVELOPMENT_LENGTH"
OBJECT_TYPE_ANCHORAGE = "ANCHORAGE"
OBJECT_TYPE_COVER = "COVER"
OBJECT_TYPE_ASSEMBLY = "ASSEMBLY"
OBJECT_TYPE_ZONE = "ZONE"

VALID_OBJECT_TYPES: FrozenSet[str] = frozenset({
    OBJECT_TYPE_BAR,
    OBJECT_TYPE_STIRRUP,
    OBJECT_TYPE_HOOK,
    OBJECT_TYPE_LAP_SPLICE,
    OBJECT_TYPE_DEVELOPMENT_LENGTH,
    OBJECT_TYPE_ANCHORAGE,
    OBJECT_TYPE_COVER,
    OBJECT_TYPE_ASSEMBLY,
    OBJECT_TYPE_ZONE,
}) | G51_OBJECT_TYPES

# Future subtypes — architecture only, no implementation
BAR_SUBTYPES: FrozenSet[str] = frozenset({
    "LONGITUDINAL",
    "TOP",
    "BOTTOM",
    "CURTAILMENT",
    "BENT",
    "CRANKED",
    "SIDE",
})


def format_engineering_object_id(sequence: int) -> str:
    return f"{PREFIX_ENG_OBJ}::{sequence:06d}"


def format_engineering_object_registry_id(beam_mark: str) -> str:
    return f"{PREFIX_ENG_OBJ_REGISTRY}::{beam_mark.upper()}"


def empty_asset_references() -> dict[str, list[str]]:
    return {
        "geometry": [],
        "text": [],
        "leaders": [],
        "blocks": [],
    }


def engineering_object_instantiation_applied(model: dict[str, Any]) -> bool:
    if model.get("engineering_object_classification"):
        return True
    registry = model.get("engineering_object_registry", {})
    if registry.get("phase") == "Phase G.5.1" and registry.get("object_count", 0) > 0:
        return True
    contexts = model.get("engineering_reinforcement_contexts", [])
    if contexts:
        section = contexts[0].get("engineering_objects", {})
        if section.get("object_count", 0) > 0:
            return True
    return bool(
        model.get("workspace_manager", {}).get("engineering_object_instantiation_complete")
    )


def engineering_object_applied(model: dict[str, Any]) -> bool:
    if model.get("engineering_object_registry") is not None:
        return True
    contexts = model.get("engineering_reinforcement_contexts", [])
    if contexts and "engineering_objects" in contexts[0]:
        return True
    return bool(
        model.get("workspace_manager", {}).get("engineering_object_framework_complete")
    )


def build_engineering_object(
    engineering_object_id: str,
    object_type: str,
    owner_context_id: str,
    owner_registry_id: str,
    object_subtype: Optional[str] = None,
    lifecycle: str = "NOT_CREATED",
    asset_references: Optional[dict[str, list[str]]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build a single engineering object dict following the base schema."""
    return {
        "engineering_object_id": engineering_object_id,
        "object_type": object_type,
        "object_subtype": object_subtype,
        "owner_context_id": owner_context_id,
        "owner_registry_id": owner_registry_id,
        "asset_references": asset_references or empty_asset_references(),
        "engineering_status": ENGINEERING_STATUS_PLACEHOLDER,
        "lifecycle": lifecycle,
        "metadata": {
            "created_phase": CREATED_PHASE_G42,
            **(metadata or {}),
        },
    }


def build_instantiated_engineering_object(
    engineering_object_id: str,
    object_type: str,
    owner_context_id: str,
    owner_registry_id: str,
    asset_references: Optional[dict[str, list[str]]] = None,
    classification_source: str = "INFERRED",
    confidence: float = 0.0,
    lifecycle: str = "CREATED",
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "engineering_object_id": engineering_object_id,
        "object_type": object_type,
        "object_subtype": None,
        "owner_context_id": owner_context_id,
        "owner_registry_id": owner_registry_id,
        "asset_references": asset_references or empty_asset_references(),
        "classification_source": classification_source,
        "confidence": confidence,
        "engineering_status": ENGINEERING_STATUS_OBJECT_CREATED,
        "lifecycle": lifecycle,
        "metadata": {
            "created_phase": CREATED_PHASE_G51,
            **(metadata or {}),
        },
    }


def engineering_objects_section(
    beam_mark: str,
    objects: Optional[list[Any]] = None,
    object_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    if object_ids is not None:
        ids = list(object_ids)
        return {
            "registry_id": format_engineering_object_registry_id(beam_mark),
            "object_count": len(ids),
            "objects": ids,
        }
    obj_list = list(objects or [])
    return {
        "registry_id": format_engineering_object_registry_id(beam_mark),
        "object_count": len(obj_list),
        "objects": obj_list,
    }
