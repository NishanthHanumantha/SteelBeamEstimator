"""Core property resolution engine — Phase G.5.3.2."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from src.property_resolver.property_conflict_detector import PropertyConflictDetector
from src.property_resolver.property_resolution_registry import PropertyResolutionRegistry
from src.property_resolver.resolution_strategy import apply_resolution_strategy
from src.property_resolver.resolved_engineering_property import build_resolved_engineering_property


class PropertyResolutionEngine:
    """Group engineering properties and resolve one value per type per object."""

    @staticmethod
    def group_properties(
        properties: List[dict[str, Any]],
    ) -> Dict[Tuple[str, str], List[dict[str, Any]]]:
        grouped: Dict[Tuple[str, str], List[dict[str, Any]]] = defaultdict(list)
        for prop in properties:
            obj_id = str(prop.get("engineering_object_id", ""))
            ptype = str(prop.get("property_type", "UNKNOWN"))
            grouped[(obj_id, ptype)].append(prop)
        return dict(grouped)

    def resolve(
        self,
        properties: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], PropertyResolutionRegistry, List[dict[str, Any]]]:
        registry = PropertyResolutionRegistry()
        grouped = self.group_properties(properties)
        conflicts = PropertyConflictDetector.detect_all_conflicts(grouped)
        resolved_properties: List[dict[str, Any]] = []

        for (obj_id, ptype), group in sorted(grouped.items()):
            outcome = apply_resolution_strategy(group)
            selected = outcome.selected or {}
            parser_versions = sorted(
                {
                    str(p.get("parser_version", ""))
                    for p in group
                    if p.get("parser_version")
                }
            )
            resolved = build_resolved_engineering_property(
                resolved_property_id="",
                engineering_object_id=obj_id,
                property_type=ptype,
                resolved_value=outcome.resolved_value,
                unit=outcome.unit,
                selected_property_id=str(selected.get("property_id", "")),
                selected_candidate_id=str(selected.get("candidate_id", "")),
                selected_source_entity=str(selected.get("source_entity_id", "")),
                resolution_strategy=outcome.strategy,
                resolution_confidence=outcome.resolution_confidence,
                candidate_count=len(group),
                conflicting_values=outcome.conflicting_values,
                alternative_property_ids=outcome.alternative_property_ids,
                parser_versions=parser_versions,
                resolution_notes=outcome.resolution_notes,
            )
            registry.register(resolved)
            resolved_properties.append(resolved)

        return resolved_properties, registry, conflicts
