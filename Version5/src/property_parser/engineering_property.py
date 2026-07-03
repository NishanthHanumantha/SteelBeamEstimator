"""Engineering Property model — Phase G.5.3.1."""

from __future__ import annotations

from typing import Any, Optional

from src.property_parser.property_parser_types import (
    CREATED_PHASE,
    PARSE_STATUS_PARSED,
    PARSER_NAME_TEXT,
    PARSER_VERSION,
)

PREFIX_PROPERTY = "ENG_PROP"
PREFIX_PARSER_REGISTRY = "PROP_PARSER_REGISTRY"


def format_property_id(sequence: int) -> str:
    return f"{PREFIX_PROPERTY}::{sequence:06d}"


def format_parser_registry_id(beam_mark: str = "") -> str:
    if beam_mark:
        return f"{PREFIX_PARSER_REGISTRY}::{beam_mark.upper()}"
    return PREFIX_PARSER_REGISTRY


def property_parser_applied(model: dict[str, Any]) -> bool:
    registry = model.get("property_parser_registry", {})
    if registry.get("phase") == "Phase G.5.3.1":
        return True
    if model.get("engineering_properties") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("property_parser_complete"))


def build_engineering_property(
    property_id: str,
    engineering_object_id: str,
    candidate_id: str,
    property_type: str,
    parsed_value: Any,
    normalized_value: Any,
    unit: str,
    source_entity_id: str,
    source_text: str = "",
    parse_status: str = PARSE_STATUS_PARSED,
    confidence: float = 0.0,
    parser_name: str = PARSER_NAME_TEXT,
    parser_version: str = PARSER_VERSION,
    source_role_id: str = "",
    owner_context_id: str = "",
    unparsed_reason: str = "",
    created_from_candidate: bool = True,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "property_id": property_id,
        "engineering_object_id": engineering_object_id,
        "candidate_id": candidate_id,
        "property_type": property_type,
        "parsed_value": parsed_value,
        "normalized_value": normalized_value,
        "unit": unit,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "confidence": round(confidence, 4),
        "source_entity_id": source_entity_id,
        "source_text": source_text,
        "parse_status": parse_status,
        "created_from_candidate": created_from_candidate,
        "source_role_id": source_role_id,
        "owner_context_id": owner_context_id,
        "unparsed_reason": unparsed_reason,
        "metadata": {
            "created_phase": CREATED_PHASE,
            **(metadata or {}),
        },
    }
