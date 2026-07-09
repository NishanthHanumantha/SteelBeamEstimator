"""Property resolution reporting consistency — Phase G.5.3.2 / lifecycle G.5.3.4."""

from __future__ import annotations

from typing import Any

from src.property_resolver.property_availability import build_lifecycle_reporting
from src.property_resolver.property_resolution_confidence_reporting import (
    PropertyResolutionConfidenceReporting,
)
from src.property_resolver.property_resolution_summary import PropertyResolutionSummary


class PropertyResolutionReporting:
    """Single source of truth for property resolution validation reporting."""

    @staticmethod
    def apply_validation(model: dict[str, Any], validation: dict[str, Any]) -> None:
        model["property_resolution_validation"] = validation
        resolved = model.get("resolved_engineering_properties", [])
        model["property_resolution_summary"] = PropertyResolutionSummary.build(
            model.get("engineering_objects", []),
            model.get("engineering_properties", []),
            resolved,
            model.get("property_conflicts", []),
            model.get("property_resolution_registry", {}),
            validation,
        )
        model["property_resolution_confidence_reporting"] = (
            PropertyResolutionConfidenceReporting.build(resolved)
        )
        model["property_lifecycle_reporting"] = build_lifecycle_reporting(resolved)
