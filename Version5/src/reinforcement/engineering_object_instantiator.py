"""Instantiate engineering objects from semantic roles or owned assets — Phase G.5.1."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.reinforcement.engineering_object import (
    engineering_objects_section,
    format_engineering_object_registry_id,
)
from src.reinforcement.engineering_object_classifier import (
    AssetClassification,
    EngineeringObjectClassifier,
    ObjectRoleBucket,
)
from src.reinforcement.engineering_object_factory import EngineeringObjectFactory
from src.reinforcement.engineering_object_graph import EngineeringObjectGraph
from src.reinforcement.engineering_object_lifecycle import EngineeringObjectLifecycle
from src.reinforcement.engineering_object_registry import EngineeringObjectRegistry
from src.reinforcement.engineering_object_types import (
    CLASSIFICATION_SOURCE_INFERRED,
    OBJECT_TYPE_ANCHORAGE,
    OBJECT_TYPE_BEAM_LABEL,
    OBJECT_TYPE_BOTTOM_BAR,
    OBJECT_TYPE_BOTTOM_EXTRA_BAR,
    OBJECT_TYPE_DEVELOPMENT_LENGTH,
    OBJECT_TYPE_DIMENSION,
    OBJECT_TYPE_HOOK,
    OBJECT_TYPE_REINFORCEMENT_NOTE,
    OBJECT_TYPE_SIDE_FACE_REINFORCEMENT,
    OBJECT_TYPE_SPACER_BAR,
    OBJECT_TYPE_STIRRUP,
    OBJECT_TYPE_TOP_BAR,
    OBJECT_TYPE_TOP_EXTRA_BAR,
    OBJECT_TYPE_UNKNOWN,
)
from src.reinforcement.engineering_relationships import (
    EngineeringRelationships,
    REL_BELONGS_TO,
    REL_REFERENCES,
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


class EngineeringObjectInstantiator:
    """Create classified engineering objects from semantic roles (G.5.0) or assets."""

    def __init__(self) -> None:
        self._classifier = EngineeringObjectClassifier()

    def build(
        self,
        contexts: List[dict[str, Any]],
        drawing_model: dict[str, Any],
        semantic_role_registry: Optional[dict[str, Any]] = None,
    ) -> Tuple[
        List[dict[str, Any]],
        EngineeringObjectRegistry,
        List[dict[str, Any]],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ]:
        registry = EngineeringObjectRegistry()
        factory = EngineeringObjectFactory(registry)
        enriched_contexts: List[dict[str, Any]] = []
        all_classifications: List[dict[str, Any]] = []
        all_relationships: List[dict[str, Any]] = []

        roles_by_id = {
            r.get("semantic_role_id"): r
            for r in (semantic_role_registry or {}).get("roles", [])
        }
        use_semantic_roles = bool(roles_by_id)

        sketches = drawing_model.get("sketches", [])
        text_objects = drawing_model.get("text_objects", [])
        leaders = drawing_model.get("leaders", [])
        blocks = drawing_model.get("blocks", [])
        views = drawing_model.get("detail_views", [])

        for erc in contexts:
            erc_id = str(erc.get("reinforcement_context_id", ""))
            beam_mark = str(erc.get("beam_mark", ""))
            owner_registry_id = format_engineering_object_registry_id(beam_mark)

            if use_semantic_roles and erc.get("semantic_roles"):
                buckets, asset_classes = self._buckets_from_semantic_roles(
                    erc,
                    roles_by_id,
                    sketches,
                    text_objects,
                    views,
                )
            else:
                asset_classes, buckets = self._classifier.classify_erc(
                    erc, sketches, text_objects, leaders, blocks, views
                )

            object_ids: List[str] = []

            for bucket in buckets:
                if not self._bucket_has_assets(bucket):
                    continue
                obj = factory.create_instantiated(
                    object_type=bucket.object_type,
                    owner_context_id=erc_id,
                    owner_registry_id=owner_registry_id,
                    asset_references={
                        "geometry": list(bucket.geometry),
                        "text": list(bucket.text),
                        "leaders": list(bucket.leaders),
                        "blocks": list(bucket.blocks),
                    },
                    classification_source=bucket.classification_source,
                    confidence=bucket.confidence,
                    metadata=dict(bucket.metadata),
                )
                object_ids.append(obj["engineering_object_id"])
                all_relationships.extend(self._relationships_for_object(erc_id, obj))

            for cls in asset_classes:
                all_classifications.append(
                    {
                        "reinforcement_context_id": erc_id,
                        "beam_mark": beam_mark,
                        "asset_id": cls.asset_id,
                        "asset_kind": cls.asset_kind,
                        "object_type": cls.object_type,
                        "confidence": cls.confidence,
                        "classification_source": cls.classification_source,
                        "metadata": dict(cls.metadata),
                        "source": "semantic_role" if use_semantic_roles else "direct",
                    }
                )

            enriched = dict(erc)
            enriched["engineering_objects"] = engineering_objects_section(
                beam_mark,
                object_ids=object_ids,
            )
            enriched_contexts.append(enriched)

        classification_export = {
            "phase": "Phase G.5.1",
            "classification_count": len(all_classifications),
            "classifications": all_classifications,
            "source": "semantic_roles" if use_semantic_roles else "direct_geometry",
        }
        relationships_export = EngineeringRelationships.build_export(all_relationships)
        statistics = self._build_statistics(registry.all_objects(), enriched_contexts)

        return (
            enriched_contexts,
            registry,
            all_relationships,
            classification_export,
            relationships_export,
            statistics,
        )

    def _buckets_from_semantic_roles(
        self,
        erc: dict[str, Any],
        roles_by_id: Dict[str, dict[str, Any]],
        sketches: List[dict[str, Any]],
        text_objects: List[dict[str, Any]],
        views: List[dict[str, Any]],
    ) -> Tuple[List[ObjectRoleBucket], List[AssetClassification]]:
        beam_mark = str(erc.get("beam_mark", "")).upper()
        view_center_y = self._classifier._view_center_y(views, erc.get("owned_views", []))
        sketch_by_id = {s["geometry_id"]: s for s in sketches}
        text_by_id = {t["geometry_id"]: t for t in text_objects}
        buckets: List[ObjectRoleBucket] = []
        asset_classes: List[AssetClassification] = []

        for role_id in erc.get("semantic_roles", []):
            role = roles_by_id.get(role_id)
            if not role:
                continue
            object_type = self._map_semantic_role_to_object_type(
                role,
                sketch_by_id,
                text_by_id,
                view_center_y,
                beam_mark,
            )
            bucket = ObjectRoleBucket(
                object_type=object_type,
                geometry=list(role.get("geometry_asset_ids", [])),
                text=list(role.get("text_asset_ids", [])),
                leaders=list(role.get("leader_asset_ids", [])),
                blocks=list(role.get("block_asset_ids", [])),
                confidence=float(role.get("classification_confidence", 0.0)),
                classification_source=str(
                    role.get("classification_source", CLASSIFICATION_SOURCE_INFERRED)
                ),
                metadata={
                    "semantic_role_id": role_id,
                    "semantic_role_type": role.get("role_type"),
                },
            )
            buckets.append(bucket)
            for geom_id in bucket.geometry:
                asset_classes.append(
                    AssetClassification(
                        geom_id, "geometry", object_type, bucket.confidence, bucket.classification_source
                    )
                )
            for text_id in bucket.text:
                asset_classes.append(
                    AssetClassification(
                        text_id, "text", object_type, bucket.confidence, bucket.classification_source
                    )
                )
            for leader_id in bucket.leaders:
                asset_classes.append(
                    AssetClassification(
                        leader_id, "leader", object_type, bucket.confidence, bucket.classification_source
                    )
                )
            for block_id in bucket.blocks:
                asset_classes.append(
                    AssetClassification(
                        block_id, "block", object_type, bucket.confidence, bucket.classification_source
                    )
                )

        return buckets, asset_classes

    def _map_semantic_role_to_object_type(
        self,
        role: dict[str, Any],
        sketch_by_id: Dict[str, dict[str, Any]],
        text_by_id: Dict[str, dict[str, Any]],
        view_center_y: float,
        beam_mark: str,
    ) -> str:
        role_type = str(role.get("role_type", ROLE_UNKNOWN))
        static_map = {
            ROLE_TRANSVERSE: OBJECT_TYPE_STIRRUP,
            ROLE_SIDE_FACE: OBJECT_TYPE_SIDE_FACE_REINFORCEMENT,
            ROLE_SPACER: OBJECT_TYPE_SPACER_BAR,
            ROLE_DEVELOPMENT_LENGTH: OBJECT_TYPE_DEVELOPMENT_LENGTH,
            ROLE_DIMENSION: OBJECT_TYPE_DIMENSION,
            ROLE_HOOK: OBJECT_TYPE_HOOK,
            ROLE_ANCHORAGE: OBJECT_TYPE_ANCHORAGE,
            ROLE_GENERAL_NOTE: OBJECT_TYPE_REINFORCEMENT_NOTE,
            ROLE_SECTION_IDENTIFIER: OBJECT_TYPE_REINFORCEMENT_NOTE,
            ROLE_LEADER: OBJECT_TYPE_UNKNOWN,
            ROLE_CALLOUT: OBJECT_TYPE_UNKNOWN,
            ROLE_UNKNOWN: OBJECT_TYPE_UNKNOWN,
        }
        if role_type == ROLE_LONGITUDINAL:
            return self._longitudinal_object_type(role, sketch_by_id, text_by_id, view_center_y)
        if role_type == ROLE_BEAM_IDENTIFIER:
            for text_id in role.get("text_asset_ids", []):
                text = text_by_id.get(text_id, {})
                raw = str(text.get("text", "")).upper().replace(" ", "")
                if beam_mark and beam_mark in raw:
                    return OBJECT_TYPE_BEAM_LABEL
            return OBJECT_TYPE_REINFORCEMENT_NOTE
        return static_map.get(role_type, OBJECT_TYPE_UNKNOWN)

    def _longitudinal_object_type(
        self,
        role: dict[str, Any],
        sketch_by_id: Dict[str, dict[str, Any]],
        text_by_id: Dict[str, dict[str, Any]],
        view_center_y: float,
    ) -> str:
        for text_id in role.get("text_asset_ids", []):
            text = text_by_id.get(text_id, {})
            raw = str(text.get("text", "")).upper()
            center_y = self._classifier._text_center_y(text)
            if "EXTRA" in raw and "TOP" in raw:
                return OBJECT_TYPE_TOP_EXTRA_BAR
            if "EXTRA" in raw and "BOTTOM" in raw:
                return OBJECT_TYPE_BOTTOM_EXTRA_BAR
            if "EXTRA" in raw:
                return (
                    OBJECT_TYPE_TOP_EXTRA_BAR
                    if center_y < view_center_y
                    else OBJECT_TYPE_BOTTOM_EXTRA_BAR
                )
            if center_y < view_center_y:
                return OBJECT_TYPE_TOP_BAR
            return OBJECT_TYPE_BOTTOM_BAR
        for geom_id in role.get("geometry_asset_ids", []):
            sketch = sketch_by_id.get(geom_id, {})
            center_y = self._classifier._sketch_center_y(sketch)
            if center_y < view_center_y:
                return OBJECT_TYPE_TOP_BAR
            return OBJECT_TYPE_BOTTOM_BAR
        return OBJECT_TYPE_TOP_BAR

    @staticmethod
    def build_project_exports(
        contexts: List[dict[str, Any]],
        registry: EngineeringObjectRegistry,
        relationships: List[dict[str, Any]],
        classification_export: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
    ) -> dict[str, Any]:
        objects = registry.all_objects()
        primary = drawing_models[0] if drawing_models else {}
        object_registry = EngineeringObjectRegistry.build_project_registry(
            contexts,
            objects=objects,
            drawing_id=primary.get("drawing_id", ""),
            drawing_set_id=primary.get("drawing_set_id", ""),
            floor_id=primary.get("floor_id", ""),
            project_id=project_id,
        )
        object_registry["phase"] = "Phase G.5.1"
        object_graph = EngineeringObjectGraph.build(
            contexts,
            drawing_models,
            project_id=project_id,
            objects=objects,
        )
        object_graph["phase"] = "Phase G.5.1"
        relationships_export = EngineeringRelationships.build_export(relationships)
        relationships_export["phase"] = "Phase G.5.1"
        lifecycle_registry = EngineeringObjectLifecycle.build_project_registry(
            contexts, phase="Phase G.5.1"
        )
        summary = EngineeringObjectRegistry.build_summary(contexts, objects=objects)
        summary["phase"] = "Phase G.5.1"
        summary["status"] = "OBJECTS_INSTANTIATED"
        statistics = EngineeringObjectInstantiator._build_statistics(objects, contexts)
        return {
            "engineering_object_registry": object_registry,
            "engineering_object_graph": object_graph,
            "engineering_object_relationships": relationships_export,
            "engineering_object_classification": classification_export,
            "engineering_object_lifecycle_registry": lifecycle_registry,
            "engineering_object_summary": summary,
            "engineering_object_statistics": statistics,
        }

    @staticmethod
    def _bucket_has_assets(bucket: ObjectRoleBucket) -> bool:
        return bool(bucket.geometry or bucket.text or bucket.leaders or bucket.blocks)

    @staticmethod
    def _relationships_for_object(
        erc_id: str,
        obj: dict[str, Any],
    ) -> List[dict[str, Any]]:
        obj_id = obj.get("engineering_object_id", "")
        refs = obj.get("asset_references", {})
        rels = [
            EngineeringRelationships.build_relationship(
                obj_id,
                erc_id,
                REL_BELONGS_TO,
                source_type="ENGINEERING_OBJECT",
                target_type="ERC",
            )
        ]
        for geom_id in refs.get("geometry", []):
            rels.append(
                EngineeringRelationships.build_relationship(
                    obj_id,
                    geom_id,
                    REL_REFERENCES,
                    source_type="ENGINEERING_OBJECT",
                    target_type="SKETCH",
                )
            )
        for text_id in refs.get("text", []):
            rels.append(
                EngineeringRelationships.build_relationship(
                    obj_id,
                    text_id,
                    REL_REFERENCES,
                    source_type="ENGINEERING_OBJECT",
                    target_type="TEXT",
                )
            )
        for leader_id in refs.get("leaders", []):
            rels.append(
                EngineeringRelationships.build_relationship(
                    obj_id,
                    leader_id,
                    REL_REFERENCES,
                    source_type="ENGINEERING_OBJECT",
                    target_type="LEADER",
                )
            )
        for block_id in refs.get("blocks", []):
            rels.append(
                EngineeringRelationships.build_relationship(
                    obj_id,
                    block_id,
                    REL_REFERENCES,
                    source_type="ENGINEERING_OBJECT",
                    target_type="BLOCK",
                )
            )
        return rels

    @staticmethod
    def _build_statistics(
        objects: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
    ) -> dict[str, Any]:
        by_type: Dict[str, int] = {}
        by_erc: Dict[str, int] = {}
        confidences: List[float] = []
        asset_counts = {"geometry": 0, "text": 0, "leaders": 0, "blocks": 0}
        for obj in objects:
            otype = str(obj.get("object_type", "UNKNOWN"))
            by_type[otype] = by_type.get(otype, 0) + 1
            owner = str(obj.get("owner_context_id", ""))
            by_erc[owner] = by_erc.get(owner, 0) + 1
            confidences.append(float(obj.get("confidence", 0.0)))
            refs = obj.get("asset_references", {})
            for key in asset_counts:
                asset_counts[key] += len(refs.get(key, []))
        return {
            "phase": "Phase G.5.1",
            "context_count": len(contexts),
            "object_count": len(objects),
            "objects_by_type": by_type,
            "objects_by_erc": by_erc,
            "average_confidence": round(
                sum(confidences) / len(confidences) if confidences else 0.0, 3
            ),
            "referenced_assets": asset_counts,
        }
