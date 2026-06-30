"""Universal geometry entity schema for reinforcement drawing intelligence."""

from __future__ import annotations

from typing import Any, Optional

ENGINEERING_STATUS_GEOMETRY_ONLY = "GEOMETRY_ONLY"
STATUS_READY = "READY"

PREFIX_REGION = "REGION"
PREFIX_SKETCH = "SKETCH"
PREFIX_TEXT = "TXT"
PREFIX_LEADER = "LDR"
PREFIX_BLOCK = "BLK"
PREFIX_VIEW = "VIEW"


def geometry_entity(
    geometry_id: str,
    *,
    engineering_object_id: Optional[str] = None,
    engineering_status: str = ENGINEERING_STATUS_GEOMETRY_ONLY,
    status: str = STATUS_READY,
    **fields: Any,
) -> dict[str, Any]:
    """Build a geometry-only entity with reserved engineering identity fields."""
    entity = {
        "geometry_id": geometry_id,
        "engineering_object_id": engineering_object_id,
        "engineering_status": engineering_status,
        "status": status,
    }
    entity.update(fields)
    return entity


def format_geometry_id(prefix: str, index: int) -> str:
    return f"{prefix}::{index:03d}"
