"""Engineering Specification model — Phase H.1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.engineering_specifications.specification_types import (
    CREATED_PHASE,
    PREFIX_SPECIFICATION,
    PREFIX_SPECIFICATION_REGISTRY,
)


def format_specification_id(sequence: int) -> str:
    return f"{PREFIX_SPECIFICATION}::{sequence:06d}"


def format_specification_registry_id(beam_mark: str = "") -> str:
    if beam_mark:
        return f"{PREFIX_SPECIFICATION_REGISTRY}::{beam_mark.upper()}"
    return PREFIX_SPECIFICATION_REGISTRY


def engineering_specifications_applied(model: dict[str, Any]) -> bool:
    registry = model.get("specification_registry", {})
    if registry.get("phase") == "Phase H.1" and registry.get("specification_count", 0) >= 0:
        return True
    if model.get("engineering_specifications") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("engineering_specification_complete"))


def build_engineering_specification(
    specification_id: str,
    engineering_object_id: str,
    beam_id: str,
    reinforcement_role: str,
    reinforcement_type: str,
    specification_status: str,
    resolved_property_ids: List[str],
    resolved_properties: List[dict[str, Any]],
    property_lifecycle_summary: Dict[str, int],
    property_status_summary: Dict[str, int],
    resolution_summary: Dict[str, int],
    traceability: dict[str, Any],
    quantity: Any = None,
    diameter: Any = None,
    bar_type: Any = None,
    spacing: Any = None,
    bar_mark: Any = None,
    shape_code: Any = None,
    hook: Any = None,
    hook_direction: Any = None,
    level: Any = None,
    zone: Any = None,
    callout: Any = None,
    notes: Any = None,
    created_timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Build an immutable, reference-ready engineering specification record.

    Contains engineering intent (Category A) only. Geometry (Category B) is
    resolved in Phase H.2 through immutable IDs — never embedded here.
    """
    return {
        "specification_id": specification_id,
        "engineering_object_id": engineering_object_id,
        "beam_id": beam_id,
        "reinforcement_role": reinforcement_role,
        "reinforcement_type": reinforcement_type,
        "specification_status": specification_status,
        "resolved_property_ids": list(resolved_property_ids),
        "resolved_properties": list(resolved_properties),
        "quantity": quantity,
        "diameter": diameter,
        "bar_type": bar_type,
        "spacing": spacing,
        "bar_mark": bar_mark,
        "shape_code": shape_code,
        "hook": hook,
        "hook_direction": hook_direction,
        "level": level,
        "zone": zone,
        "callout": callout,
        "notes": notes,
        "property_lifecycle_summary": dict(property_lifecycle_summary),
        "property_status_summary": dict(property_status_summary),
        "resolution_summary": dict(resolution_summary),
        "traceability": traceability,
        "created_timestamp": created_timestamp
        or datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "created_phase": CREATED_PHASE,
        },
    }
