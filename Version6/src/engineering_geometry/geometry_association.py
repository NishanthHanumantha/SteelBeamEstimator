"""Engineering Geometry Association model — Phase H.2."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.engineering_geometry.geometry_types import CREATED_PHASE, REFERENCE_CONTRACT_VERSION


def geometry_associations_applied(model: dict[str, Any]) -> bool:
    registry = model.get("geometry_registry", {})
    if registry.get("phase") == "Phase H.2" and registry.get("association_count", 0) >= 0:
        return True
    if model.get("geometry_associations") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("geometry_association_complete"))


def build_engineering_geometry_association(
    association_id: str,
    specification_id: str,
    engineering_object_id: str,
    beam_id: str,
    beam_geometry_id: str,
    beam_section_id: str,
    clear_span_id: str,
    effective_span_id: str,
    stationing_id: str,
    coordinate_system_id: str,
    support_start_id: str,
    support_end_id: str,
    knowledge_graph_node_id: str,
    association_status: str,
    association_reason: str,
    association_confidence: float,
    traceability: dict[str, Any],
    reference_contract_version: str = REFERENCE_CONTRACT_VERSION,
    created_timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Build an immutable geometry association containing IDs only."""
    return {
        "association_id": association_id,
        "specification_id": specification_id,
        "engineering_object_id": engineering_object_id,
        "beam_id": beam_id,
        "beam_geometry_id": beam_geometry_id,
        "beam_section_id": beam_section_id,
        "clear_span_id": clear_span_id,
        "effective_span_id": effective_span_id,
        "stationing_id": stationing_id,
        "coordinate_system_id": coordinate_system_id,
        "support_start_id": support_start_id,
        "support_end_id": support_end_id,
        "knowledge_graph_node_id": knowledge_graph_node_id,
        "association_status": association_status,
        "association_reason": association_reason,
        "association_confidence": round(association_confidence, 4),
        "reference_contract_version": reference_contract_version,
        "traceability": traceability,
        "created_timestamp": created_timestamp
        or datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "created_phase": CREATED_PHASE,
        },
    }
