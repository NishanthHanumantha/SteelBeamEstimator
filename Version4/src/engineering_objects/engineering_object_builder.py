"""Graph-based Engineering Object builder — Phase G.5.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.engineering_objects.engineering_object import (
    build_engineering_object,
    engineering_object_registry_section,
)
from src.engineering_objects.engineering_object_graph import EngineeringObjectGraph
from src.engineering_objects.engineering_object_registry import EngineeringObjectRegistry
from src.engineering_objects.engineering_object_summary import EngineeringObjectSummary
from src.engineering_objects.engineering_object_types import (
    CLASSIFICATION_SOURCE_SEMANTIC_GRAPH,
    CLASSIFICATION_SOURCE_SEMANTIC_ROLE,
    ENGINEERING_STATUS_OBJECT_CREATED,
    ENGINEERING_STATUS_UNKNOWN_OBJECT,
    LIFECYCLE_OBJECT_CREATED,
    OBJECT_BEAM_IDENTIFIER,
    OBJECT_BOTTOM_REINFORCEMENT,
    OBJECT_DIMENSION,
    OBJECT_GENERAL_NOTE,
    OBJECT_LEADER,
    OBJECT_SECTION_MARKER,
    OBJECT_SIDE_FACE_REINFORCEMENT,
    OBJECT_STIRRUP,
    OBJECT_TEXT_NOTE,
    OBJECT_TOP_REINFORCEMENT,
    OBJECT_UNKNOWN,
)
from src.engineering_objects.engineering_object_validator import EngineeringObjectG51Validator
from src.reinforcement.engineering_semantic_relationship_types import (
    REL_ANNOTATES,
    REL_CONNECTED_TO,
    REL_CONTINUES_TO,
    REL_PART_OF_GROUP,
)
from src.reinforcement.engineering_semantic_role_types import (
    ROLE_ANCHORAGE,
    ROLE_BEAM_IDENTIFIER,
    ROLE_CALLOUT,
    ROLE_DEVELOPMENT_LENGTH,
    ROLE_DIMENSION,
    ROLE_GENERAL_NOTE,
    ROLE_HOOK,
    ROLE_LEADER,
    ROLE_LONGITUDINAL,
    ROLE_SECTION_IDENTIFIER,
    ROLE_SIDE_FACE,
    ROLE_SPACER,
    ROLE_TRANSVERSE,
    ROLE_UNKNOWN,
)


@dataclass
class RoleGraphIndex:
    """Per-ERC semantic role relationship index."""

    role_id: str
    incoming: List[dict[str, Any]] = field(default_factory=list)
    outgoing: List[dict[str, Any]] = field(default_factory=list)

    @property
    def incoming_ids(self) -> List[str]:
        return [r["relationship_id"] for r in self.incoming if r.get("relationship_id")]

    @property
    def outgoing_ids(self) -> List[str]:
        return [r["relationship_id"] for r in self.outgoing if r.get("relationship_id")]

    def connected_role_ids(self) -> List[str]:
        ids: Set[str] = set()
        for rel in self.incoming + self.outgoing:
            for key in ("source_role_id", "target_role_id"):
                rid = rel.get(key)
                if rid and rid != self.role_id:
                    ids.add(rid)
        return sorted(ids)

    def annotation_role_ids(self) -> List[str]:
        return sorted(
            {
                rel.get("source_role_id", "")
                for rel in self.incoming
                if rel.get("relationship_type") == REL_ANNOTATES
                and rel.get("source_role_id")
            }
        )

    def parent_group_role_ids(self) -> List[str]:
        return sorted(
            {
                rel.get("source_role_id", "")
                for rel in self.incoming
                if rel.get("relationship_type") == REL_PART_OF_GROUP
                and rel.get("source_role_id")
            }
        )

    def child_group_role_ids(self) -> List[str]:
        return sorted(
            {
                rel.get("target_role_id", "")
                for rel in self.outgoing
                if rel.get("relationship_type") == REL_PART_OF_GROUP
                and rel.get("target_role_id")
            }
        )


class EngineeringObjectBuilder:
    """Instantiate engineering objects from semantic roles and relationships."""

    def __init__(self, unknown_threshold: float = 0.15) -> None:
        self._unknown_threshold = unknown_threshold

    def build(
        self,
        contexts: List[dict[str, Any]],
        roles: List[dict[str, Any]],
        relationships: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], EngineeringObjectRegistry, Dict[str, str]]:
        registry = EngineeringObjectRegistry()
        roles_by_id = {r["semantic_role_id"]: r for r in roles}
        role_to_object: Dict[str, str] = {}
        enriched: List[dict[str, Any]] = []

        for erc in contexts:
            erc_id = str(erc.get("reinforcement_context_id", ""))
            erc_roles = [
                roles_by_id[rid]
                for rid in erc.get("semantic_roles", [])
                if rid in roles_by_id
            ]
            erc_rels = [
                r
                for r in relationships
                if r.get("owner_context_id") == erc_id
            ]
            graph_index = self._build_graph_index(erc_roles, erc_rels)
            longitudinal_map = self._assign_longitudinal_types(erc_roles, graph_index)

            object_ids: List[str] = []

            for role in erc_roles:
                role_id = role["semantic_role_id"]
                idx = graph_index.get(role_id, RoleGraphIndex(role_id=role_id))
                object_type = self._resolve_object_type(role, longitudinal_map)
                status = (
                    ENGINEERING_STATUS_OBJECT_CREATED
                    if object_type != OBJECT_UNKNOWN
                    else ENGINEERING_STATUS_UNKNOWN_OBJECT
                )
                confidence = self._compute_confidence(role, idx)
                rel_ids = sorted(set(idx.incoming_ids + idx.outgoing_ids))

                obj = build_engineering_object(
                    object_id=registry.next_id(),
                    object_type=object_type,
                    owner_context_id=erc_id,
                    source_role_id=role_id,
                    detail_context_id=str(erc.get("detail_context_id", "")),
                    drawing_id=str(erc.get("drawing_id", "")),
                    drawing_set_id=str(erc.get("drawing_set_id", "")),
                    source_relationship_ids=rel_ids,
                    classification_source=(
                        CLASSIFICATION_SOURCE_SEMANTIC_GRAPH
                        if rel_ids
                        else CLASSIFICATION_SOURCE_SEMANTIC_ROLE
                    ),
                    confidence=confidence,
                    engineering_status=status,
                    lifecycle=LIFECYCLE_OBJECT_CREATED,
                    metadata={
                        "semantic_role_type": role.get("role_type"),
                        "engineering_priority": role.get("engineering_priority"),
                        "connected_role_ids": idx.connected_role_ids(),
                    },
                    incoming_relationship_ids=idx.incoming_ids,
                    outgoing_relationship_ids=idx.outgoing_ids,
                    parent_group_ids=idx.parent_group_role_ids(),
                    child_group_ids=idx.child_group_role_ids(),
                    annotation_ids=idx.annotation_role_ids(),
                )
                obj_id = registry.register(obj)
                role_to_object[role_id] = obj_id
                object_ids.append(obj_id)

            self._link_connected_objects(registry, object_ids, role_to_object, graph_index)

            enriched_ctx = dict(erc)
            enriched_ctx["engineering_object_registry"] = engineering_object_registry_section(
                str(erc.get("beam_mark", "")),
                object_ids=object_ids,
            )
            enriched_ctx["engineering_objects"] = list(object_ids)
            enriched.append(enriched_ctx)

        return enriched, registry, role_to_object

    @staticmethod
    def build_project_exports(
        contexts: List[dict[str, Any]],
        registry: EngineeringObjectRegistry,
        role_to_object: Dict[str, str],
        relationships: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
        unknown_threshold: float = 0.15,
    ) -> dict[str, Any]:
        objects = registry.all_objects()
        primary = drawing_models[0] if drawing_models else {}
        object_registry = EngineeringObjectRegistry.build_project_registry(
            contexts,
            objects,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        object_graph = EngineeringObjectGraph.build(
            objects,
            relationships,
            role_to_object,
            project_id=project_id,
        )
        validation = EngineeringObjectG51Validator(unknown_threshold).validate(
            {
                "engineering_reinforcement_contexts": contexts,
                "engineering_object_registry": object_registry,
                "engineering_objects": objects,
                "engineering_object_graph": object_graph,
            }
        )
        summary = EngineeringObjectSummary.build(
            contexts,
            objects,
            object_registry,
            object_graph,
            validation,
            unknown_threshold=unknown_threshold,
        )
        return {
            "engineering_objects": objects,
            "engineering_object_registry": object_registry,
            "engineering_object_graph": object_graph,
            "engineering_object_summary": summary,
            "engineering_object_instantiation_validation": validation,
        }

    @staticmethod
    def _build_graph_index(
        erc_roles: List[dict[str, Any]],
        erc_rels: List[dict[str, Any]],
    ) -> Dict[str, RoleGraphIndex]:
        role_ids = {r["semantic_role_id"] for r in erc_roles}
        index: Dict[str, RoleGraphIndex] = {
            rid: RoleGraphIndex(role_id=rid) for rid in role_ids
        }
        for rel in erc_rels:
            src = rel.get("source_role_id")
            tgt = rel.get("target_role_id")
            if src in index:
                index[src].outgoing.append(rel)
            if tgt in index:
                index[tgt].incoming.append(rel)
        return index

    def _assign_longitudinal_types(
        self,
        erc_roles: List[dict[str, Any]],
        graph_index: Dict[str, RoleGraphIndex],
    ) -> Dict[str, str]:
        longitudinals = [
            r for r in erc_roles if r.get("role_type") == ROLE_LONGITUDINAL
        ]
        assignment: Dict[str, str] = {}
        if not longitudinals:
            return assignment

        assigned: Set[str] = set()
        for role in longitudinals:
            rid = role["semantic_role_id"]
            idx = graph_index.get(rid, RoleGraphIndex(role_id=rid))
            for rel in idx.outgoing:
                if rel.get("relationship_type") != REL_CONNECTED_TO:
                    continue
                tgt = rel.get("target_role_id")
                tgt_role = next(
                    (r for r in erc_roles if r.get("semantic_role_id") == tgt),
                    None,
                )
                if tgt_role and tgt_role.get("role_type") == ROLE_LONGITUDINAL:
                    assignment.setdefault(rid, OBJECT_TOP_REINFORCEMENT)
                    assignment.setdefault(tgt, OBJECT_BOTTOM_REINFORCEMENT)
                    assigned.update({rid, tgt})

            for rel in idx.outgoing:
                if rel.get("relationship_type") != REL_CONTINUES_TO:
                    continue
                tgt = rel.get("target_role_id")
                assignment.setdefault(rid, OBJECT_TOP_REINFORCEMENT)
                assignment.setdefault(tgt, OBJECT_BOTTOM_REINFORCEMENT)
                assigned.update({rid, tgt})

        remaining = [
            r for r in longitudinals if r["semantic_role_id"] not in assigned
        ]
        remaining.sort(key=lambda r: r["semantic_role_id"])
        for i, role in enumerate(remaining):
            rid = role["semantic_role_id"]
            assignment[rid] = (
                OBJECT_TOP_REINFORCEMENT if i % 2 == 0 else OBJECT_BOTTOM_REINFORCEMENT
            )
        return assignment

    @staticmethod
    def _resolve_object_type(
        role: dict[str, Any],
        longitudinal_map: Dict[str, str],
    ) -> str:
        role_type = str(role.get("role_type", ROLE_UNKNOWN))
        role_id = role.get("semantic_role_id", "")

        if role_type == ROLE_LONGITUDINAL:
            return longitudinal_map.get(role_id, OBJECT_TOP_REINFORCEMENT)
        static = {
            ROLE_BEAM_IDENTIFIER: OBJECT_BEAM_IDENTIFIER,
            ROLE_TRANSVERSE: OBJECT_STIRRUP,
            ROLE_SIDE_FACE: OBJECT_SIDE_FACE_REINFORCEMENT,
            ROLE_DIMENSION: OBJECT_DIMENSION,
            ROLE_LEADER: OBJECT_LEADER,
            ROLE_GENERAL_NOTE: OBJECT_GENERAL_NOTE,
            ROLE_SECTION_IDENTIFIER: OBJECT_SECTION_MARKER,
            ROLE_CALLOUT: OBJECT_TEXT_NOTE,
            ROLE_DEVELOPMENT_LENGTH: OBJECT_TEXT_NOTE,
            ROLE_HOOK: OBJECT_UNKNOWN,
            ROLE_ANCHORAGE: OBJECT_UNKNOWN,
            ROLE_SPACER: OBJECT_UNKNOWN,
            ROLE_UNKNOWN: OBJECT_UNKNOWN,
        }
        return static.get(role_type, OBJECT_UNKNOWN)

    @staticmethod
    def _compute_confidence(role: dict[str, Any], idx: RoleGraphIndex) -> float:
        weights: List[Tuple[float, float]] = [
            (float(role.get("classification_confidence", 0.0)), 1.0)
        ]
        for rel in idx.incoming + idx.outgoing:
            weights.append((float(rel.get("confidence", 0.0)), 0.5))
        total_w = sum(w for _, w in weights)
        if total_w <= 0:
            return 0.0
        return sum(c * w for c, w in weights) / total_w

    @staticmethod
    def _link_connected_objects(
        registry: EngineeringObjectRegistry,
        object_ids: List[str],
        role_to_object: Dict[str, str],
        graph_index: Dict[str, RoleGraphIndex],
    ) -> None:
        for obj_id in object_ids:
            obj = registry.lookup(obj_id)
            if not obj:
                continue
            role_id = obj.get("source_role_id")
            idx = graph_index.get(role_id)
            if not idx:
                continue
            connected_objs = sorted(
                {
                    role_to_object[rid]
                    for rid in idx.connected_role_ids()
                    if rid in role_to_object
                }
            )
            obj["connected_object_ids"] = connected_objs
            obj["annotation_ids"] = [
                role_to_object[rid]
                for rid in idx.annotation_role_ids()
                if rid in role_to_object
            ]
            obj["parent_group_ids"] = [
                role_to_object[rid]
                for rid in idx.parent_group_role_ids()
                if rid in role_to_object
            ]
            obj["child_group_ids"] = [
                role_to_object[rid]
                for rid in idx.child_group_role_ids()
                if rid in role_to_object
            ]
