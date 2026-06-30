"""Engineering Asset Registry — single entry point for owned reinforcement assets."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.reinforcement.engineering_reinforcement_context import (
    ENGINEERING_RESULTS_PLACEHOLDERS,
    engineering_results_block,
)
from src.reinforcement.engineering_reinforcement_state_machine import (
    EngineeringReinforcementLifecycle,
    STATE_OWNERSHIP_READY,
)

PREFIX_ASSET_REGISTRY = "ASSET_REGISTRY"
REGISTRY_STATUS_READY = "READY"


def format_asset_registry_id(beam_mark: str) -> str:
    return f"{PREFIX_ASSET_REGISTRY}::{beam_mark.upper()}"


def engineering_assets_applied(model: dict[str, Any]) -> bool:
    if model.get("engineering_asset_registry"):
        return True
    contexts = model.get("engineering_reinforcement_contexts", [])
    if contexts and contexts[0].get("engineering_assets"):
        return True
    return bool(
        model.get("workspace_manager", {}).get("engineering_asset_registry_complete")
    )


class EngineeringAssetRegistry:
    """Reference owned asset IDs per ERC — no geometry duplication."""

    @staticmethod
    def build_from_erc(erc: dict[str, Any]) -> dict[str, Any]:
        beam_mark = str(erc.get("beam_mark", ""))
        return {
            "asset_registry_id": format_asset_registry_id(beam_mark),
            "beam_match_id": erc.get("beam_match_id"),
            "reinforcement_context_id": erc.get("reinforcement_context_id"),
            "views": list(erc.get("owned_views", [])),
            "geometry": list(erc.get("owned_geometry", [])),
            "text": list(erc.get("owned_text", [])),
            "leaders": list(erc.get("owned_leaders", [])),
            "blocks": list(erc.get("owned_blocks", [])),
            "status": REGISTRY_STATUS_READY,
        }

    @staticmethod
    def build_engineering_assets_section(registry: dict[str, Any]) -> dict[str, Any]:
        return {
            "registry_id": registry.get("asset_registry_id"),
            "views": list(registry.get("views", [])),
            "geometry": list(registry.get("geometry", [])),
            "text": list(registry.get("text", [])),
            "leaders": list(registry.get("leaders", [])),
            "blocks": list(registry.get("blocks", [])),
        }

    @staticmethod
    def enrich_erc(erc: dict[str, Any]) -> Tuple[dict[str, Any], dict[str, Any]]:
        registry = EngineeringAssetRegistry.build_from_erc(erc)
        enriched = dict(erc)
        enriched["engineering_assets"] = EngineeringAssetRegistry.build_engineering_assets_section(
            registry
        )
        enriched["engineering_results"] = engineering_results_block()
        enriched["lifecycle"] = EngineeringReinforcementLifecycle.initial(
            current_state=STATE_OWNERSHIP_READY
        )
        return enriched, registry

    @staticmethod
    def enrich_contexts(
        contexts: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
        enriched: List[dict[str, Any]] = []
        registries: List[dict[str, Any]] = []
        for erc in contexts:
            e, reg = EngineeringAssetRegistry.enrich_erc(erc)
            enriched.append(e)
            registries.append(reg)
        return enriched, registries

    @staticmethod
    def build_project_registry(
        registries: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
        project_id: str = "",
    ) -> dict[str, Any]:
        return {
            "namespace": "ENGINEERING_ASSET_REGISTRY",
            "phase": "Phase G.4.1",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "project_id": project_id,
            "registry_count": len(registries),
            "registries": list(registries),
        }

    @staticmethod
    def build_summary(registries: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase G.4.1",
            "registry_count": len(registries),
            "view_count": sum(len(r.get("views", [])) for r in registries),
            "geometry_count": sum(len(r.get("geometry", [])) for r in registries),
            "text_count": sum(len(r.get("text", [])) for r in registries),
            "leader_count": sum(len(r.get("leaders", [])) for r in registries),
            "block_count": sum(len(r.get("blocks", [])) for r in registries),
            "status": REGISTRY_STATUS_READY,
        }

    @staticmethod
    def build_engineering_result_summary() -> dict[str, Any]:
        return {
            "phase": "Phase G.4.1",
            **{key: None for key in ENGINEERING_RESULTS_PLACEHOLDERS},
        }
