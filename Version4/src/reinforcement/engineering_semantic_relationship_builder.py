"""Discover Engineering Semantic Relationships within each ERC — Phase G.5.0.1."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.reinforcement.engineering_semantic_relationship import (
    build_semantic_relationship,
    semantic_relationship_registry_section,
)
from src.reinforcement.engineering_semantic_relationship_graph import (
    EngineeringSemanticRelationshipGraph,
)
from src.reinforcement.engineering_semantic_relationship_registry import (
    EngineeringSemanticRelationshipRegistry,
)
from src.reinforcement.engineering_semantic_relationship_types import (
    CLASSIFICATION_SOURCE_ANNOTATION,
    CLASSIFICATION_SOURCE_CONTINUITY,
    CLASSIFICATION_SOURCE_GROUPING,
    CLASSIFICATION_SOURCE_LEADER_LINK,
    CLASSIFICATION_SOURCE_PROXIMITY,
    REL_ANNOTATES,
    REL_CONNECTED_TO,
    REL_CONTINUES_TO,
    REL_HAS_DEVELOPMENT_LENGTH,
    REL_HAS_DIMENSION,
    REL_HAS_LEADER,
    REL_HAS_NOTE,
    REL_HAS_SIDE_FACE_NOTE,
    REL_HAS_SPACING_NOTE,
    REL_PART_OF_GROUP,
    REINFORCEMENT_ROLE_TYPES,
    STATE_CLASSIFIED,
)
from src.reinforcement.engineering_semantic_role_types import (
    ROLE_BEAM_IDENTIFIER,
    ROLE_CALLOUT,
    ROLE_DEVELOPMENT_LENGTH,
    ROLE_DIMENSION,
    ROLE_GENERAL_NOTE,
    ROLE_LEADER,
    ROLE_LONGITUDINAL,
    ROLE_SIDE_FACE,
    ROLE_TRANSVERSE,
)

SPACING_RE = re.compile(r"@|SPACING|@\s*\d", re.IGNORECASE)


class EngineeringSemanticRelationshipBuilder:
    """Connect semantic roles through explicit relationships — one ERC at a time."""

    def __init__(self, proximity_tolerance_mm: float = 8000.0) -> None:
        self._proximity_tolerance_mm = proximity_tolerance_mm

    def build(
        self,
        contexts: List[dict[str, Any]],
        roles: List[dict[str, Any]],
        drawing_model: dict[str, Any],
    ) -> Tuple[List[dict[str, Any]], EngineeringSemanticRelationshipRegistry]:
        registry = EngineeringSemanticRelationshipRegistry()
        roles_by_id = {r["semantic_role_id"]: r for r in roles}
        anchors = RoleAnchorIndex(drawing_model)
        detail_types = self._detail_type_index(drawing_model)
        enriched: List[dict[str, Any]] = []
        seen_signatures: set[str] = set()

        for erc in contexts:
            erc_id = str(erc.get("reinforcement_context_id", ""))
            erc_roles = [
                roles_by_id[rid]
                for rid in erc.get("semantic_roles", [])
                if rid in roles_by_id
            ]
            rel_ids: List[str] = []
            detail_type = detail_types.get(str(erc.get("detail_context_id", "")), "")

            def add_rel(
                rel_type: str,
                source_id: str,
                target_id: str,
                confidence: float,
                source_kind: str,
                notes: str = "",
            ) -> None:
                if source_id == target_id:
                    return
                signature = f"{erc_id}|{rel_type}|{source_id}|{target_id}"
                if signature in seen_signatures:
                    return
                seen_signatures.add(signature)
                rel = build_semantic_relationship(
                    relationship_id=registry.next_id(),
                    relationship_type=rel_type,
                    source_role_id=source_id,
                    target_role_id=target_id,
                    owner_context_id=erc_id,
                    detail_context_id=str(erc.get("detail_context_id", "")),
                    drawing_id=str(erc.get("drawing_id", "")),
                    drawing_set_id=str(erc.get("drawing_set_id", "")),
                    classification_source=source_kind,
                    confidence=confidence,
                    lifecycle=STATE_CLASSIFIED,
                    notes=notes,
                )
                rel_ids.append(registry.register(rel))

            reinf_roles = [
                r for r in erc_roles if r.get("role_type") in REINFORCEMENT_ROLE_TYPES
            ]
            longitudinal = [r for r in erc_roles if r.get("role_type") == ROLE_LONGITUDINAL]
            transverse = [r for r in erc_roles if r.get("role_type") == ROLE_TRANSVERSE]
            primary_targets = longitudinal + transverse

            # Rule 1: Leader → nearest reinforcement (LONGITUDINAL/TRANSVERSE has leader)
            for role in erc_roles:
                if role.get("role_type") == ROLE_LEADER:
                    nearest = self._nearest_role(role, primary_targets, anchors)
                    if nearest:
                        add_rel(
                            REL_HAS_LEADER,
                            nearest["semantic_role_id"],
                            role["semantic_role_id"],
                            0.88,
                            CLASSIFICATION_SOURCE_LEADER_LINK,
                        )
                elif role.get("leader_asset_ids") and role.get("role_type") in REINFORCEMENT_ROLE_TYPES:
                    for leader_role in erc_roles:
                        if leader_role.get("role_type") != ROLE_LEADER:
                            continue
                        if set(leader_role.get("leader_asset_ids", [])) & set(
                            role.get("leader_asset_ids", [])
                        ):
                            add_rel(
                                REL_HAS_LEADER,
                                role["semantic_role_id"],
                                leader_role["semantic_role_id"],
                                0.9,
                                CLASSIFICATION_SOURCE_LEADER_LINK,
                            )

            # Rule 2: Dimension → nearest reinforcement
            for role in erc_roles:
                if role.get("role_type") != ROLE_DIMENSION:
                    continue
                nearest = self._nearest_role(role, primary_targets, anchors)
                if nearest:
                    add_rel(
                        REL_HAS_DIMENSION,
                        nearest["semantic_role_id"],
                        role["semantic_role_id"],
                        0.87,
                        CLASSIFICATION_SOURCE_PROXIMITY,
                    )

            # Rule 3: Development length → nearest reinforcement
            for role in erc_roles:
                if role.get("role_type") != ROLE_DEVELOPMENT_LENGTH:
                    continue
                nearest = self._nearest_role(role, primary_targets, anchors)
                if nearest:
                    add_rel(
                        REL_HAS_DEVELOPMENT_LENGTH,
                        nearest["semantic_role_id"],
                        role["semantic_role_id"],
                        0.9,
                        CLASSIFICATION_SOURCE_PROXIMITY,
                    )

            # Rule 4: Side face → nearest reinforcement
            for role in erc_roles:
                if role.get("role_type") != ROLE_SIDE_FACE:
                    continue
                nearest = self._nearest_role(role, primary_targets, anchors)
                if nearest:
                    add_rel(
                        REL_HAS_SIDE_FACE_NOTE,
                        nearest["semantic_role_id"],
                        role["semantic_role_id"],
                        0.88,
                        CLASSIFICATION_SOURCE_PROXIMITY,
                    )

            # Rule 5: Spacing note → nearest stirrup/transverse
            for role in erc_roles:
                if not self._is_spacing_note(role, drawing_model):
                    continue
                nearest = self._nearest_role(role, transverse or primary_targets, anchors)
                if nearest:
                    add_rel(
                        REL_HAS_SPACING_NOTE,
                        nearest["semantic_role_id"],
                        role["semantic_role_id"],
                        0.86,
                        CLASSIFICATION_SOURCE_PROXIMITY,
                    )

            # Rule 6: Beam identifier annotates all reinforcement roles
            beam_ids = [r for r in erc_roles if r.get("role_type") == ROLE_BEAM_IDENTIFIER]
            for beam_role in beam_ids:
                for reinf in reinf_roles:
                    add_rel(
                        REL_ANNOTATES,
                        beam_role["semantic_role_id"],
                        reinf["semantic_role_id"],
                        0.92,
                        CLASSIFICATION_SOURCE_ANNOTATION,
                    )

            # Rule 7: General notes → nearest engineering role
            for role in erc_roles:
                if role.get("role_type") not in (ROLE_GENERAL_NOTE, ROLE_CALLOUT):
                    continue
                candidates = [r for r in erc_roles if r is not role]
                nearest = self._nearest_role(role, candidates, anchors)
                if nearest:
                    add_rel(
                        REL_HAS_NOTE,
                        nearest["semantic_role_id"],
                        role["semantic_role_id"],
                        0.75,
                        CLASSIFICATION_SOURCE_PROXIMITY,
                    )

            # Rule 8: Repeated beam identifiers → PART_OF_GROUP
            if len(beam_ids) > 1:
                hub = beam_ids[0]["semantic_role_id"]
                for other in beam_ids[1:]:
                    add_rel(
                        REL_PART_OF_GROUP,
                        hub,
                        other["semantic_role_id"],
                        0.85,
                        CLASSIFICATION_SOURCE_GROUPING,
                    )

            # Rule 9: Continuous multi-span → CONTINUES_TO adjacent longitudinal roles
            if detail_type == "CONTINUOUS_MULTI_SPAN" and len(longitudinal) > 1:
                ordered = sorted(
                    longitudinal,
                    key=lambda r: anchors.anchor(r).get("x", 0.0),
                )
                for left, right in zip(ordered, ordered[1:]):
                    add_rel(
                        REL_CONTINUES_TO,
                        left["semantic_role_id"],
                        right["semantic_role_id"],
                        0.8,
                        CLASSIFICATION_SOURCE_CONTINUITY,
                    )

            # Fallback: connect co-located reinforcement roles within ERC
            if len(reinf_roles) > 1:
                hub = reinf_roles[0]["semantic_role_id"]
                for other in reinf_roles[1:]:
                    add_rel(
                        REL_CONNECTED_TO,
                        hub,
                        other["semantic_role_id"],
                        0.7,
                        CLASSIFICATION_SOURCE_PROXIMITY,
                        notes="co-located reinforcement roles",
                    )

            enriched_ctx = dict(erc)
            enriched_ctx["semantic_relationship_registry"] = semantic_relationship_registry_section(
                str(erc.get("beam_mark", "")),
                relationship_ids=rel_ids,
            )
            enriched_ctx["semantic_relationships"] = list(rel_ids)
            enriched.append(enriched_ctx)

        return enriched, registry

    @staticmethod
    def build_project_exports(
        contexts: List[dict[str, Any]],
        registry: EngineeringSemanticRelationshipRegistry,
        roles: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
        unknown_threshold: float = 0.15,
    ) -> dict[str, Any]:
        relationships = registry.all_relationships()
        primary = drawing_models[0] if drawing_models else {}
        return {
            "engineering_semantic_relationships": relationships,
            "engineering_semantic_relationship_registry": (
                EngineeringSemanticRelationshipRegistry.build_project_registry(
                    contexts,
                    relationships,
                    drawing_id=primary.get("drawing_id", ""),
                    drawing_set_id=primary.get("drawing_set_id", ""),
                    floor_id=primary.get("floor_id", ""),
                    project_id=project_id,
                )
            ),
            "engineering_semantic_relationship_graph": EngineeringSemanticRelationshipGraph.build(
                contexts,
                relationships,
                roles,
                project_id=project_id,
            ),
            "engineering_semantic_relationship_summary": (
                EngineeringSemanticRelationshipRegistry.build_summary(
                    contexts,
                    relationships,
                    unknown_threshold=unknown_threshold,
                )
            ),
        }

    def _nearest_role(
        self,
        source_role: dict[str, Any],
        candidates: List[dict[str, Any]],
        anchors: "RoleAnchorIndex",
    ) -> Optional[dict[str, Any]]:
        if not candidates:
            return None
        src = anchors.anchor(source_role)
        best: Optional[dict[str, Any]] = None
        best_dist = self._proximity_tolerance_mm
        for candidate in candidates:
            if candidate["semantic_role_id"] == source_role["semantic_role_id"]:
                continue
            dst = anchors.anchor(candidate)
            dist = ((src["x"] - dst["x"]) ** 2 + (src["y"] - dst["y"]) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = candidate
        return best

    def _is_spacing_note(
        self,
        role: dict[str, Any],
        drawing_model: dict[str, Any],
    ) -> bool:
        if role.get("role_type") == ROLE_TRANSVERSE:
            return False
        text_by_id = {
            t["geometry_id"]: t for t in drawing_model.get("text_objects", [])
        }
        for text_id in role.get("text_asset_ids", []):
            raw = str(text_by_id.get(text_id, {}).get("text", ""))
            if SPACING_RE.search(raw):
                return True
        return False

    @staticmethod
    def _detail_type_index(drawing_model: dict[str, Any]) -> Dict[str, str]:
        return {
            str(dc.get("detail_context_id", "")): str(dc.get("detail_type", ""))
            for dc in drawing_model.get("detail_contexts", [])
        }


class RoleAnchorIndex:
    """Compute anchor points for semantic roles from drawing assets."""

    def __init__(self, drawing_model: dict[str, Any]) -> None:
        self._entities: Dict[str, dict[str, Any]] = {}
        for key in ("sketches", "text_objects", "leaders", "blocks"):
            for item in drawing_model.get(key, []):
                gid = item.get("geometry_id")
                if gid:
                    self._entities[gid] = item

    def anchor(self, role: dict[str, Any]) -> dict[str, float]:
        points: List[Tuple[float, float]] = []
        for asset_id in (
            list(role.get("geometry_asset_ids", []))
            + list(role.get("text_asset_ids", []))
            + list(role.get("leader_asset_ids", []))
            + list(role.get("block_asset_ids", []))
        ):
            pt = self._asset_center(asset_id)
            if pt:
                points.append(pt)
        if not points:
            return {"x": 0.0, "y": 0.0}
        return {
            "x": sum(p[0] for p in points) / len(points),
            "y": sum(p[1] for p in points) / len(points),
        }

    def _asset_center(self, asset_id: str) -> Optional[Tuple[float, float]]:
        entity = self._entities.get(asset_id)
        if not entity:
            return None
        box = entity.get("bbox", {})
        if box:
            return (
                (float(box.get("min_x", 0.0)) + float(box.get("max_x", 0.0))) / 2.0,
                (float(box.get("min_y", 0.0)) + float(box.get("max_y", 0.0))) / 2.0,
            )
        end = entity.get("end", entity.get("arrow_head", {}))
        if end:
            return (float(end.get("x", 0.0)), float(end.get("y", 0.0)))
        start = entity.get("start", {})
        if start:
            return (float(start.get("x", 0.0)), float(start.get("y", 0.0)))
        return None
