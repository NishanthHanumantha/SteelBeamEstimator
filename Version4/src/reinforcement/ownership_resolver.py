"""Resolve engineering ownership of reinforcement geometry via BeamMatch hierarchy."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from loguru import logger

from src.reinforcement.reinforcement_geometry_utils import bbox_center, point_in_bbox
from src.reinforcement.engineering_reinforcement_context import (
    ENGINEERING_STATUS_OWNERSHIP_READY,
    EngineeringReinforcementContext,
    FUTURE_PLACEHOLDERS,
    OWNERSHIP_STATUS_RESOLVED,
    format_erc_id,
    ownership_block,
)


class OwnershipResolver:
    """Assign every reinforcement entity to exactly one EngineeringReinforcementContext."""

    def build(
        self,
        model: dict[str, Any],
        drawing_set_id: str,
        floor_id: str,
        drawing_id: str,
        beam_matches: List[dict[str, Any]],
        detail_contexts: List[dict[str, Any]],
        detail_identities: List[dict[str, Any]],
        detail_views: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        text_objects: List[dict[str, Any]],
        leaders: List[dict[str, Any]],
        blocks: List[dict[str, Any]],
        regions: List[dict[str, Any]],
        geometric_relationships: List[dict[str, Any]],
    ) -> Tuple[
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
        List[dict[str, Any]],
    ]:
        project_id = str(model.get("project_workspace", {}).get("project_id", ""))
        context_by_id = {str(c.get("detail_context_id")): c for c in detail_contexts}
        view_by_id = {
            str(v.get("view_id", v.get("geometry_id"))): v for v in detail_views
        }

        sketch_by_id = {str(s.get("geometry_id")): dict(s) for s in sketches}
        text_by_id = {str(t.get("geometry_id")): dict(t) for t in text_objects}
        leader_by_id = {str(l.get("geometry_id")): dict(l) for l in leaders}
        block_by_id = {str(b.get("geometry_id")): dict(b) for b in blocks}
        view_store = {str(v.get("view_id", v.get("geometry_id"))): dict(v) for v in detail_views}
        region_by_id = {str(r.get("geometry_id")): r for r in regions}

        contexts: List[dict[str, Any]] = []
        relationships: List[dict[str, Any]] = []
        ownership_registry: List[dict[str, Any]] = []
        identity_by_id = {str(i.get("detail_identity_id")): dict(i) for i in detail_identities}
        assigned: set[str] = set()

        for match in beam_matches:
            erc_id = format_erc_id(str(match.get("beam_mark", "")))
            detail_context_id = str(match.get("detail_context_id", ""))
            detail_identity_id = str(match.get("detail_identity_id", ""))
            beam_context_id = str(match.get("beam_context_id", ""))
            detail_ctx = context_by_id.get(detail_context_id, {})

            owned_views: List[str] = []
            owned_geometry: List[str] = []
            owned_text: List[str] = []
            owned_leaders: List[str] = []
            owned_blocks: List[str] = []

            view_ids = list(detail_ctx.get("view_ids", []))
            if not view_ids:
                identity = identity_by_id.get(detail_identity_id, {})
                view_ids = list(identity.get("metadata", {}).get("view_ids", []))

            for view_id in view_ids:
                vid = str(view_id)
                view = view_store.get(vid) or view_by_id.get(vid)
                if not view:
                    continue
                self._assign_entity(
                    vid,
                    "VIEW",
                    erc_id,
                    view_store,
                    assigned,
                    ownership_registry,
                    owned_views,
                )
                relationships.append(
                    self._rel(erc_id, vid, "ERC_OWNS_VIEW")
                )

                for gid in view.get("geometry_entities", []):
                    self._assign_entity(
                        str(gid),
                        "SKETCH",
                        erc_id,
                        sketch_by_id,
                        assigned,
                        ownership_registry,
                        owned_geometry,
                    )
                    relationships.append(self._rel(erc_id, str(gid), "ERC_OWNS_GEOMETRY"))

                for tid in view.get("text_entities", []):
                    self._assign_entity(
                        str(tid),
                        "TEXT",
                        erc_id,
                        text_by_id,
                        assigned,
                        ownership_registry,
                        owned_text,
                    )
                    relationships.append(self._rel(erc_id, str(tid), "ERC_OWNS_TEXT"))

                for lid in view.get("leader_entities", []):
                    self._assign_entity(
                        str(lid),
                        "LEADER",
                        erc_id,
                        leader_by_id,
                        assigned,
                        ownership_registry,
                        owned_leaders,
                    )
                    relationships.append(self._rel(erc_id, str(lid), "ERC_OWNS_LEADER"))

                for bid in view.get("block_entities", []):
                    self._assign_entity(
                        str(bid),
                        "BLOCK",
                        erc_id,
                        block_by_id,
                        assigned,
                        ownership_registry,
                        owned_blocks,
                    )
                    relationships.append(self._rel(erc_id, str(bid), "ERC_OWNS_BLOCK"))

            region_id = str(detail_ctx.get("region_id", ""))
            region = region_by_id.get(region_id, {})
            region_box = region.get("bbox", {})
            if region_box:
                for gid, sketch in sketch_by_id.items():
                    if gid in assigned:
                        continue
                    if str(sketch.get("region_id", "")) == region_id:
                        self._assign_entity(
                            gid,
                            "SKETCH",
                            erc_id,
                            sketch_by_id,
                            assigned,
                            ownership_registry,
                            owned_geometry,
                        )
                        relationships.append(self._rel(erc_id, gid, "ERC_OWNS_GEOMETRY"))

                for store, gtype, owned_list, rel_name in (
                    (text_by_id, "TEXT", owned_text, "ERC_OWNS_TEXT"),
                    (leader_by_id, "LEADER", owned_leaders, "ERC_OWNS_LEADER"),
                    (block_by_id, "BLOCK", owned_blocks, "ERC_OWNS_BLOCK"),
                ):
                    for gid, entity in store.items():
                        if gid in assigned:
                            continue
                        if self._entity_in_region(entity, region_box):
                            self._assign_entity(
                                gid,
                                gtype,
                                erc_id,
                                store,
                                assigned,
                                ownership_registry,
                                owned_list,
                            )
                            relationships.append(self._rel(erc_id, gid, rel_name))

            erc = EngineeringReinforcementContext(
                reinforcement_context_id=erc_id,
                beam_context_id=beam_context_id,
                beam_match_id=str(match.get("beam_match_id", "")),
                beam_mark=str(match.get("beam_mark", "")),
                drawing_set_id=drawing_set_id,
                drawing_id=drawing_id,
                project_id=project_id or str(match.get("project_id", "")),
                floor_id=floor_id,
                detail_identity_id=detail_identity_id,
                detail_context_id=detail_context_id,
                engineering_status=ENGINEERING_STATUS_OWNERSHIP_READY,
                ownership_status=OWNERSHIP_STATUS_RESOLVED,
                owned_views=owned_views,
                owned_geometry=owned_geometry,
                owned_text=owned_text,
                owned_leaders=owned_leaders,
                owned_blocks=owned_blocks,
                future=dict(FUTURE_PLACEHOLDERS),
                metadata={"drawing_id": drawing_id},
            )
            contexts.append(erc.to_dict())

            relationships.append(
                self._rel(str(match.get("beam_match_id", "")), erc_id, "BEAM_MATCH_CREATES_ERC")
            )
            relationships.append(
                self._rel(beam_context_id, erc_id, "BEAM_CONTEXT_HAS_REINFORCEMENT_CONTEXT")
            )

            if detail_identity_id in identity_by_id:
                ident = identity_by_id[detail_identity_id]
                ident["engineering_owner"] = erc_id
                ident["engineering_status"] = ENGINEERING_STATUS_OWNERSHIP_READY

        region_to_erc = {}
        for erc_dict in contexts:
            ctx = context_by_id.get(str(erc_dict.get("detail_context_id", "")), {})
            region_id = str(ctx.get("region_id", ""))
            if region_id:
                region_to_erc[region_id] = str(erc_dict.get("reinforcement_context_id", ""))

        self._inherit_from_relationships(
            geometric_relationships,
            region_to_erc,
            sketch_by_id,
            text_by_id,
            leader_by_id,
            block_by_id,
            assigned,
            ownership_registry,
            relationships,
        )
        self._inherit_from_owned_views(
            view_store,
            text_by_id,
            leader_by_id,
            block_by_id,
            assigned,
            ownership_registry,
            relationships,
        )
        self._rebuild_owned_lists(
            contexts,
            view_store,
            sketch_by_id,
            text_by_id,
            leader_by_id,
            block_by_id,
        )

        context_by_beam = {str(c.get("context_id")): c for c in model.get("beam_engineering_contexts", [])}
        for erc_dict in contexts:
            beam_ctx_id = str(erc_dict.get("beam_context_id", ""))
            if beam_ctx_id in context_by_beam:
                ctx_copy = dict(context_by_beam[beam_ctx_id])
                ctx_copy["reinforcement_context_id"] = erc_dict["reinforcement_context_id"]
                ctx_copy["ownership_status"] = OWNERSHIP_STATUS_RESOLVED
                context_by_beam[beam_ctx_id] = ctx_copy
        model["beam_engineering_contexts"] = list(context_by_beam.values())

        updated_sketches = list(sketch_by_id.values())
        updated_text = list(text_by_id.values())
        updated_leaders = list(leader_by_id.values())
        updated_blocks = list(block_by_id.values())
        updated_views = list(view_store.values())
        updated_identities = list(identity_by_id.values())

        logger.info(
            "Ownership resolved — drawing={} erc_count={} entities={}",
            drawing_id,
            len(contexts),
            len(ownership_registry),
        )
        return (
            contexts,
            updated_identities,
            updated_views,
            updated_sketches,
            updated_text,
            updated_leaders,
            updated_blocks,
            relationships,
            ownership_registry,
        )

    def _inherit_from_relationships(
        self,
        geometric_relationships: List[dict[str, Any]],
        region_to_erc: dict[str, str],
        sketch_by_id: dict[str, dict[str, Any]],
        text_by_id: dict[str, dict[str, Any]],
        leader_by_id: dict[str, dict[str, Any]],
        block_by_id: dict[str, dict[str, Any]],
        assigned: set[str],
        ownership_registry: List[dict[str, Any]],
        relationships: List[dict[str, Any]],
    ) -> None:
        rel_map = {
            "REGION_CONTAINS_TEXT": ("TEXT", text_by_id, "ERC_OWNS_TEXT"),
            "REGION_CONTAINS_LEADER": ("LEADER", leader_by_id, "ERC_OWNS_LEADER"),
            "REGION_CONTAINS_BLOCK": ("BLOCK", block_by_id, "ERC_OWNS_BLOCK"),
            "SKETCH_CONTAINS_TEXT": ("TEXT", text_by_id, "ERC_OWNS_TEXT"),
            "SKETCH_CONTAINS_LEADER": ("LEADER", leader_by_id, "ERC_OWNS_LEADER"),
        }
        changed = True
        while changed:
            changed = False
            for rel in geometric_relationships:
                rel_name = str(rel.get("relationship", ""))
                if rel_name not in rel_map:
                    continue
                target = str(rel.get("target_id", ""))
                if not target or target in assigned:
                    continue
                source = str(rel.get("source_id", ""))
                gtype, store, edge_rel = rel_map[rel_name]
                if target not in store:
                    continue
                erc_id = None
                if rel_name.startswith("REGION_CONTAINS_"):
                    erc_id = region_to_erc.get(source)
                else:
                    erc_id = sketch_by_id.get(source, {}).get("ownership", {}).get("owner_id")
                if not erc_id:
                    continue
                self._assign_entity(
                    target,
                    gtype,
                    str(erc_id),
                    store,
                    assigned,
                    ownership_registry,
                    [],
                )
                relationships.append(self._rel(str(erc_id), target, edge_rel))
                changed = True

    def _inherit_from_owned_views(
        self,
        view_store: dict[str, dict[str, Any]],
        text_by_id: dict[str, dict[str, Any]],
        leader_by_id: dict[str, dict[str, Any]],
        block_by_id: dict[str, dict[str, Any]],
        assigned: set[str],
        ownership_registry: List[dict[str, Any]],
        relationships: List[dict[str, Any]],
    ) -> None:
        for view in view_store.values():
            erc_id = view.get("ownership", {}).get("owner_id")
            if not erc_id:
                continue
            view_box = view.get("bbox", {})
            if not view_box:
                continue
            for store, gtype, rel_name in (
                (text_by_id, "TEXT", "ERC_OWNS_TEXT"),
                (leader_by_id, "LEADER", "ERC_OWNS_LEADER"),
                (block_by_id, "BLOCK", "ERC_OWNS_BLOCK"),
            ):
                for gid, entity in store.items():
                    if gid in assigned:
                        continue
                    if self._entity_in_region(entity, view_box):
                        self._assign_entity(
                            gid,
                            gtype,
                            str(erc_id),
                            store,
                            assigned,
                            ownership_registry,
                            [],
                        )
                        relationships.append(self._rel(str(erc_id), gid, rel_name))

    @staticmethod
    def _rebuild_owned_lists(
        contexts: List[dict[str, Any]],
        view_store: dict[str, dict[str, Any]],
        sketch_by_id: dict[str, dict[str, Any]],
        text_by_id: dict[str, dict[str, Any]],
        leader_by_id: dict[str, dict[str, Any]],
        block_by_id: dict[str, dict[str, Any]],
    ) -> None:
        for erc in contexts:
            erc_id = str(erc.get("reinforcement_context_id", ""))
            erc["owned_views"] = sorted(
                gid
                for gid, view in view_store.items()
                if view.get("ownership", {}).get("owner_id") == erc_id
            )
            erc["owned_geometry"] = sorted(
                gid
                for gid, sketch in sketch_by_id.items()
                if sketch.get("ownership", {}).get("owner_id") == erc_id
            )
            erc["owned_text"] = sorted(
                gid
                for gid, text in text_by_id.items()
                if text.get("ownership", {}).get("owner_id") == erc_id
            )
            erc["owned_leaders"] = sorted(
                gid
                for gid, leader in leader_by_id.items()
                if leader.get("ownership", {}).get("owner_id") == erc_id
            )
            erc["owned_blocks"] = sorted(
                gid
                for gid, block in block_by_id.items()
                if block.get("ownership", {}).get("owner_id") == erc_id
            )

    def _entity_in_region(self, entity: dict[str, Any], region_box: dict[str, float]) -> bool:
        bbox = entity.get("bbox")
        if bbox:
            cx, cy = bbox_center(bbox)
            return point_in_bbox(cx, cy, region_box)
        start = entity.get("start", {})
        sx = start.get("x")
        sy = start.get("y")
        if sx is not None and sy is not None:
            return point_in_bbox(float(sx), float(sy), region_box)
        return False

    def _assign_entity(
        self,
        geometry_id: str,
        geometry_type: str,
        erc_id: str,
        store: dict[str, dict[str, Any]],
        assigned: set[str],
        ownership_registry: List[dict[str, Any]],
        owned_list: List[str],
    ) -> None:
        if geometry_id in assigned or geometry_id not in store:
            return
        entity = store[geometry_id]
        entity["ownership"] = ownership_block(erc_id)
        assigned.add(geometry_id)
        owned_list.append(geometry_id)
        ownership_registry.append(
            {
                "geometry_id": geometry_id,
                "geometry_type": geometry_type,
                "owner_type": "ENGINEERING_REINFORCEMENT_CONTEXT",
                "owner_id": erc_id,
                "ownership_source": "BEAM_MATCH",
                "ownership_confidence": 1.0,
            }
        )

    def _rel(self, source_id: str, target_id: str, relationship: str) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "type": "ENGINEERING",
        }
