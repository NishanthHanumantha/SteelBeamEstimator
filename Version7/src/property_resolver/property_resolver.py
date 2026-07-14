"""Main Engineering Property Resolver — Phase G.5.3.2 / lifecycle G.5.3.4."""

from __future__ import annotations

from typing import Any, List

from src.property_resolver.property_availability import (
    CURRENT_PIPELINE_PHASE,
    apply_lifecycle_to_resolved_properties,
    build_property_availability_report,
)
from src.property_resolver.property_resolution_engine import PropertyResolutionEngine
from src.property_resolver.property_resolution_registry import PropertyResolutionRegistry


def property_resolver_applied(model: dict[str, Any]) -> bool:
    registry = model.get("property_resolution_registry", {})
    if registry.get("phase") in ("Phase G.5.3.2", "Phase G.5.3.3", "Phase G.5.3.4"):
        return True
    if model.get("resolved_engineering_properties") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("property_resolver_complete"))


class PropertyResolver:
    """Resolve duplicate engineering properties into single authoritative values."""

    def __init__(self) -> None:
        self._engine = PropertyResolutionEngine()

    def build(
        self,
        properties: List[dict[str, Any]],
        current_phase: str = CURRENT_PIPELINE_PHASE,
    ) -> tuple[List[dict[str, Any]], PropertyResolutionRegistry, List[dict[str, Any]]]:
        resolved, registry, conflicts = self._engine.resolve(properties)
        apply_lifecycle_to_resolved_properties(resolved, current_phase=current_phase)
        return resolved, registry, conflicts

    @staticmethod
    def build_project_exports(
        properties: List[dict[str, Any]],
        resolved_properties: List[dict[str, Any]],
        registry: PropertyResolutionRegistry,
        conflicts: List[dict[str, Any]],
        engineering_objects: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
        current_phase: str = CURRENT_PIPELINE_PHASE,
    ) -> dict[str, Any]:
        primary = drawing_models[0] if drawing_models else {}
        resolution_registry = PropertyResolutionRegistry.build_project_registry(
            resolved_properties,
            properties,
            engineering_objects,
            conflicts,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return {
            "resolved_engineering_properties": resolved_properties,
            "property_resolution_registry": resolution_registry,
            "property_conflicts": conflicts,
            "property_availability_report": build_property_availability_report(
                resolved_properties,
                current_phase=current_phase,
            ),
        }
