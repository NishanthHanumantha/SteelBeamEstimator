"""Engineering Reinforcement Context — permanent engineering workspace per matched beam."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

PREFIX_ERC = "ERC"

ENGINEERING_STATUS_OWNERSHIP_READY = "OWNERSHIP_READY"
OWNERSHIP_STATUS_RESOLVED = "RESOLVED"

OWNER_TYPE_ERC = "ENGINEERING_REINFORCEMENT_CONTEXT"
OWNERSHIP_SOURCE_BEAM_MATCH = "BEAM_MATCH"

FUTURE_PLACEHOLDERS: dict[str, None] = {
    "bars": None,
    "stirrups": None,
    "development_length": None,
    "anchorage": None,
    "lap_splices": None,
    "quantities": None,
}

ENGINEERING_RESULTS_PLACEHOLDERS: dict[str, None] = {
    "parsed_reinforcement": None,
    "bar_objects": None,
    "stirrup_objects": None,
    "development_length": None,
    "lap_splices": None,
    "anchorage_objects": None,
    "cover_adjustments": None,
    "steel_quantities": None,
    "concrete_quantities": None,
    "boq": None,
}

PREFIX_ENGINEERING_RESULTS = "ENGINEERING_RESULTS"


def format_engineering_results_id(beam_mark: str) -> str:
    return f"{PREFIX_ENGINEERING_RESULTS}::{beam_mark.upper()}"


def engineering_results_block() -> dict[str, Any]:
    return dict(ENGINEERING_RESULTS_PLACEHOLDERS)


def format_erc_id(beam_mark: str) -> str:
    return f"{PREFIX_ERC}::{beam_mark.upper()}"


def ownership_block(erc_id: str) -> dict[str, Any]:
    return {
        "owner_type": OWNER_TYPE_ERC,
        "owner_id": erc_id,
        "ownership_source": OWNERSHIP_SOURCE_BEAM_MATCH,
        "ownership_confidence": 1.0,
    }


def ownership_resolver_applied(model: dict[str, Any]) -> bool:
    if model.get("engineering_reinforcement_contexts"):
        return True
    return bool(model.get("workspace_manager", {}).get("ownership_resolver_complete"))


@dataclass
class EngineeringReinforcementContext:
    """Engineering workspace for one matched beam's reinforcement detail."""

    reinforcement_context_id: str
    beam_context_id: str
    beam_match_id: str
    beam_mark: str
    drawing_set_id: str
    drawing_id: str
    project_id: str
    floor_id: str
    detail_identity_id: str
    detail_context_id: str
    engineering_status: str = ENGINEERING_STATUS_OWNERSHIP_READY
    ownership_status: str = OWNERSHIP_STATUS_RESOLVED
    owned_views: List[str] = field(default_factory=list)
    owned_geometry: List[str] = field(default_factory=list)
    owned_text: List[str] = field(default_factory=list)
    owned_leaders: List[str] = field(default_factory=list)
    owned_blocks: List[str] = field(default_factory=list)
    engineering_assets: Optional[Dict[str, Any]] = None
    engineering_results: Optional[Dict[str, Any]] = None
    lifecycle: Optional[Dict[str, Any]] = None
    engineering_objects: Optional[Dict[str, Any]] = None
    semantic_role_registry: Optional[Dict[str, Any]] = None
    semantic_roles: Optional[List[str]] = None
    semantic_relationship_registry: Optional[Dict[str, Any]] = None
    semantic_relationships: Optional[List[str]] = None
    future: Dict[str, Any] = field(default_factory=lambda: dict(FUTURE_PLACEHOLDERS))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "reinforcement_context_id": self.reinforcement_context_id,
            "beam_context_id": self.beam_context_id,
            "beam_match_id": self.beam_match_id,
            "beam_mark": self.beam_mark,
            "drawing_set_id": self.drawing_set_id,
            "drawing_id": self.drawing_id,
            "project_id": self.project_id,
            "floor_id": self.floor_id,
            "engineering_status": self.engineering_status,
            "ownership_status": self.ownership_status,
            "detail_identity_id": self.detail_identity_id,
            "detail_context_id": self.detail_context_id,
            "owned_views": list(self.owned_views),
            "owned_geometry": list(self.owned_geometry),
            "owned_text": list(self.owned_text),
            "owned_leaders": list(self.owned_leaders),
            "owned_blocks": list(self.owned_blocks),
            "future": dict(self.future),
            "metadata": dict(self.metadata),
        }
        if self.engineering_assets is not None:
            result["engineering_assets"] = dict(self.engineering_assets)
        if self.engineering_results is not None:
            result["engineering_results"] = dict(self.engineering_results)
        if self.lifecycle is not None:
            result["lifecycle"] = dict(self.lifecycle)
        if self.engineering_objects is not None:
            result["engineering_objects"] = dict(self.engineering_objects)
        if self.semantic_role_registry is not None:
            result["semantic_role_registry"] = dict(self.semantic_role_registry)
        if self.semantic_roles is not None:
            result["semantic_roles"] = list(self.semantic_roles)
        if self.semantic_relationship_registry is not None:
            result["semantic_relationship_registry"] = dict(self.semantic_relationship_registry)
        if self.semantic_relationships is not None:
            result["semantic_relationships"] = list(self.semantic_relationships)
        return result
