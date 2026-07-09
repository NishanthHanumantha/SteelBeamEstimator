"""Property graph builder — graph-driven candidate discovery (Phase G.5.2)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from src.engineering_objects.engineering_object_types import (
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
)
from src.property_graph.property_candidate import (
    build_property_candidate,
    property_candidate_registry_section,
)
from src.property_graph.property_graph_registry import PropertyGraphRegistry
from src.property_graph.property_graph_types import (
    CANDIDATE_ANCHORAGE,
    CANDIDATE_BAR_LENGTH,
    CANDIDATE_BAR_LOCATION,
    CANDIDATE_BAR_MARK,
    CANDIDATE_BAR_TYPE,
    CANDIDATE_BEND,
    CANDIDATE_BLOCK,
    CANDIDATE_CALLOUT,
    CANDIDATE_CUT_LENGTH,
    CANDIDATE_DEVELOPMENT_LENGTH,
    CANDIDATE_DIAMETER,
    CANDIDATE_DIMENSION,
    CANDIDATE_HOOK,
    CANDIDATE_HOOK_DIRECTION,
    CANDIDATE_LAP,
    CANDIDATE_LEADER,
    CANDIDATE_LEVEL,
    CANDIDATE_MARK,
    CANDIDATE_NOTE,
    CANDIDATE_QUANTITY,
    CANDIDATE_REINFORCEMENT_CODE,
    CANDIDATE_SHAPE_CODE,
    CANDIDATE_SKETCH,
    CANDIDATE_SPACING,
    CANDIDATE_START_OFFSET,
    CANDIDATE_END_OFFSET,
    CANDIDATE_TEXT,
    CANDIDATE_UNKNOWN,
    CANDIDATE_ZONE,
    CONFIDENCE_DIRECT,
    CONFIDENCE_GENERAL_NOTE,
    CONFIDENCE_ONE_HOP,
    CONFIDENCE_TWO_HOP,
    CONFIDENCE_UNKNOWN,
    DISCOVERY_ANNOTATION_CHAIN,
    DISCOVERY_CALLOUT_CHAIN,
    DISCOVERY_DIRECT,
    DISCOVERY_GRAPH_INFERENCE,
    DISCOVERY_LEADER_CHAIN,
    DISCOVERY_ONE_HOP,
    DISCOVERY_TEXT_CHAIN,
    DISCOVERY_TWO_HOP,
    DISCOVERY_UNKNOWN,
    MAX_TRAVERSAL_DISTANCE,
    SOURCE_TYPE_BLOCK,
    SOURCE_TYPE_CALLOUT,
    SOURCE_TYPE_DIMENSION,
    SOURCE_TYPE_LEADER,
    SOURCE_TYPE_NOTE,
    SOURCE_TYPE_SKETCH,
    SOURCE_TYPE_TEXT,
)
from src.reinforcement.engineering_semantic_relationship_types import (
    REL_ANNOTATES,
    REL_ASSOCIATED_WITH,
    REL_CONNECTED_TO,
    REL_CONTINUES_TO,
    REL_HAS_CALLOUT,
    REL_HAS_DEVELOPMENT_LENGTH,
    REL_HAS_DIMENSION,
    REL_HAS_LEADER,
    REL_HAS_NOTE,
    REL_HAS_SIDE_FACE_NOTE,
    REL_HAS_SPACING_NOTE,
    REL_HAS_STIRRUP_NOTE,
    REL_PART_OF_GROUP,
    REL_REFERENCES,
)
from src.reinforcement.engineering_semantic_role_types import (
    ROLE_BEAM_IDENTIFIER,
    ROLE_CALLOUT,
    ROLE_DEVELOPMENT_LENGTH,
    ROLE_DIMENSION,
    ROLE_GENERAL_NOTE,
    ROLE_LEADER,
    ROLE_LONGITUDINAL,
    ROLE_SECTION_IDENTIFIER,
    ROLE_SIDE_FACE,
    ROLE_TRANSVERSE,
)


@dataclass
class RoleVisit:
    role_id: str
    distance: int
    relationship_id: str
    relationship_type: str
    discovery_method: str


class PropertyGraphBuilder:
    """Discover property source candidates by traversing the semantic graph."""

    def __init__(self, max_distance: int = MAX_TRAVERSAL_DISTANCE) -> None:
        self.max_distance = max_distance

    def build(
        self,
        contexts: List[dict[str, Any]],
        objects: List[dict[str, Any]],
        roles: List[dict[str, Any]],
        relationships: List[dict[str, Any]],
    ) -> Tuple[List[dict[str, Any]], PropertyGraphRegistry, List[dict[str, Any]]]:
        registry = PropertyGraphRegistry()
        roles_by_id = {r["semantic_role_id"]: r for r in roles}
        objects_by_id = {
            (o.get("object_id") or o.get("engineering_object_id")): o for o in objects
        }
        rels_by_erc: Dict[str, List[dict[str, Any]]] = {}
        for rel in relationships:
            erc_id = rel.get("owner_context_id", "")
            rels_by_erc.setdefault(erc_id, []).append(rel)

        enriched: List[dict[str, Any]] = []
        all_candidates: List[dict[str, Any]] = []

        for erc in contexts:
            erc_id = str(erc.get("reinforcement_context_id", ""))
            erc_objects = [
                objects_by_id[oid]
                for oid in _erc_object_ids(erc)
                if oid in objects_by_id
            ]
            erc_rels = rels_by_erc.get(erc_id, [])
            candidate_ids: List[str] = []

            for obj in erc_objects:
                obj_id = obj.get("object_id") or obj.get("engineering_object_id")
                source_role_id = obj.get("source_role_id", "")
                visits = self._traverse_roles(source_role_id, erc_rels, roles_by_id)
                seen_keys: Set[Tuple[str, str, str]] = set()

                for visit in visits:
                    role = roles_by_id.get(visit.role_id)
                    if not role:
                        continue
                    cand_types = self._candidate_types_for_visit(
                        role,
                        visit,
                        obj.get("object_type", ""),
                    )
                    for asset_kind, entity_ids, source_type in self._role_assets(role):
                        for entity_id in entity_ids:
                            for cand_type in cand_types.get(asset_kind, [CANDIDATE_UNKNOWN]):
                                key = (obj_id, entity_id, cand_type)
                                if key in seen_keys:
                                    continue
                                seen_keys.add(key)
                                confidence = self._confidence_for(visit, role)
                                candidate = build_property_candidate(
                                    candidate_id=registry.next_id(),
                                    engineering_object_id=obj_id,
                                    candidate_type=cand_type,
                                    candidate_source_type=source_type,
                                    source_entity_id=entity_id,
                                    source_relationship_id=visit.relationship_id,
                                    confidence=confidence,
                                    relationship_distance=visit.distance,
                                    discovery_method=visit.discovery_method,
                                    owner_context_id=erc_id,
                                    source_role_id=visit.role_id,
                                    metadata={
                                        "semantic_role_type": role.get("role_type"),
                                        "relationship_type": visit.relationship_type,
                                        "engineering_object_type": obj.get("object_type"),
                                    },
                                )
                                cid = registry.register(candidate)
                                candidate_ids.append(cid)
                                all_candidates.append(candidate)

            enriched_ctx = dict(erc)
            enriched_ctx["property_candidate_registry"] = property_candidate_registry_section(
                str(erc.get("beam_mark", "")),
                candidate_ids=[
                    c["candidate_id"]
                    for c in all_candidates
                    if c.get("owner_context_id") == erc_id
                ],
            )
            enriched_ctx["property_candidates"] = list(
                enriched_ctx["property_candidate_registry"]["candidate_ids"]
            )
            enriched.append(enriched_ctx)

        graph = self._build_graph(objects, all_candidates)
        return enriched, registry, graph

    @staticmethod
    def build_project_exports(
        contexts: List[dict[str, Any]],
        registry: PropertyGraphRegistry,
        graph: dict[str, Any],
        objects: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        candidates = registry.all_candidates()
        primary = drawing_models[0] if drawing_models else {}
        property_registry = PropertyGraphRegistry.build_project_registry(
            contexts,
            candidates,
            objects,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        return {
            "property_candidates": candidates,
            "property_registry": property_registry,
            "property_graph": graph,
        }

    def _traverse_roles(
        self,
        source_role_id: str,
        erc_rels: List[dict[str, Any]],
        roles_by_id: Dict[str, dict[str, Any]],
    ) -> List[RoleVisit]:
        if not source_role_id or source_role_id not in roles_by_id:
            return []

        visits: List[RoleVisit] = []
        seen: Set[str] = set()
        queue: deque[RoleVisit] = deque()

        queue.append(
            RoleVisit(
                role_id=source_role_id,
                distance=0,
                relationship_id="",
                relationship_type="",
                discovery_method=DISCOVERY_DIRECT,
            )
        )

        while queue:
            visit = queue.popleft()
            if visit.role_id in seen:
                continue
            seen.add(visit.role_id)
            visits.append(visit)
            if visit.distance >= self.max_distance:
                continue

            for rel in erc_rels:
                next_role = None
                if rel.get("source_role_id") == visit.role_id:
                    next_role = rel.get("target_role_id")
                elif rel.get("target_role_id") == visit.role_id:
                    next_role = rel.get("source_role_id")

                if not next_role or next_role in seen or next_role not in roles_by_id:
                    continue

                rel_type = str(rel.get("relationship_type", ""))
                distance = visit.distance + 1
                discovery = self._discovery_method(rel_type, distance)
                queue.append(
                    RoleVisit(
                        role_id=next_role,
                        distance=distance,
                        relationship_id=str(rel.get("relationship_id", "")),
                        relationship_type=rel_type,
                        discovery_method=discovery,
                    )
                )

        return visits

    @staticmethod
    def _discovery_method(rel_type: str, distance: int) -> str:
        if distance <= 0:
            return DISCOVERY_DIRECT
        mapping = {
            REL_ANNOTATES: DISCOVERY_ANNOTATION_CHAIN,
            REL_HAS_LEADER: DISCOVERY_LEADER_CHAIN,
            REL_HAS_NOTE: DISCOVERY_TEXT_CHAIN,
            REL_HAS_CALLOUT: DISCOVERY_CALLOUT_CHAIN,
            REL_HAS_SPACING_NOTE: DISCOVERY_TEXT_CHAIN,
            REL_HAS_STIRRUP_NOTE: DISCOVERY_TEXT_CHAIN,
            REL_HAS_SIDE_FACE_NOTE: DISCOVERY_TEXT_CHAIN,
            REL_HAS_DEVELOPMENT_LENGTH: DISCOVERY_TEXT_CHAIN,
            REL_HAS_DIMENSION: DISCOVERY_GRAPH_INFERENCE,
            REL_CONNECTED_TO: DISCOVERY_GRAPH_INFERENCE,
            REL_CONTINUES_TO: DISCOVERY_GRAPH_INFERENCE,
            REL_PART_OF_GROUP: DISCOVERY_GRAPH_INFERENCE,
            REL_ASSOCIATED_WITH: DISCOVERY_GRAPH_INFERENCE,
            REL_REFERENCES: DISCOVERY_GRAPH_INFERENCE,
        }
        if rel_type in mapping:
            return mapping[rel_type]
        if distance == 1:
            return DISCOVERY_ONE_HOP
        if distance == 2:
            return DISCOVERY_TWO_HOP
        return DISCOVERY_UNKNOWN

    @staticmethod
    def _confidence_for(visit: RoleVisit, role: dict[str, Any]) -> float:
        if visit.distance == 0:
            return CONFIDENCE_DIRECT
        if visit.discovery_method == DISCOVERY_LEADER_CHAIN:
            return CONFIDENCE_ONE_HOP
        if visit.distance == 2:
            return CONFIDENCE_TWO_HOP
        if role.get("role_type") == ROLE_GENERAL_NOTE:
            return CONFIDENCE_GENERAL_NOTE
        if visit.distance == 1:
            return CONFIDENCE_ONE_HOP
        return CONFIDENCE_UNKNOWN

    def _candidate_types_for_visit(
        self,
        role: dict[str, Any],
        visit: RoleVisit,
        object_type: str,
    ) -> Dict[str, List[str]]:
        role_type = str(role.get("role_type", ""))
        rel_type = visit.relationship_type
        result: Dict[str, List[str]] = {
            "geometry": [],
            "text": [],
            "leader": [],
            "block": [],
        }

        result["geometry"] = self._types_for_asset(
            role_type, object_type, "geometry", rel_type
        )
        result["text"] = self._types_for_asset(role_type, object_type, "text", rel_type)
        result["leader"] = self._types_for_asset(
            role_type, object_type, "leader", rel_type
        )
        result["block"] = self._types_for_asset(
            role_type, object_type, "block", rel_type
        )
        return result

    @staticmethod
    def _types_for_asset(
        role_type: str,
        object_type: str,
        asset_kind: str,
        rel_type: str,
    ) -> List[str]:
        types: Set[str] = set()

        if asset_kind == "geometry":
            types.add(CANDIDATE_SKETCH)
        elif asset_kind == "text":
            types.add(CANDIDATE_TEXT)
        elif asset_kind == "leader":
            types.add(CANDIDATE_LEADER)
        elif asset_kind == "block":
            types.add(CANDIDATE_BLOCK)

        longitudinal_objects = {OBJECT_TOP_REINFORCEMENT, OBJECT_BOTTOM_REINFORCEMENT}
        if role_type == ROLE_LONGITUDINAL or object_type in longitudinal_objects:
            if asset_kind == "text":
                types.update({
                    CANDIDATE_DIAMETER,
                    CANDIDATE_BAR_MARK,
                    CANDIDATE_BAR_TYPE,
                    CANDIDATE_REINFORCEMENT_CODE,
                    CANDIDATE_QUANTITY,
                    CANDIDATE_BAR_LENGTH,
                    CANDIDATE_CUT_LENGTH,
                })
            if asset_kind == "geometry":
                types.update({
                    CANDIDATE_BAR_LENGTH,
                    CANDIDATE_SHAPE_CODE,
                    CANDIDATE_BAR_LOCATION,
                    CANDIDATE_HOOK,
                    CANDIDATE_HOOK_DIRECTION,
                    CANDIDATE_BEND,
                    CANDIDATE_START_OFFSET,
                    CANDIDATE_END_OFFSET,
                })

        if role_type == ROLE_TRANSVERSE or object_type == OBJECT_STIRRUP:
            if asset_kind == "text":
                types.update({CANDIDATE_SPACING, CANDIDATE_QUANTITY, CANDIDATE_BAR_MARK})
            if asset_kind == "geometry":
                types.update({
                    CANDIDATE_SHAPE_CODE,
                    CANDIDATE_HOOK,
                    CANDIDATE_HOOK_DIRECTION,
                    CANDIDATE_BEND,
                    CANDIDATE_SPACING,
                })

        if role_type == ROLE_SIDE_FACE or object_type == OBJECT_SIDE_FACE_REINFORCEMENT:
            if asset_kind == "text":
                types.update({CANDIDATE_DIAMETER, CANDIDATE_SPACING, CANDIDATE_QUANTITY})

        if role_type == ROLE_DEVELOPMENT_LENGTH or rel_type == REL_HAS_DEVELOPMENT_LENGTH:
            if asset_kind == "text":
                types.update({
                    CANDIDATE_DEVELOPMENT_LENGTH,
                    CANDIDATE_ANCHORAGE,
                    CANDIDATE_LAP,
                    CANDIDATE_CUT_LENGTH,
                })

        if role_type == ROLE_DIMENSION or object_type == OBJECT_DIMENSION or rel_type == REL_HAS_DIMENSION:
            if asset_kind in ("text", "geometry"):
                types.add(CANDIDATE_DIMENSION)

        if role_type == ROLE_BEAM_IDENTIFIER or object_type == OBJECT_BEAM_IDENTIFIER:
            if asset_kind == "text":
                types.update({CANDIDATE_MARK, CANDIDATE_REINFORCEMENT_CODE, CANDIDATE_LEVEL})

        if role_type == ROLE_GENERAL_NOTE or object_type == OBJECT_GENERAL_NOTE:
            if asset_kind == "text":
                types.update({CANDIDATE_NOTE, CANDIDATE_TEXT, CANDIDATE_ZONE})

        if role_type == ROLE_CALLOUT or object_type == OBJECT_TEXT_NOTE:
            if asset_kind == "text":
                types.update({CANDIDATE_CALLOUT, CANDIDATE_NOTE, CANDIDATE_TEXT})

        if role_type == ROLE_SECTION_IDENTIFIER or object_type == OBJECT_SECTION_MARKER:
            if asset_kind == "text":
                types.add(CANDIDATE_MARK)

        if role_type == ROLE_LEADER or object_type == OBJECT_LEADER:
            if asset_kind == "leader":
                types.add(CANDIDATE_LEADER)
            if asset_kind == "text":
                types.add(CANDIDATE_TEXT)

        if rel_type == REL_HAS_SPACING_NOTE and asset_kind == "text":
            types.add(CANDIDATE_SPACING)
        if rel_type == REL_HAS_STIRRUP_NOTE and asset_kind == "text":
            types.update({CANDIDATE_SPACING, CANDIDATE_QUANTITY})
        if rel_type == REL_HAS_SIDE_FACE_NOTE and asset_kind == "text":
            types.update({CANDIDATE_DIAMETER, CANDIDATE_SPACING})
        if rel_type == REL_HAS_NOTE and asset_kind == "text":
            types.add(CANDIDATE_NOTE)
        if rel_type == REL_HAS_CALLOUT and asset_kind == "text":
            types.add(CANDIDATE_CALLOUT)
        if rel_type == REL_ANNOTATES and asset_kind == "text":
            types.update({CANDIDATE_MARK, CANDIDATE_TEXT, CANDIDATE_REINFORCEMENT_CODE})

        if not types:
            types.add(CANDIDATE_UNKNOWN)
        return sorted(types)

    @staticmethod
    def _role_assets(
        role: dict[str, Any],
    ) -> List[Tuple[str, List[str], str]]:
        assets: List[Tuple[str, List[str], str]] = []
        geometry = list(role.get("geometry_asset_ids") or role.get("source_geometry_ids") or [])
        text = list(role.get("text_asset_ids") or [])
        leaders = list(role.get("leader_asset_ids") or [])
        blocks = list(role.get("block_asset_ids") or [])

        if geometry:
            assets.append(("geometry", geometry, SOURCE_TYPE_SKETCH))
        if text:
            source = SOURCE_TYPE_TEXT
            if role.get("role_type") == ROLE_DIMENSION:
                source = SOURCE_TYPE_DIMENSION
            elif role.get("role_type") in (ROLE_GENERAL_NOTE,):
                source = SOURCE_TYPE_NOTE
            elif role.get("role_type") == ROLE_CALLOUT:
                source = SOURCE_TYPE_CALLOUT
            assets.append(("text", text, source))
        if leaders:
            assets.append(("leader", leaders, SOURCE_TYPE_LEADER))
        if blocks:
            assets.append(("block", blocks, SOURCE_TYPE_BLOCK))
        return assets

    @staticmethod
    def _build_graph(
        objects: List[dict[str, Any]],
        candidates: List[dict[str, Any]],
    ) -> dict[str, Any]:
        nodes: List[dict[str, Any]] = []
        edges: List[dict[str, Any]] = []
        existing: Set[str] = set()
        seen_edges: Set[Tuple[str, str, str]] = set()

        def add_node(node: dict[str, Any]) -> None:
            nid = node.get("id")
            if nid and nid not in existing:
                nodes.append(node)
                existing.add(nid)

        def add_edge(edge: dict[str, Any]) -> None:
            key = (edge.get("from"), edge.get("to"), edge.get("relationship"))
            if key in seen_edges:
                return
            seen_edges.add(key)
            edges.append(edge)

        for obj in objects:
            oid = obj.get("object_id") or obj.get("engineering_object_id")
            if oid:
                add_node({"id": oid, "type": "ENGINEERING_OBJECT", "object_type": obj.get("object_type")})

        for cand in candidates:
            cid = cand.get("candidate_id")
            entity_id = cand.get("source_entity_id")
            obj_id = cand.get("engineering_object_id")
            if not cid:
                continue
            add_node(
                {
                    "id": cid,
                    "type": "PROPERTY_CANDIDATE",
                    "candidate_type": cand.get("candidate_type"),
                    "engineering_object_id": obj_id,
                }
            )
            if entity_id:
                add_node(
                    {
                        "id": entity_id,
                        "type": "SOURCE_ENTITY",
                        "source_type": cand.get("candidate_source_type"),
                    }
                )
            if obj_id:
                add_edge(
                    {
                        "from": obj_id,
                        "to": cid,
                        "relationship": "HAS_PROPERTY_SOURCE",
                    }
                )
            if entity_id:
                add_edge(
                    {
                        "from": cid,
                        "to": entity_id,
                        "relationship": "REFERENCES",
                    }
                )
            rel_id = cand.get("source_relationship_id")
            if rel_id:
                add_node({"id": rel_id, "type": "SEMANTIC_RELATIONSHIP"})
                add_edge(
                    {
                        "from": cid,
                        "to": rel_id,
                        "relationship": "DISCOVERED_FROM",
                    }
                )
            erc_id = cand.get("owner_context_id")
            if erc_id:
                add_edge(
                    {
                        "from": cid,
                        "to": erc_id,
                        "relationship": "BELONGS_TO",
                    }
                )

        entity_groups: Dict[Tuple[str, str], List[str]] = {}
        for cand in candidates:
            key = (cand.get("engineering_object_id", ""), cand.get("source_entity_id", ""))
            entity_groups.setdefault(key, []).append(cand.get("candidate_id", ""))
        for ids in entity_groups.values():
            if len(ids) < 2:
                continue
            for i, src_id in enumerate(ids):
                for tgt_id in ids[i + 1 :]:
                    add_edge(
                        {
                            "from": src_id,
                            "to": tgt_id,
                            "relationship": "CONNECTED_TO",
                        }
                    )

        return {
            "phase": "Phase G.5.2",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "supports_traversal": True,
            "nodes": nodes,
            "edges": edges,
        }


def _erc_object_ids(ctx: dict[str, Any]) -> List[str]:
    from src.engineering_objects.engineering_object import erc_engineering_object_ids

    return erc_engineering_object_ids(ctx)
