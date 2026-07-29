"""Property availability engine — Phase G.5.3.4."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from src.property_resolver.property_lifecycle import (
    LIFECYCLE_AVAILABLE_FROM,
    LIFECYCLE_DEFER_REASON,
    PHASE_ORDER,
    PROPERTY_TYPE_LIFECYCLE,
    EngineeringPropertyLifecycle,
    PipelineAvailabilityStage,
)
from src.property_resolver.property_resolver_types import (
    RESOLUTION_CONFLICT,
    RESOLUTION_UNKNOWN,
)

AVAILABILITY_AVAILABLE = "AVAILABLE"
AVAILABILITY_NOT_AVAILABLE_YET = "NOT_AVAILABLE_YET"
AVAILABILITY_INVALID_PROPERTY = "INVALID_PROPERTY"
AVAILABILITY_UNKNOWN_PROPERTY = "UNKNOWN_PROPERTY"

PROPERTY_STATUS_RESOLVED = "RESOLVED"
PROPERTY_STATUS_CONFLICT = "CONFLICT"
PROPERTY_STATUS_UNKNOWN = "UNKNOWN"
PROPERTY_STATUS_NOT_AVAILABLE_YET = "NOT_AVAILABLE_YET"

VALID_PROPERTY_STATUSES = frozenset({
    PROPERTY_STATUS_RESOLVED,
    PROPERTY_STATUS_CONFLICT,
    PROPERTY_STATUS_UNKNOWN,
    PROPERTY_STATUS_NOT_AVAILABLE_YET,
})

CURRENT_PIPELINE_PHASE = PipelineAvailabilityStage.PHASE_G.value


def get_property_lifecycle(property_type: str) -> str:
    lifecycle = PROPERTY_TYPE_LIFECYCLE.get(str(property_type).upper())
    if lifecycle is None:
        lifecycle = PROPERTY_TYPE_LIFECYCLE.get(str(property_type))
    if lifecycle is None:
        return EngineeringPropertyLifecycle.UNKNOWN.value
    return lifecycle.value


def get_property_available_phase(property_type: str) -> str:
    lifecycle_name = get_property_lifecycle(property_type)
    try:
        lifecycle = EngineeringPropertyLifecycle(lifecycle_name)
    except ValueError:
        return PipelineAvailabilityStage.PHASE_G.value
    return LIFECYCLE_AVAILABLE_FROM[lifecycle].value


def is_property_available(property_type: str, current_phase: str = CURRENT_PIPELINE_PHASE) -> bool:
    availability = evaluate_property_availability(property_type, current_phase)
    return availability == AVAILABILITY_AVAILABLE


def evaluate_property_availability(
    property_type: str,
    current_phase: str = CURRENT_PIPELINE_PHASE,
) -> str:
    normalized = str(property_type or "").upper()
    if not normalized:
        return AVAILABILITY_INVALID_PROPERTY
    if normalized not in PROPERTY_TYPE_LIFECYCLE and normalized != "UNKNOWN":
        return AVAILABILITY_UNKNOWN_PROPERTY

    available_from = get_property_available_phase(normalized)
    current_order = PHASE_ORDER.get(current_phase, 0)
    available_order = PHASE_ORDER.get(available_from, 0)
    if current_order >= available_order:
        return AVAILABILITY_AVAILABLE
    return AVAILABILITY_NOT_AVAILABLE_YET


def availability_reason(
    property_type: str,
    current_phase: str = CURRENT_PIPELINE_PHASE,
) -> str:
    availability = evaluate_property_availability(property_type, current_phase)
    if availability == AVAILABILITY_AVAILABLE:
        return "Available in current pipeline phase."
    if availability == AVAILABILITY_NOT_AVAILABLE_YET:
        lifecycle_name = get_property_lifecycle(property_type)
        try:
            lifecycle = EngineeringPropertyLifecycle(lifecycle_name)
            return LIFECYCLE_DEFER_REASON.get(
                lifecycle,
                f"Available from {get_property_available_phase(property_type)}.",
            )
        except ValueError:
            return f"Available from {get_property_available_phase(property_type)}."
    if availability == AVAILABILITY_INVALID_PROPERTY:
        return "Invalid property type."
    return "Unknown property lifecycle mapping."


def derive_property_status(resolved: dict[str, Any], current_phase: str = CURRENT_PIPELINE_PHASE) -> str:
    property_type = str(resolved.get("property_type", ""))
    if not is_property_available(property_type, current_phase):
        return PROPERTY_STATUS_NOT_AVAILABLE_YET

    strategy = str(resolved.get("resolution_strategy", ""))
    if strategy == RESOLUTION_CONFLICT:
        return PROPERTY_STATUS_CONFLICT
    if strategy == RESOLUTION_UNKNOWN:
        return PROPERTY_STATUS_UNKNOWN
    return PROPERTY_STATUS_RESOLVED


def apply_lifecycle_to_resolved(
    resolved: dict[str, Any],
    current_phase: str = CURRENT_PIPELINE_PHASE,
) -> dict[str, Any]:
    property_type = str(resolved.get("property_type", ""))
    lifecycle = get_property_lifecycle(property_type)
    available_from = get_property_available_phase(property_type)
    reason = availability_reason(property_type, current_phase)
    status = derive_property_status(resolved, current_phase)

    resolved["lifecycle"] = lifecycle
    resolved["available_from_phase"] = available_from
    resolved["property_status"] = status
    resolved["availability_reason"] = reason

    if status == PROPERTY_STATUS_NOT_AVAILABLE_YET:
        resolved["resolved_value"] = None
        resolved["resolution_confidence"] = 0.0

    return resolved


def apply_lifecycle_to_resolved_properties(
    resolved_properties: List[dict[str, Any]],
    current_phase: str = CURRENT_PIPELINE_PHASE,
) -> List[dict[str, Any]]:
    return [
        apply_lifecycle_to_resolved(resolved, current_phase=current_phase)
        for resolved in resolved_properties
    ]


def build_property_availability_report(
    resolved_properties: List[dict[str, Any]],
    current_phase: str = CURRENT_PIPELINE_PHASE,
) -> dict[str, Any]:
    by_type: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "resolved_count": 0,
            "deferred_count": 0,
            "unknown_count": 0,
            "conflict_count": 0,
            "total_count": 0,
        }
    )

    for resolved in resolved_properties:
        ptype = str(resolved.get("property_type", "UNKNOWN"))
        stats = by_type[ptype]
        stats["total_count"] += 1
        status = str(resolved.get("property_status", ""))
        if status == PROPERTY_STATUS_NOT_AVAILABLE_YET:
            stats["deferred_count"] += 1
        elif status == PROPERTY_STATUS_UNKNOWN:
            stats["unknown_count"] += 1
        elif status == PROPERTY_STATUS_CONFLICT:
            stats["conflict_count"] += 1
        else:
            stats["resolved_count"] += 1

    property_types: List[dict[str, Any]] = []
    for ptype in sorted(by_type.keys()):
        stats = by_type[ptype]
        lifecycle = get_property_lifecycle(ptype)
        available_from = get_property_available_phase(ptype)
        total = stats["total_count"]
        resolved_count = stats["resolved_count"]
        deferred_count = stats["deferred_count"]
        property_types.append(
            {
                "property_type": ptype,
                "lifecycle": lifecycle,
                "available_from_phase": available_from,
                "total_count": total,
                "resolved_count": resolved_count,
                "deferred_count": deferred_count,
                "unknown_count": stats["unknown_count"],
                "conflict_count": stats["conflict_count"],
                "availability_percentage": round(
                    resolved_count / total if total else 0.0, 4
                ),
                "deferred_percentage": round(
                    deferred_count / total if total else 0.0, 4
                ),
            }
        )

    available_count = sum(
        1
        for item in resolved_properties
        if item.get("property_status")
        not in (PROPERTY_STATUS_NOT_AVAILABLE_YET,)
    )
    deferred_count = sum(
        1
        for item in resolved_properties
        if item.get("property_status") == PROPERTY_STATUS_NOT_AVAILABLE_YET
    )
    total = len(resolved_properties)

    return {
        "phase": "Phase G.5.3.4",
        "current_pipeline_phase": current_phase,
        "property_type_count": len(property_types),
        "total_resolved_properties": total,
        "available_count": available_count,
        "deferred_count": deferred_count,
        "percentage_available": round(available_count / total if total else 0.0, 4),
        "percentage_deferred": round(deferred_count / total if total else 0.0, 4),
        "property_types": property_types,
    }


def build_engineering_roadmap() -> dict[str, List[str]]:
    roadmap: Dict[str, List[str]] = defaultdict(list)
    for property_type, lifecycle in sorted(PROPERTY_TYPE_LIFECYCLE.items()):
        available_from = LIFECYCLE_AVAILABLE_FROM[lifecycle].value
        if available_from != PipelineAvailabilityStage.PHASE_G.value:
            roadmap[available_from].append(property_type)
    return {phase: sorted(types) for phase, types in sorted(roadmap.items())}


def build_lifecycle_reporting(resolved_properties: List[dict[str, Any]]) -> dict[str, Any]:
    lifecycle_distribution: Dict[str, int] = defaultdict(int)
    status_distribution: Dict[str, int] = defaultdict(int)
    deferred_properties: List[dict[str, Any]] = []
    unknown_properties: List[dict[str, Any]] = []

    for resolved in resolved_properties:
        lifecycle_distribution[str(resolved.get("lifecycle", "UNKNOWN"))] += 1
        status = str(resolved.get("property_status", "UNKNOWN"))
        status_distribution[status] += 1
        entry = {
            "resolved_property_id": resolved.get("resolved_property_id"),
            "engineering_object_id": resolved.get("engineering_object_id"),
            "property_type": resolved.get("property_type"),
            "lifecycle": resolved.get("lifecycle"),
            "available_from_phase": resolved.get("available_from_phase"),
            "property_status": status,
            "availability_reason": resolved.get("availability_reason"),
        }
        if status == PROPERTY_STATUS_NOT_AVAILABLE_YET:
            deferred_properties.append(entry)
        elif status == PROPERTY_STATUS_UNKNOWN:
            unknown_properties.append(entry)

    available_count = status_distribution.get(PROPERTY_STATUS_RESOLVED, 0)
    available_count += status_distribution.get(PROPERTY_STATUS_CONFLICT, 0)
    available_count += status_distribution.get(PROPERTY_STATUS_UNKNOWN, 0)
    deferred_count = status_distribution.get(PROPERTY_STATUS_NOT_AVAILABLE_YET, 0)
    total = len(resolved_properties)

    return {
        "lifecycle_summary": dict(sorted(lifecycle_distribution.items())),
        "availability_summary": {
            "available": available_count,
            "deferred": deferred_count,
            "percentage_available": round(available_count / total if total else 0.0, 4),
            "percentage_deferred": round(deferred_count / total if total else 0.0, 4),
        },
        "status_distribution": dict(sorted(status_distribution.items())),
        "deferred_engineering_properties": deferred_properties[:20],
        "unknown_engineering_properties": unknown_properties[:20],
        "engineering_roadmap": build_engineering_roadmap(),
    }
