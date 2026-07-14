"""Reinforcement calculation models — Phase I.2."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.reinforcement_calculation.reinforcement_types import CREATED_PHASE, READINESS_PHASE


def reinforcement_objects_applied(model: dict[str, Any]) -> bool:
    registry = model.get("reinforcement_registry", {})
    if registry.get("phase") == "Phase I.2" and registry.get("bar_count", 0) >= 0:
        return True
    if model.get("reinforcement_groups") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("reinforcement_calculation_complete"))


def build_reinforcement_bar(
    bar_id: str,
    beam_id: str,
    context_id: str,
    specification_id: str,
    bar_mark: Any,
    role: str,
    position: str,
    quantity: Any,
    diameter_mm: Any,
    steel_grade: Any,
    bar_type: str,
    continuity: str,
    orientation: Any,
    layer: Any,
    shape: Any,
    status: str,
    traceability: dict[str, Any],
    calculation_readiness: dict[str, Any] | None = None,
    created_timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Build an immutable reinforcement bar record."""
    record = {
        "bar_id": bar_id,
        "beam_id": beam_id,
        "context_id": context_id,
        "specification_id": specification_id,
        "bar_mark": bar_mark,
        "role": role,
        "position": position,
        "quantity": quantity,
        "diameter_mm": diameter_mm,
        "steel_grade": steel_grade,
        "bar_type": bar_type,
        "continuity": continuity,
        "orientation": orientation,
        "layer": layer,
        "shape": shape,
        "status": status,
        "traceability": dict(traceability),
        "created_timestamp": created_timestamp
        or datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "created_phase": CREATED_PHASE,
        },
    }
    if calculation_readiness is not None:
        record["calculation_readiness"] = dict(calculation_readiness)
        record["metadata"]["readiness_phase"] = READINESS_PHASE
    return record


def build_reinforcement_group(
    group_id: str,
    beam_id: str,
    context_id: str,
    specification_id: str,
    bars: List[dict[str, Any]],
    group_type: str,
    engineering_role: str,
    status: str,
    traceability: dict[str, Any],
    calculation_readiness: dict[str, Any] | None = None,
    created_timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Build an immutable reinforcement group containing normalized bars."""
    record = {
        "group_id": group_id,
        "beam_id": beam_id,
        "context_id": context_id,
        "specification_id": specification_id,
        "bars": list(bars),
        "group_type": group_type,
        "engineering_role": engineering_role,
        "status": status,
        "traceability": dict(traceability),
        "created_timestamp": created_timestamp
        or datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "created_phase": CREATED_PHASE,
        },
    }
    if calculation_readiness is not None:
        record["calculation_readiness"] = dict(calculation_readiness)
        record["metadata"]["readiness_phase"] = READINESS_PHASE
    return record
