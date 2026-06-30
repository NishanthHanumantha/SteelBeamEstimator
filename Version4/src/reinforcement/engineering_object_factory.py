"""Engineering Object Factory — create placeholder objects for G.5+ parsers."""

from __future__ import annotations

from typing import Any, Optional

from src.reinforcement.engineering_object import (
    OBJECT_TYPE_ANCHORAGE,
    OBJECT_TYPE_ASSEMBLY,
    OBJECT_TYPE_BAR,
    OBJECT_TYPE_COVER,
    OBJECT_TYPE_DEVELOPMENT_LENGTH,
    OBJECT_TYPE_HOOK,
    OBJECT_TYPE_LAP_SPLICE,
    OBJECT_TYPE_STIRRUP,
    OBJECT_TYPE_ZONE,
    build_engineering_object,
    build_instantiated_engineering_object,
    empty_asset_references,
)
from src.reinforcement.engineering_object_lifecycle import (
    STATE_CREATED,
    STATE_PLACEHOLDER_CREATED,
)
from src.reinforcement.engineering_object_registry import EngineeringObjectRegistry


class EngineeringObjectFactory:
    """Factory for engineering objects — placeholders only until G.5."""

    def __init__(self, registry: Optional[EngineeringObjectRegistry] = None) -> None:
        self._registry = registry or EngineeringObjectRegistry()

    @property
    def registry(self) -> EngineeringObjectRegistry:
        return self._registry

    def create_instantiated(
        self,
        object_type: str,
        owner_context_id: str,
        owner_registry_id: str,
        asset_references: Optional[dict[str, list[str]]] = None,
        classification_source: str = "INFERRED",
        confidence: float = 0.0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        obj = build_instantiated_engineering_object(
            engineering_object_id=self._registry.next_id(),
            object_type=object_type,
            owner_context_id=owner_context_id,
            owner_registry_id=owner_registry_id,
            asset_references=asset_references or empty_asset_references(),
            classification_source=classification_source,
            confidence=confidence,
            lifecycle=STATE_CREATED,
            metadata=metadata,
        )
        self._registry.register(obj)
        return obj

    def _create(
        self,
        object_type: str,
        owner_context_id: str,
        owner_registry_id: str,
        object_subtype: Optional[str] = None,
    ) -> dict[str, Any]:
        obj = build_engineering_object(
            engineering_object_id=self._registry.next_id(),
            object_type=object_type,
            object_subtype=object_subtype,
            owner_context_id=owner_context_id,
            owner_registry_id=owner_registry_id,
            lifecycle=STATE_PLACEHOLDER_CREATED,
        )
        self._registry.register(obj)
        return obj

    def create_bar(
        self,
        owner_context_id: str,
        owner_registry_id: str,
        object_subtype: Optional[str] = None,
    ) -> dict[str, Any]:
        return self._create(OBJECT_TYPE_BAR, owner_context_id, owner_registry_id, object_subtype)

    def create_stirrup(
        self,
        owner_context_id: str,
        owner_registry_id: str,
    ) -> dict[str, Any]:
        return self._create(OBJECT_TYPE_STIRRUP, owner_context_id, owner_registry_id)

    def create_hook(
        self,
        owner_context_id: str,
        owner_registry_id: str,
    ) -> dict[str, Any]:
        return self._create(OBJECT_TYPE_HOOK, owner_context_id, owner_registry_id)

    def create_lap_splice(
        self,
        owner_context_id: str,
        owner_registry_id: str,
    ) -> dict[str, Any]:
        return self._create(OBJECT_TYPE_LAP_SPLICE, owner_context_id, owner_registry_id)

    def create_development_length(
        self,
        owner_context_id: str,
        owner_registry_id: str,
    ) -> dict[str, Any]:
        return self._create(
            OBJECT_TYPE_DEVELOPMENT_LENGTH, owner_context_id, owner_registry_id
        )

    def create_anchorage(
        self,
        owner_context_id: str,
        owner_registry_id: str,
    ) -> dict[str, Any]:
        return self._create(OBJECT_TYPE_ANCHORAGE, owner_context_id, owner_registry_id)

    def create_cover_region(
        self,
        owner_context_id: str,
        owner_registry_id: str,
    ) -> dict[str, Any]:
        return self._create(OBJECT_TYPE_COVER, owner_context_id, owner_registry_id)

    def create_steel_assembly(
        self,
        owner_context_id: str,
        owner_registry_id: str,
    ) -> dict[str, Any]:
        return self._create(OBJECT_TYPE_ASSEMBLY, owner_context_id, owner_registry_id)

    def create_reinforcement_zone(
        self,
        owner_context_id: str,
        owner_registry_id: str,
    ) -> dict[str, Any]:
        return self._create(OBJECT_TYPE_ZONE, owner_context_id, owner_registry_id)

    # Future subtype convenience methods (architecture only)
    def create_longitudinal_bar(
        self, owner_context_id: str, owner_registry_id: str
    ) -> dict[str, Any]:
        return self.create_bar(owner_context_id, owner_registry_id, "LONGITUDINAL")

    def create_top_bar(self, owner_context_id: str, owner_registry_id: str) -> dict[str, Any]:
        return self.create_bar(owner_context_id, owner_registry_id, "TOP")

    def create_bottom_bar(self, owner_context_id: str, owner_registry_id: str) -> dict[str, Any]:
        return self.create_bar(owner_context_id, owner_registry_id, "BOTTOM")

    def create_curtailment_bar(
        self, owner_context_id: str, owner_registry_id: str
    ) -> dict[str, Any]:
        return self.create_bar(owner_context_id, owner_registry_id, "CURTAILMENT")

    def create_bent_bar(self, owner_context_id: str, owner_registry_id: str) -> dict[str, Any]:
        return self.create_bar(owner_context_id, owner_registry_id, "BENT")

    def create_cranked_bar(self, owner_context_id: str, owner_registry_id: str) -> dict[str, Any]:
        return self.create_bar(owner_context_id, owner_registry_id, "CRANKED")

    def create_side_bar(self, owner_context_id: str, owner_registry_id: str) -> dict[str, Any]:
        return self.create_bar(owner_context_id, owner_registry_id, "SIDE")
