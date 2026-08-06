"""Engineering Specification Builder — Phase H.1."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from src.engineering_specifications.engineering_specification import (
    build_engineering_specification,
)
from src.engineering_specifications.specification_registry import SpecificationRegistry
from src.engineering_specifications.specification_types import (
    OBJECT_TYPE_TO_SPECIFICATION_TYPE,
    PROPERTY_TYPE_TO_SPEC_FIELD,
    SPECIFICATION_ELIGIBLE_OBJECT_TYPES,
    SPEC_UNKNOWN,
    STATUS_COMPLETE,
    STATUS_CONFLICT,
    STATUS_DEFERRED,
    STATUS_PARTIAL,
)
from src.property_resolver.property_availability import (
    PROPERTY_STATUS_NOT_AVAILABLE_YET,
    PROPERTY_STATUS_RESOLVED,
    PROPERTY_STATUS_UNKNOWN,
)
from src.property_resolver.property_resolver_types import RESOLUTION_CONFLICT


class SpecificationBuilder:
    """Assemble resolved engineering properties into engineering specifications."""

    def build(
        self,
        engineering_objects: List[dict[str, Any]],
        resolved_properties: List[dict[str, Any]],
        engineering_properties: Optional[List[dict[str, Any]]] = None,
        property_candidates: Optional[List[dict[str, Any]]] = None,
        engineering_reinforcement_contexts: Optional[List[dict[str, Any]]] = None,
        semantic_roles: Optional[List[dict[str, Any]]] = None,
    ) -> Tuple[List[dict[str, Any]], SpecificationRegistry]:
        engineering_properties = engineering_properties or []
        property_candidates = property_candidates or []
        engineering_reinforcement_contexts = engineering_reinforcement_contexts or []
        semantic_roles = semantic_roles or []

        props_by_object = self._group_properties(resolved_properties)
        property_map = {
            str(item.get("property_id")): item for item in engineering_properties
        }
        candidate_map = {
            str(item.get("candidate_id")): item for item in property_candidates
        }
        role_map = {
            str(item.get("semantic_role_id") or item.get("role_id")): item
            for item in semantic_roles
        }
        beam_by_owner = self._build_beam_lookup(engineering_reinforcement_contexts)

        registry = SpecificationRegistry()
        specifications: List[dict[str, Any]] = []

        sorted_objects = sorted(
            engineering_objects,
            key=lambda item: str(
                item.get("engineering_object_id") or item.get("object_id") or ""
            ),
        )

        for obj in sorted_objects:
            object_id = str(
                obj.get("engineering_object_id") or obj.get("object_id") or ""
            )
            object_type = str(obj.get("object_type", ""))
            registry.mark_processed(object_id, created=False)

            if object_type not in SPECIFICATION_ELIGIBLE_OBJECT_TYPES:
                continue

            object_props = props_by_object.get(object_id, [])
            if not object_props:
                continue

            spec = self._build_specification_for_object(
                registry=registry,
                obj=obj,
                object_props=object_props,
                property_map=property_map,
                candidate_map=candidate_map,
                role_map=role_map,
                beam_by_owner=beam_by_owner,
            )
            if spec:
                registry.register(spec)
                specifications.append(spec)
                registry.mark_processed(object_id, created=True)

        return specifications, registry

    @staticmethod
    def build_project_exports(
        specifications: List[dict[str, Any]],
        registry: SpecificationRegistry,
        engineering_objects: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        primary = drawing_models[0] if drawing_models else {}
        specification_registry = SpecificationRegistry.build_project_registry(
            specifications,
            engineering_objects,
            registry.processed_object_ids,
            registry.skipped_object_ids,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return {
            "engineering_specifications": specifications,
            "specification_registry": specification_registry,
        }

    @staticmethod
    def _group_properties(
        resolved_properties: List[dict[str, Any]],
    ) -> Dict[str, List[dict[str, Any]]]:
        grouped: Dict[str, List[dict[str, Any]]] = defaultdict(list)
        for item in resolved_properties:
            obj_id = str(item.get("engineering_object_id", ""))
            if obj_id:
                grouped[obj_id].append(item)
        for obj_id in grouped:
            grouped[obj_id].sort(
                key=lambda item: (
                    str(item.get("property_type", "")),
                    str(item.get("resolved_property_id", "")),
                )
            )
        return grouped

    @staticmethod
    def _build_beam_lookup(
        contexts: List[dict[str, Any]],
    ) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        for ctx in contexts:
            owner_id = str(ctx.get("reinforcement_context_id", ""))
            beam_mark = str(ctx.get("beam_mark", ""))
            if owner_id and beam_mark:
                lookup[owner_id] = beam_mark
        return lookup

    def _build_specification_for_object(
        self,
        registry: SpecificationRegistry,
        obj: dict[str, Any],
        object_props: List[dict[str, Any]],
        property_map: Dict[str, dict[str, Any]],
        candidate_map: Dict[str, dict[str, Any]],
        role_map: Dict[str, dict[str, Any]],
        beam_by_owner: Dict[str, str],
    ) -> Optional[dict[str, Any]]:
        object_id = str(obj.get("engineering_object_id") or obj.get("object_id") or "")
        object_type = str(obj.get("object_type", ""))
        owner_context_id = str(obj.get("owner_context_id", ""))
        metadata = obj.get("metadata") or {}

        reinforcement_type = self._resolve_specification_type(object_type, metadata)
        reinforcement_role = self._resolve_reinforcement_role(obj, metadata, role_map)
        beam_id = beam_by_owner.get(owner_context_id, owner_context_id)

        field_values: Dict[str, Any] = {
            "quantity": None,
            "diameter": None,
            "bar_type": None,
            "spacing": None,
            "bar_mark": None,
            "shape_code": None,
            "hook": None,
            "hook_direction": None,
            "level": None,
            "zone": None,
            "callout": None,
            "notes": None,
        }

        for prop in object_props:
            field_name = PROPERTY_TYPE_TO_SPEC_FIELD.get(
                str(prop.get("property_type", "")).upper()
            )
            if not field_name or field_name not in field_values:
                continue
            field_values[field_name] = self._spec_field_value(prop)

        property_lifecycle_summary = self._count_by_key(object_props, "lifecycle")
        property_status_summary = self._build_property_status_summary(object_props)
        resolution_summary = self._count_by_key(object_props, "resolution_strategy")
        specification_status = self._determine_specification_status(object_props)
        traceability = self._build_traceability(
            obj,
            object_props,
            property_map,
            candidate_map,
            role_map,
        )

        return build_engineering_specification(
            specification_id=registry.next_id(),
            engineering_object_id=object_id,
            beam_id=beam_id,
            reinforcement_role=reinforcement_role,
            reinforcement_type=reinforcement_type,
            specification_status=specification_status,
            resolved_property_ids=[
                str(item.get("resolved_property_id"))
                for item in object_props
                if item.get("resolved_property_id")
            ],
            resolved_properties=list(object_props),
            property_lifecycle_summary=property_lifecycle_summary,
            property_status_summary=property_status_summary,
            resolution_summary=resolution_summary,
            traceability=traceability,
            **field_values,
        )

    @staticmethod
    def _resolve_specification_type(object_type: str, metadata: dict[str, Any]) -> str:
        explicit = str(
            metadata.get("specification_type")
            or metadata.get("reinforcement_subtype")
            or ""
        ).upper()
        if explicit in OBJECT_TYPE_TO_SPECIFICATION_TYPE.values():
            return explicit
        return OBJECT_TYPE_TO_SPECIFICATION_TYPE.get(object_type, SPEC_UNKNOWN)

    @staticmethod
    def _resolve_reinforcement_role(
        obj: dict[str, Any],
        metadata: dict[str, Any],
        role_map: Dict[str, dict[str, Any]],
    ) -> str:
        role_id = str(obj.get("source_role_id", ""))
        role = role_map.get(role_id, {})
        return str(
            role.get("role_type")
            or role.get("semantic_role_type")
            or metadata.get("semantic_role_type")
            or obj.get("object_type", "")
        )

    @staticmethod
    def _spec_field_value(prop: dict[str, Any]) -> Any:
        status = str(prop.get("property_status", ""))
        if status == PROPERTY_STATUS_NOT_AVAILABLE_YET:
            return None
        if status == PROPERTY_STATUS_UNKNOWN:
            return None
        return prop.get("resolved_value")

    @staticmethod
    def _count_by_key(items: List[dict[str, Any]], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in items:
            value = str(item.get(key, "") or "UNKNOWN")
            counts[value] = counts.get(value, 0) + 1
        return counts

    @staticmethod
    def _build_property_status_summary(object_props: List[dict[str, Any]]) -> Dict[str, int]:
        summary = {
            "resolved": 0,
            "deferred": 0,
            "conflict": 0,
            "unknown": 0,
        }
        for prop in object_props:
            status = str(prop.get("property_status", ""))
            strategy = str(prop.get("resolution_strategy", ""))
            if strategy == RESOLUTION_CONFLICT or status == "CONFLICT":
                summary["conflict"] += 1
            elif status == PROPERTY_STATUS_NOT_AVAILABLE_YET:
                summary["deferred"] += 1
            elif status == PROPERTY_STATUS_UNKNOWN:
                summary["unknown"] += 1
            elif status == PROPERTY_STATUS_RESOLVED:
                summary["resolved"] += 1
        return summary

    @staticmethod
    def _determine_specification_status(object_props: List[dict[str, Any]]) -> str:
        if any(
            str(item.get("resolution_strategy", "")) == RESOLUTION_CONFLICT
            or str(item.get("property_status", "")) == "CONFLICT"
            for item in object_props
        ):
            return STATUS_CONFLICT

        if any(
            str(item.get("property_status", "")) == PROPERTY_STATUS_UNKNOWN
            for item in object_props
        ):
            return STATUS_PARTIAL

        resolved_count = sum(
            1
            for item in object_props
            if str(item.get("property_status", "")) == PROPERTY_STATUS_RESOLVED
        )
        deferred_count = sum(
            1
            for item in object_props
            if str(item.get("property_status", "")) == PROPERTY_STATUS_NOT_AVAILABLE_YET
        )

        if resolved_count == 0 and deferred_count > 0:
            return STATUS_DEFERRED

        return STATUS_COMPLETE

    @staticmethod
    def _build_traceability(
        obj: dict[str, Any],
        object_props: List[dict[str, Any]],
        property_map: Dict[str, dict[str, Any]],
        candidate_map: Dict[str, dict[str, Any]],
        role_map: Dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        role_id = str(obj.get("source_role_id", ""))
        role = role_map.get(role_id, {})
        property_chains: List[dict[str, Any]] = []

        for prop in object_props:
            property_id = str(prop.get("selected_property_id", ""))
            candidate_id = str(prop.get("selected_candidate_id", ""))
            engineering_property = property_map.get(property_id, {})
            property_candidate = candidate_map.get(candidate_id, {})

            property_chains.append(
                {
                    "resolved_property_id": prop.get("resolved_property_id"),
                    "property_type": prop.get("property_type"),
                    "property_status": prop.get("property_status"),
                    "lifecycle": prop.get("lifecycle"),
                    "resolution_strategy": prop.get("resolution_strategy"),
                    "engineering_property": {
                        "property_id": engineering_property.get("property_id"),
                        "candidate_id": engineering_property.get("candidate_id"),
                        "source_entity_id": engineering_property.get("source_entity_id"),
                        "source_role_id": engineering_property.get("source_role_id"),
                        "owner_context_id": engineering_property.get("owner_context_id"),
                    },
                    "property_candidate": {
                        "candidate_id": property_candidate.get("candidate_id"),
                        "source_entity_id": property_candidate.get("source_entity_id"),
                        "source_role_id": property_candidate.get("source_role_id"),
                        "candidate_source_type": property_candidate.get(
                            "candidate_source_type"
                        ),
                    },
                    "semantic_role": {
                        "role_id": role.get("semantic_role_id") or role_id,
                        "semantic_role_type": role.get("role_type")
                        or role.get("semantic_role_type"),
                        "source_entity_id": (
                            (role.get("geometry_asset_ids") or [None])[0]
                            if role.get("geometry_asset_ids")
                            else role.get("source_entity_id")
                        ),
                    },
                    "drawing_entity_id": prop.get("selected_source_entity")
                    or engineering_property.get("source_entity_id")
                    or property_candidate.get("source_entity_id"),
                }
            )

        return {
            "engineering_object_id": obj.get("engineering_object_id") or obj.get("object_id"),
            "source_role_id": role_id,
            "semantic_role_type": role.get("role_type") or role.get("semantic_role_type"),
            "drawing_entity_id": (
                (role.get("geometry_asset_ids") or [None])[0]
                if role.get("geometry_asset_ids")
                else role.get("source_entity_id")
            ),
            "property_chains": property_chains,
            "lineage": [
                "Engineering Specification",
                "Resolved Property",
                "Engineering Property",
                "Property Candidate",
                "Semantic Role",
                "Drawing Entity",
            ],
        }
