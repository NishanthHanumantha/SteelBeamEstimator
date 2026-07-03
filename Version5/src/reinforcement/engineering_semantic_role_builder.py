"""Build Engineering Semantic Roles for each ERC — Phase G.5.0."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.reinforcement.engineering_semantic_role import (
    build_semantic_role,
    semantic_role_registry_section,
)
from src.reinforcement.engineering_semantic_role_classifier import (
    EngineeringSemanticRoleClassifier,
    SemanticRoleBucket,
)
from src.reinforcement.engineering_semantic_role_graph import EngineeringSemanticRoleGraph
from src.reinforcement.engineering_semantic_role_lifecycle import (
    EngineeringSemanticRoleLifecycle,
)
from src.reinforcement.engineering_semantic_role_registry import (
    EngineeringSemanticRoleRegistry,
)


class EngineeringSemanticRoleBuilder:
    """Discover and classify semantic roles from owned assets."""

    def __init__(self, unknown_threshold: float = 0.15) -> None:
        self._classifier = EngineeringSemanticRoleClassifier()
        self._unknown_threshold = unknown_threshold

    def build(
        self,
        contexts: List[dict[str, Any]],
        drawing_model: dict[str, Any],
    ) -> Tuple[List[dict[str, Any]], EngineeringSemanticRoleRegistry, dict[str, Any]]:
        registry = EngineeringSemanticRoleRegistry()
        enriched: List[dict[str, Any]] = []

        sketches = drawing_model.get("sketches", [])
        text_objects = drawing_model.get("text_objects", [])
        leaders = drawing_model.get("leaders", [])
        blocks = drawing_model.get("blocks", [])

        for erc in contexts:
            erc_id = str(erc.get("reinforcement_context_id", ""))
            _, buckets = self._classifier.classify_erc(
                erc, sketches, text_objects, leaders, blocks
            )
            role_ids: List[str] = []
            seen_signatures: set[str] = set()

            for bucket in buckets:
                if not self._bucket_has_assets(bucket):
                    continue
                signature = self._bucket_signature(bucket)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)

                role = build_semantic_role(
                    semantic_role_id=registry.next_id(),
                    role_type=bucket.role_type,
                    owner_context_id=erc_id,
                    detail_context_id=str(erc.get("detail_context_id", "")),
                    drawing_id=str(erc.get("drawing_id", "")),
                    drawing_set_id=str(erc.get("drawing_set_id", "")),
                    beam_match_id=str(erc.get("beam_match_id", "")),
                    geometry_asset_ids=list(bucket.geometry),
                    text_asset_ids=list(bucket.text),
                    leader_asset_ids=list(bucket.leaders),
                    block_asset_ids=list(bucket.blocks),
                    classification_source=bucket.classification_source,
                    classification_confidence=bucket.confidence,
                    lifecycle=EngineeringSemanticRoleLifecycle.current_phase_state(),
                    metadata=dict(bucket.metadata),
                )
                role_id = registry.register(role)
                role_ids.append(role_id)

            enriched_ctx = dict(erc)
            enriched_ctx["semantic_role_registry"] = semantic_role_registry_section(
                str(erc.get("beam_mark", "")),
                role_ids=role_ids,
            )
            enriched_ctx["semantic_roles"] = list(role_ids)
            enriched.append(enriched_ctx)

        return enriched, registry, {"classifier": "EngineeringSemanticRoleClassifier"}

    @staticmethod
    def build_project_exports(
        contexts: List[dict[str, Any]],
        registry: EngineeringSemanticRoleRegistry,
        drawing_models: List[dict[str, Any]],
        project_id: str = "",
        unknown_threshold: float = 0.15,
    ) -> dict[str, Any]:
        roles = registry.all_roles()
        primary = drawing_models[0] if drawing_models else {}
        return {
            "engineering_semantic_roles": roles,
            "engineering_semantic_role_registry": EngineeringSemanticRoleRegistry.build_project_registry(
                contexts,
                roles,
                drawing_id=primary.get("drawing_id", ""),
                drawing_set_id=primary.get("drawing_set_id", ""),
                floor_id=primary.get("floor_id", ""),
                project_id=project_id,
            ),
            "engineering_semantic_role_graph": EngineeringSemanticRoleGraph.build(
                contexts,
                roles,
                drawing_models,
                project_id=project_id,
            ),
            "engineering_semantic_role_summary": EngineeringSemanticRoleRegistry.build_summary(
                contexts,
                roles,
                unknown_threshold=unknown_threshold,
            ),
        }

    @staticmethod
    def _bucket_has_assets(bucket: SemanticRoleBucket) -> bool:
        return bool(bucket.geometry or bucket.text or bucket.leaders or bucket.blocks)

    @staticmethod
    def _bucket_signature(bucket: SemanticRoleBucket) -> str:
        parts = [
            bucket.role_type,
            ",".join(sorted(bucket.geometry)),
            ",".join(sorted(bucket.text)),
            ",".join(sorted(bucket.leaders)),
            ",".join(sorted(bucket.blocks)),
        ]
        return "|".join(parts)
