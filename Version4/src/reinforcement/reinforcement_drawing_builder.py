"""Assemble ReinforcementDrawingModel and update workspace / graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from loguru import logger

from src.project.drawing_identity import DRAWING_TYPE_BEAM_REINFORCEMENT
from src.reinforcement.beam_candidate_builder import BeamCandidateBuilder
from src.reinforcement.beam_candidate_ranker import BeamCandidateRanker
from src.reinforcement.beam_candidate_registry import BeamCandidateRegistry
from src.reinforcement.beam_candidate_validator import BeamCandidateValidator
from src.reinforcement.detail_context_builder import DetailContextBuilder
from src.reinforcement.detail_context_registry import DetailContextRegistry
from src.reinforcement.detail_context_validator import DetailContextValidator
from src.reinforcement.detail_fingerprint_builder import DetailFingerprintBuilder
from src.reinforcement.detail_identity_builder import DetailIdentityBuilder
from src.reinforcement.detail_identity_registry import DetailIdentityRegistry
from src.reinforcement.detail_identity_validator import DetailIdentityValidator
from src.reinforcement.match_decision_builder import MatchDecisionBuilder
from src.reinforcement.match_decision_registry import MatchDecisionRegistry
from src.reinforcement.match_decision_quality_builder import MatchDecisionQualityBuilder
from src.reinforcement.match_decision_quality_registry import MatchDecisionQualityRegistry
from src.reinforcement.match_decision_quality_validator import MatchDecisionQualityValidator
from src.reinforcement.beam_match_builder import BeamMatchBuilder
from src.reinforcement.beam_match_registry import BeamMatchRegistry
from src.reinforcement.engineering_object_graph import EngineeringObjectGraph
from src.reinforcement.engineering_object_lifecycle import EngineeringObjectLifecycle
from src.reinforcement.engineering_object_registry import EngineeringObjectRegistry
from src.reinforcement.engineering_object_creation_validator import (
    EngineeringObjectCreationValidator,
)
from src.reinforcement.engineering_semantic_role_builder import EngineeringSemanticRoleBuilder
from src.reinforcement.engineering_semantic_role_validator import (
    EngineeringSemanticRoleValidator,
)
from src.reinforcement.engineering_semantic_relationship_builder import (
    EngineeringSemanticRelationshipBuilder,
)
from src.reinforcement.engineering_semantic_relationship_validator import (
    EngineeringSemanticRelationshipValidator,
)
from src.reinforcement.engineering_object_instantiator import EngineeringObjectInstantiator
from src.reinforcement.engineering_object_validator import EngineeringObjectValidator
from src.reinforcement.engineering_relationships import EngineeringRelationships
from src.reinforcement.engineering_asset_registry import EngineeringAssetRegistry
from src.reinforcement.engineering_asset_registry_validator import (
    EngineeringAssetRegistryValidator,
)
from src.reinforcement.engineering_reinforcement_context import (
    format_engineering_results_id,
)
from src.reinforcement.engineering_reinforcement_context_registry import (
    EngineeringReinforcementContextRegistry,
)
from src.reinforcement.engineering_reinforcement_context_validator import (
    EngineeringReinforcementContextValidator,
)
from src.reinforcement.engineering_reinforcement_lifecycle_registry import (
    EngineeringReinforcementLifecycleRegistry,
)
from src.reinforcement.engineering_reinforcement_lifecycle_validator import (
    EngineeringReinforcementLifecycleValidator,
)
from src.reinforcement.engineering_reinforcement_state_machine import (
    format_erc_lifecycle_id,
)
from src.reinforcement.ownership_resolver import OwnershipResolver
from src.reinforcement.beam_match_validator import BeamMatchValidator
from src.reinforcement.match_decision_validator import MatchDecisionValidator
from src.reinforcement.reinforcement_drawing_validator import ReinforcementDrawingValidator


PHASE = "Phase G.5.1"
MODEL_VERSION = "5.1"


@dataclass
class ReinforcementDrawingModel:
    """Authoritative geometry model for a reinforcement drawing."""

    drawing_id: str
    drawing_set_id: str
    floor_id: str
    floor_slug: str
    source_file: str
    regions: List[dict[str, Any]] = field(default_factory=list)
    detail_contexts: List[dict[str, Any]] = field(default_factory=list)
    detail_identities: List[dict[str, Any]] = field(default_factory=list)
    detail_fingerprints: List[dict[str, Any]] = field(default_factory=list)
    beam_match_candidates: List[dict[str, Any]] = field(default_factory=list)
    match_decisions: List[dict[str, Any]] = field(default_factory=list)
    beam_matches: List[dict[str, Any]] = field(default_factory=list)
    engineering_reinforcement_contexts: List[dict[str, Any]] = field(default_factory=list)
    detail_views: List[dict[str, Any]] = field(default_factory=list)
    sketches: List[dict[str, Any]] = field(default_factory=list)
    text_objects: List[dict[str, Any]] = field(default_factory=list)
    leaders: List[dict[str, Any]] = field(default_factory=list)
    blocks: List[dict[str, Any]] = field(default_factory=list)
    relationships: List[dict[str, Any]] = field(default_factory=list)
    detail_context_relationships: List[dict[str, Any]] = field(default_factory=list)
    detail_identity_relationships: List[dict[str, Any]] = field(default_factory=list)
    candidate_relationships: List[dict[str, Any]] = field(default_factory=list)
    decision_relationships: List[dict[str, Any]] = field(default_factory=list)
    quality_relationships: List[dict[str, Any]] = field(default_factory=list)
    match_relationships: List[dict[str, Any]] = field(default_factory=list)
    ownership_relationships: List[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "creation_timestamp": datetime.now(timezone.utc).isoformat(),
            "drawing_id": self.drawing_id,
            "drawing_set_id": self.drawing_set_id,
            "floor_id": self.floor_id,
            "floor_slug": self.floor_slug,
            "source_file": self.source_file,
            "region_count": len(self.regions),
            "detail_context_count": len(self.detail_contexts),
            "detail_identity_count": len(self.detail_identities),
            "detail_fingerprint_count": len(self.detail_fingerprints),
            "beam_match_candidate_count": len(self.beam_match_candidates),
            "match_decision_count": len(self.match_decisions),
            "beam_match_count": len(self.beam_matches),
            "engineering_reinforcement_context_count": len(self.engineering_reinforcement_contexts),
            "detail_view_count": len(self.detail_views),
            "sketch_count": len(self.sketches),
            "text_count": len(self.text_objects),
            "leader_count": len(self.leaders),
            "block_count": len(self.blocks),
            "relationship_count": len(self.relationships),
            "detail_context_relationship_count": len(self.detail_context_relationships),
            "detail_identity_relationship_count": len(self.detail_identity_relationships),
            "candidate_relationship_count": len(self.candidate_relationships),
            "decision_relationship_count": len(self.decision_relationships),
            "quality_relationship_count": len(self.quality_relationships),
            "match_relationship_count": len(self.match_relationships),
            "ownership_relationship_count": len(self.ownership_relationships),
            "regions": list(self.regions),
            "detail_contexts": list(self.detail_contexts),
            "detail_identities": list(self.detail_identities),
            "detail_fingerprints": list(self.detail_fingerprints),
            "beam_match_candidates": list(self.beam_match_candidates),
            "match_decisions": list(self.match_decisions),
            "beam_matches": list(self.beam_matches),
            "engineering_reinforcement_contexts": list(self.engineering_reinforcement_contexts),
            "detail_views": list(self.detail_views),
            "sketches": list(self.sketches),
            "text_objects": list(self.text_objects),
            "leaders": list(self.leaders),
            "blocks": list(self.blocks),
            "relationships": list(self.relationships),
            "detail_context_relationships": list(self.detail_context_relationships),
            "detail_identity_relationships": list(self.detail_identity_relationships),
            "candidate_relationships": list(self.candidate_relationships),
            "decision_relationships": list(self.decision_relationships),
            "quality_relationships": list(self.quality_relationships),
            "match_relationships": list(self.match_relationships),
            "ownership_relationships": list(self.ownership_relationships),
        }


class ReinforcementDrawingBuilder:
    """Build reinforcement drawing models and enrich project state."""

    def __init__(self, config: dict[str, Any]) -> None:
        g2 = config.get("reinforcement_geometry", {})
        self._enabled = bool(g2.get("enable", True))
        dc_cfg = g2.get("detail_context", {})
        if isinstance(dc_cfg, dict):
            enabled = dc_cfg.get("enable", True)
        else:
            enabled = g2.get("detail_context_enable", True)
        self._detail_context_enabled = bool(enabled)
        self._detail_identity_enabled = bool(g2.get("detail_identity_enable", True))
        self._beam_candidate_enabled = bool(g2.get("beam_candidate_enable", True))
        self._match_decision_enabled = bool(g2.get("match_decision_enable", True))
        self._match_decision_quality_enabled = bool(g2.get("match_decision_quality_enable", True))
        self._beam_matching_enabled = bool(g2.get("beam_matching_enable", True))
        self._ownership_resolver_enabled = bool(g2.get("ownership_resolver_enable", True))
        self._engineering_asset_registry_enabled = bool(
            g2.get("engineering_asset_registry_enable", True)
        )
        self._engineering_object_framework_enabled = bool(
            g2.get("engineering_object_framework_enable", True)
        )
        self._engineering_semantic_role_enabled = bool(
            g2.get("engineering_semantic_role_enable", True)
        )
        self._engineering_semantic_relationship_enabled = bool(
            g2.get("engineering_semantic_relationship_enable", True)
        )
        self._engineering_object_instantiation_enabled = bool(
            g2.get("engineering_object_instantiation_enable", True)
        )

    def build_model(self, model: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            logger.info("Reinforcement geometry intelligence disabled in config")
            return model

        drawing_models: List[dict[str, Any]] = []
        all_contexts: List[dict[str, Any]] = []
        all_identities: List[dict[str, Any]] = []
        all_fingerprints: List[dict[str, Any]] = []
        all_candidates: List[dict[str, Any]] = []
        all_rankings: List[dict[str, Any]] = []
        all_decisions: List[dict[str, Any]] = []
        all_matches: List[dict[str, Any]] = []
        all_ercs: List[dict[str, Any]] = []
        all_ownership_entries: List[dict[str, Any]] = []
        all_asset_registries: List[dict[str, Any]] = []

        for payload in model.get("reinforcement_geometry_payloads", []):
            drawing_model = self._assemble_drawing_model(model, payload)
            if self._detail_context_enabled:
                drawing_model = self._enrich_detail_contexts(drawing_model)
                all_contexts.extend(drawing_model.detail_contexts)
            if self._detail_identity_enabled and drawing_model.detail_contexts:
                drawing_model = self._enrich_detail_identities(drawing_model)
            if self._beam_candidate_enabled and drawing_model.detail_identities:
                drawing_model, rankings = self._enrich_beam_candidates(model, drawing_model)
                all_rankings.extend(rankings)
            if self._match_decision_enabled and drawing_model.detail_identities:
                drawing_model = self._enrich_match_decisions(drawing_model)
            if self._match_decision_quality_enabled and drawing_model.match_decisions:
                drawing_model = self._enrich_match_decision_quality(drawing_model)
            if self._beam_matching_enabled and drawing_model.match_decisions:
                drawing_model = self._enrich_beam_matches(model, drawing_model)
            if self._ownership_resolver_enabled and drawing_model.beam_matches:
                drawing_model, ownership_entries = self._enrich_ownership_resolution(
                    model, drawing_model
                )
                all_ownership_entries.extend(ownership_entries)
            if (
                self._engineering_asset_registry_enabled
                and drawing_model.engineering_reinforcement_contexts
            ):
                drawing_model, asset_registries = self._enrich_engineering_assets(drawing_model)
                all_asset_registries.extend(asset_registries)
            if (
                self._engineering_object_framework_enabled
                and drawing_model.engineering_reinforcement_contexts
            ):
                drawing_model = self._enrich_engineering_objects(drawing_model)
            all_identities.extend(drawing_model.detail_identities)
            all_fingerprints.extend(drawing_model.detail_fingerprints)
            all_candidates.extend(drawing_model.beam_match_candidates)
            all_decisions.extend(drawing_model.match_decisions)
            all_matches.extend(drawing_model.beam_matches)
            all_ercs.extend(drawing_model.engineering_reinforcement_contexts)

            drawing_models.append(drawing_model.to_dict())
            self._populate_workspace(model, payload, drawing_model)
            self._update_drawing_registry(model, drawing_model)

        model["reinforcement_drawing_models"] = drawing_models
        if drawing_models:
            model["reinforcement_drawing_model"] = drawing_models[0]

        if all_contexts and drawing_models:
            primary = drawing_models[0]
            model["detail_context_registry"] = DetailContextRegistry.build(
                all_contexts,
                drawing_id=primary.get("drawing_id", ""),
                floor_id=primary.get("floor_id", ""),
            )
            self._enrich_drawing_sets(model, drawing_models, model["detail_context_registry"])

        if all_identities and drawing_models:
            primary = drawing_models[0]
            model["detail_identity_registry"] = DetailIdentityRegistry.build_identities(
                all_identities,
                drawing_id=primary.get("drawing_id", ""),
                floor_id=primary.get("floor_id", ""),
            )
            model["detail_fingerprint_registry"] = DetailIdentityRegistry.build_fingerprints(
                all_fingerprints,
                drawing_id=primary.get("drawing_id", ""),
                floor_id=primary.get("floor_id", ""),
            )
            self._enrich_drawing_sets_identities(
                model,
                drawing_models,
                model["detail_identity_registry"],
                model["detail_fingerprint_registry"],
            )

        if all_candidates and drawing_models:
            primary = drawing_models[0]
            model["beam_candidate_registry"] = BeamCandidateRegistry.build(
                all_candidates,
                drawing_id=primary.get("drawing_id", ""),
                drawing_set_id=primary.get("drawing_set_id", ""),
                floor_id=primary.get("floor_id", ""),
            )
            model["beam_candidate_ranking"] = {
                "phase": PHASE,
                "rankings": all_rankings,
            }
            model["candidate_graph"] = self._build_candidate_graph(
                all_candidates,
                drawing_models,
            )
            self._enrich_drawing_sets_candidates(
                model,
                drawing_models,
                model["beam_candidate_registry"],
            )

        if all_decisions and drawing_models:
            primary = drawing_models[0]
            model["match_decision_registry"] = MatchDecisionRegistry.build(
                all_decisions,
                drawing_id=primary.get("drawing_id", ""),
                drawing_set_id=primary.get("drawing_set_id", ""),
                floor_id=primary.get("floor_id", ""),
            )
            model["match_decision_graph"] = self._build_match_decision_graph(
                all_decisions,
                drawing_models,
            )
            self._enrich_drawing_sets_decisions(
                model,
                drawing_models,
                model["match_decision_registry"],
            )
            model["match_decision_quality_registry"] = MatchDecisionQualityRegistry.build_registry(
                all_decisions
            )
            model["decision_algorithm"] = MatchDecisionQualityRegistry.build_algorithm_export()
            self._enrich_drawing_sets_quality(model, drawing_models, all_decisions)
            self._enrich_project_workspace_quality(model, all_decisions)

        if all_matches and drawing_models:
            primary = drawing_models[0]
            project_id = str(model.get("project_workspace", {}).get("project_id", ""))
            model["beam_matches"] = all_matches
            model["beam_match_registry"] = BeamMatchRegistry.build(
                all_matches,
                drawing_id=primary.get("drawing_id", ""),
                drawing_set_id=primary.get("drawing_set_id", ""),
                floor_id=primary.get("floor_id", ""),
                project_id=project_id,
            )
            model["beam_matching_summary"] = BeamMatchRegistry.build_summary_export(
                all_matches,
                all_decisions,
            )
            model["beam_match_graph"] = self._build_beam_match_graph(
                all_matches,
                drawing_models,
            )
            self._enrich_drawing_sets_beam_matches(
                model,
                drawing_models,
                model["beam_match_registry"],
            )
            self._enrich_project_workspace_beam_matches(
                model,
                all_matches,
                all_decisions,
            )

        if all_ercs and drawing_models:
            primary = drawing_models[0]
            project_id = str(model.get("project_workspace", {}).get("project_id", ""))
            model["engineering_reinforcement_contexts"] = all_ercs
            model["engineering_reinforcement_context_registry"] = (
                EngineeringReinforcementContextRegistry.build_registry(
                    all_ercs,
                    drawing_id=primary.get("drawing_id", ""),
                    drawing_set_id=primary.get("drawing_set_id", ""),
                    floor_id=primary.get("floor_id", ""),
                    project_id=project_id,
                )
            )
            model["ownership_registry"] = (
                EngineeringReinforcementContextRegistry.build_ownership_registry(
                    all_ownership_entries
                )
            )
            model["ownership_summary"] = (
                EngineeringReinforcementContextRegistry.build_ownership_summary(
                    all_ercs,
                    all_ownership_entries,
                )
            )
            model["erc_ownership_graph"] = self._build_erc_ownership_graph(
                all_ercs,
                drawing_models,
            )
            model["ownership_relationships"] = [
                rel
                for dm in drawing_models
                for rel in dm.get("ownership_relationships", [])
            ]
            self._enrich_drawing_sets_ownership(
                model,
                drawing_models,
                model["engineering_reinforcement_context_registry"],
                model["ownership_summary"],
            )
            self._enrich_project_workspace_ownership(
                model,
                all_ercs,
                all_ownership_entries,
            )

        if all_ercs and all_asset_registries and drawing_models:
            primary = drawing_models[0]
            project_id = str(model.get("project_workspace", {}).get("project_id", ""))
            model["engineering_asset_registry"] = EngineeringAssetRegistry.build_project_registry(
                all_asset_registries,
                drawing_id=primary.get("drawing_id", ""),
                drawing_set_id=primary.get("drawing_set_id", ""),
                floor_id=primary.get("floor_id", ""),
                project_id=project_id,
            )
            model["engineering_asset_summary"] = EngineeringAssetRegistry.build_summary(
                all_asset_registries
            )
            model["engineering_result_summary"] = (
                EngineeringAssetRegistry.build_engineering_result_summary()
            )
            model["engineering_reinforcement_lifecycle_registry"] = (
                EngineeringReinforcementLifecycleRegistry.build_registry(all_ercs)
            )
            model["lifecycle_summary"] = EngineeringReinforcementLifecycleRegistry.build_summary(
                all_ercs
            )
            self._enrich_drawing_sets_assets(
                model,
                drawing_models,
                model["engineering_asset_registry"],
                model["engineering_result_summary"],
                model["lifecycle_summary"],
            )
            self._enrich_project_workspace_assets(
                model,
                model["engineering_asset_registry"],
                model["engineering_result_summary"],
                model["lifecycle_summary"],
            )

        if (
            all_ercs
            and drawing_models
            and self._engineering_object_framework_enabled
            and all_ercs[0].get("engineering_objects") is not None
        ):
            primary = drawing_models[0]
            project_id = str(model.get("project_workspace", {}).get("project_id", ""))
            model["engineering_object_registry"] = EngineeringObjectRegistry.build_project_registry(
                all_ercs,
                objects=[],
                drawing_id=primary.get("drawing_id", ""),
                drawing_set_id=primary.get("drawing_set_id", ""),
                floor_id=primary.get("floor_id", ""),
                project_id=project_id,
            )
            model["engineering_object_graph"] = EngineeringObjectGraph.build(
                all_ercs,
                drawing_models,
                project_id=project_id,
                objects=[],
            )
            model["engineering_object_relationships"] = EngineeringRelationships.build_export()
            model["engineering_object_lifecycle_registry"] = (
                EngineeringObjectLifecycle.build_project_registry(all_ercs)
            )
            model["engineering_object_summary"] = EngineeringObjectRegistry.build_summary(
                all_ercs,
                objects=[],
            )
            self._enrich_drawing_sets_engineering_objects(
                model,
                drawing_models,
                model["engineering_object_registry"],
                model["engineering_object_summary"],
            )
            self._enrich_project_workspace_engineering_objects(
                model,
                model["engineering_object_registry"],
                model["engineering_object_summary"],
            )

        if (
            self._engineering_semantic_role_enabled
            and all_ercs
            and drawing_models
            and all_ercs[0].get("engineering_objects") is not None
        ):
            primary = drawing_models[0]
            project_id = str(model.get("project_workspace", {}).get("project_id", ""))
            role_builder = EngineeringSemanticRoleBuilder()
            enriched_ercs, role_registry, _ = role_builder.build(all_ercs, primary)
            all_ercs = enriched_ercs
            model["engineering_reinforcement_contexts"] = all_ercs
            for dm in drawing_models:
                dm["engineering_reinforcement_contexts"] = enriched_ercs
            g50_exports = EngineeringSemanticRoleBuilder.build_project_exports(
                enriched_ercs,
                role_registry,
                drawing_models,
                project_id=project_id,
            )
            model.update(g50_exports)
            self._enrich_drawing_sets_semantic_roles(
                model,
                drawing_models,
                model["engineering_semantic_role_registry"],
                model["engineering_semantic_role_summary"],
            )
            self._enrich_project_workspace_semantic_roles(
                model,
                model["engineering_semantic_role_registry"],
                model["engineering_semantic_role_summary"],
            )

        if (
            self._engineering_semantic_relationship_enabled
            and all_ercs
            and drawing_models
            and all_ercs[0].get("semantic_roles")
        ):
            primary = drawing_models[0]
            project_id = str(model.get("project_workspace", {}).get("project_id", ""))
            role_list = model.get("engineering_semantic_role_registry", {}).get("roles", [])
            rel_builder = EngineeringSemanticRelationshipBuilder()
            enriched_ercs, rel_registry = rel_builder.build(all_ercs, role_list, primary)
            all_ercs = enriched_ercs
            model["engineering_reinforcement_contexts"] = all_ercs
            for dm in drawing_models:
                dm["engineering_reinforcement_contexts"] = enriched_ercs
            g501_exports = EngineeringSemanticRelationshipBuilder.build_project_exports(
                enriched_ercs,
                rel_registry,
                role_list,
                drawing_models,
                project_id=project_id,
            )
            model.update(g501_exports)
            self._enrich_drawing_sets_semantic_relationships(
                model,
                drawing_models,
                model["engineering_semantic_relationship_registry"],
                model["engineering_semantic_relationship_summary"],
            )
            self._enrich_project_workspace_semantic_relationships(
                model,
                model["engineering_semantic_relationship_registry"],
                model["engineering_semantic_relationship_summary"],
            )

        if (
            self._engineering_object_instantiation_enabled
            and all_ercs
            and drawing_models
            and all_ercs[0].get("engineering_objects") is not None
        ):
            primary = drawing_models[0]
            project_id = str(model.get("project_workspace", {}).get("project_id", ""))
            semantic_registry = model.get("engineering_semantic_role_registry")
            enriched_ercs, obj_registry, relationships, class_export, _, _ = (
                EngineeringObjectInstantiator().build(
                    all_ercs,
                    primary,
                    semantic_role_registry=semantic_registry,
                )
            )
            all_ercs = enriched_ercs
            model["engineering_reinforcement_contexts"] = all_ercs
            for dm in drawing_models:
                dm["engineering_reinforcement_contexts"] = enriched_ercs
            g51_exports = EngineeringObjectInstantiator.build_project_exports(
                enriched_ercs,
                obj_registry,
                relationships,
                class_export,
                drawing_models,
                project_id=project_id,
            )
            model.update(g51_exports)
            model["engineering_objects"] = obj_registry.all_objects()
            self._enrich_drawing_sets_engineering_objects(
                model,
                drawing_models,
                model["engineering_object_registry"],
                model["engineering_object_summary"],
            )
            self._enrich_project_workspace_engineering_objects(
                model,
                model["engineering_object_registry"],
                model["engineering_object_summary"],
            )

        self._update_project_graph(model, drawing_models)

        g22_validation = ReinforcementDrawingValidator().validate(model, drawing_models)
        model["reinforcement_drawing_validation"] = g22_validation

        g23_validation = DetailContextValidator().validate(model)
        model["detail_context_validation"] = g23_validation

        g24_validation = DetailIdentityValidator().validate(model)
        model["detail_identity_validation"] = g24_validation

        g25_validation = BeamCandidateValidator().validate(model)
        model["beam_candidate_validation"] = g25_validation

        g26_validation = MatchDecisionValidator().validate(model)
        model["match_decision_validation"] = g26_validation

        g27_validation = MatchDecisionQualityValidator().validate(model)
        model["match_decision_quality_validation"] = g27_validation

        g3_validation = BeamMatchValidator().validate(model)
        model["beam_match_validation"] = g3_validation

        g4_validation = EngineeringReinforcementContextValidator().validate(model)
        model["engineering_reinforcement_context_validation"] = g4_validation

        g41_asset_validation = EngineeringAssetRegistryValidator().validate(model)
        model["engineering_asset_validation"] = g41_asset_validation

        g41_lifecycle_validation = EngineeringReinforcementLifecycleValidator().validate(model)
        model["engineering_reinforcement_lifecycle_validation"] = g41_lifecycle_validation

        g42_object_validation = EngineeringObjectValidator().validate(model)
        model["engineering_object_validation"] = g42_object_validation

        g50_role_validation = EngineeringSemanticRoleValidator().validate(model)
        model["engineering_semantic_role_validation"] = g50_role_validation

        g501_rel_validation = EngineeringSemanticRelationshipValidator().validate(model)
        model["engineering_semantic_relationship_validation"] = g501_rel_validation

        g51_creation_validation = EngineeringObjectCreationValidator().validate(model)
        model["engineering_object_creation_validation"] = g51_creation_validation

        model["phase_g"] = PHASE
        model["phase"] = PHASE
        model["model_version"] = MODEL_VERSION

        manager = dict(model.get("workspace_manager", {}))
        manager["reinforcement_geometry_complete"] = g22_validation.get("status") == "PASS"
        manager["detail_context_complete"] = g23_validation.get("status") == "PASS"
        manager["detail_identity_complete"] = g24_validation.get("status") == "PASS"
        manager["beam_candidate_complete"] = g25_validation.get("status") == "PASS"
        manager["match_decision_complete"] = g26_validation.get("status") == "PASS"
        manager["match_decision_quality_complete"] = g27_validation.get("status") == "PASS"
        manager["beam_matching_complete"] = g3_validation.get("status") == "PASS"
        manager["ownership_resolver_complete"] = g4_validation.get("status") == "PASS"
        manager["engineering_asset_registry_complete"] = (
            g41_asset_validation.get("status") == "PASS"
        )
        manager["engineering_reinforcement_lifecycle_complete"] = (
            g41_lifecycle_validation.get("status") == "PASS"
        )
        manager["engineering_object_framework_complete"] = (
            g42_object_validation.get("status") == "PASS"
            or g42_object_validation.get("status") == "SKIP"
        )
        manager["engineering_semantic_role_complete"] = (
            g50_role_validation.get("status") == "PASS"
            or g50_role_validation.get("status") == "SKIP"
        )
        manager["engineering_semantic_relationship_complete"] = (
            g501_rel_validation.get("status") == "PASS"
            or g501_rel_validation.get("status") == "SKIP"
        )
        manager["engineering_object_instantiation_complete"] = (
            g51_creation_validation.get("status") == "PASS"
        )
        manager["beam_match_count"] = len(model.get("beam_matches", []))
        manager["engineering_reinforcement_context_count"] = len(
            model.get("engineering_reinforcement_contexts", [])
        )
        manager["reinforcement_region_count"] = sum(
            dm.get("region_count", 0) for dm in drawing_models
        )
        manager["detail_context_count"] = sum(
            dm.get("detail_context_count", 0) for dm in drawing_models
        )
        manager["detail_identity_count"] = sum(
            dm.get("detail_identity_count", 0) for dm in drawing_models
        )
        manager["beam_match_candidate_count"] = sum(
            dm.get("beam_match_candidate_count", 0) for dm in drawing_models
        )
        manager["match_decision_count"] = sum(
            dm.get("match_decision_count", 0) for dm in drawing_models
        )
        manager["phase"] = PHASE
        model["workspace_manager"] = manager

        logger.info(
            "Reinforcement drawing models — count={}, regions={}, contexts={}, identities={}, candidates={}, decisions={}, matches={}, ercs={}",
            len(drawing_models),
            sum(dm.get("region_count", 0) for dm in drawing_models),
            sum(dm.get("detail_context_count", 0) for dm in drawing_models),
            sum(dm.get("detail_identity_count", 0) for dm in drawing_models),
            sum(dm.get("beam_match_candidate_count", 0) for dm in drawing_models),
            sum(dm.get("match_decision_count", 0) for dm in drawing_models),
            sum(dm.get("beam_match_count", 0) for dm in drawing_models),
            sum(dm.get("engineering_reinforcement_context_count", 0) for dm in drawing_models),
        )
        return model

    def _enrich_match_decision_quality(
        self,
        drawing_model: ReinforcementDrawingModel,
    ) -> ReinforcementDrawingModel:
        enriched, rels = MatchDecisionQualityBuilder().build(drawing_model.match_decisions)
        drawing_model.match_decisions = enriched
        drawing_model.quality_relationships = rels
        drawing_model.relationships = list(drawing_model.relationships) + rels
        return drawing_model

    def _enrich_beam_matches(
        self,
        model: dict[str, Any],
        drawing_model: ReinforcementDrawingModel,
    ) -> ReinforcementDrawingModel:
        matches, identities, decisions, _contexts, rels = BeamMatchBuilder().build(
            model,
            drawing_model.drawing_set_id,
            drawing_model.floor_id,
            drawing_model.drawing_id,
            drawing_model.detail_identities,
            drawing_model.match_decisions,
            drawing_model.beam_match_candidates,
        )
        drawing_model.detail_identities = identities
        drawing_model.match_decisions = decisions
        drawing_model.beam_matches = matches
        drawing_model.match_relationships = rels
        drawing_model.relationships = list(drawing_model.relationships) + rels
        return drawing_model

    def _enrich_ownership_resolution(
        self,
        model: dict[str, Any],
        drawing_model: ReinforcementDrawingModel,
    ) -> tuple[ReinforcementDrawingModel, List[dict[str, Any]]]:
        (
            contexts,
            identities,
            views,
            sketches,
            text_objects,
            leaders,
            blocks,
            rels,
            ownership_entries,
        ) = OwnershipResolver().build(
            model,
            drawing_model.drawing_set_id,
            drawing_model.floor_id,
            drawing_model.drawing_id,
            drawing_model.beam_matches,
            drawing_model.detail_contexts,
            drawing_model.detail_identities,
            drawing_model.detail_views,
            drawing_model.sketches,
            drawing_model.text_objects,
            drawing_model.leaders,
            drawing_model.blocks,
            drawing_model.regions,
            drawing_model.relationships,
        )
        drawing_model.engineering_reinforcement_contexts = contexts
        drawing_model.detail_identities = identities
        drawing_model.detail_views = views
        drawing_model.sketches = sketches
        drawing_model.text_objects = text_objects
        drawing_model.leaders = leaders
        drawing_model.blocks = blocks
        drawing_model.ownership_relationships = rels
        return drawing_model, ownership_entries

    def _enrich_engineering_assets(
        self,
        drawing_model: ReinforcementDrawingModel,
    ) -> tuple[ReinforcementDrawingModel, List[dict[str, Any]]]:
        enriched, registries = EngineeringAssetRegistry.enrich_contexts(
            drawing_model.engineering_reinforcement_contexts
        )
        drawing_model.engineering_reinforcement_contexts = enriched
        return drawing_model, registries

    def _enrich_engineering_objects(
        self,
        drawing_model: ReinforcementDrawingModel,
    ) -> ReinforcementDrawingModel:
        drawing_model.engineering_reinforcement_contexts = (
            EngineeringObjectRegistry.enrich_contexts(
                drawing_model.engineering_reinforcement_contexts
            )
        )
        return drawing_model

    @staticmethod
    def _build_erc_ownership_graph(
        contexts: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
    ) -> dict[str, Any]:
        nodes = [
            {
                "id": c.get("reinforcement_context_id"),
                "type": "ENGINEERING_REINFORCEMENT_CONTEXT",
                "beam_mark": c.get("beam_mark"),
                "beam_context_id": c.get("beam_context_id"),
            }
            for c in contexts
        ]
        edges = []
        for dm in drawing_models:
            for rel in dm.get("ownership_relationships", []):
                rel_name = str(rel.get("relationship", ""))
                if rel_name == "BEAM_MATCH_CREATES_ERC":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "CREATES",
                        }
                    )
                elif rel_name == "BEAM_CONTEXT_HAS_REINFORCEMENT_CONTEXT":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "HAS_REINFORCEMENT_CONTEXT",
                        }
                    )
                elif rel_name == "ERC_OWNS_VIEW":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "OWNS_VIEW",
                        }
                    )
                elif rel_name == "ERC_OWNS_GEOMETRY":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "OWNS_GEOMETRY",
                        }
                    )
                elif rel_name == "ERC_OWNS_TEXT":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "OWNS_TEXT",
                        }
                    )
                elif rel_name == "ERC_OWNS_LEADER":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "OWNS_LEADER",
                        }
                    )
                elif rel_name == "ERC_OWNS_BLOCK":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "OWNS_BLOCK",
                        }
                    )
        return {
            "phase": PHASE,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def _enrich_drawing_sets_ownership(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        erc_registry: dict[str, Any],
        ownership_summary: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["engineering_reinforcement_context_registry"] = erc_registry
                ds["ownership_summary"] = ownership_summary
                ds["ownership_status"] = ownership_summary.get("ownership_status", "RESOLVED")

    def _enrich_project_workspace_ownership(
        self,
        model: dict[str, Any],
        contexts: List[dict[str, Any]],
        ownership_entries: List[dict[str, Any]],
    ) -> None:
        project = dict(model.get("project_workspace", {}))
        project["engineering_reinforcement_context_registry"] = model.get(
            "engineering_reinforcement_context_registry", {}
        )
        project["ownership_summary"] = EngineeringReinforcementContextRegistry.build_ownership_summary(
            contexts,
            ownership_entries,
        )
        model["project_workspace"] = project

    def _enrich_drawing_sets_assets(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        asset_registry: dict[str, Any],
        engineering_result_summary: dict[str, Any],
        lifecycle_summary: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["asset_registry"] = asset_registry
                ds["asset_registry_count"] = asset_registry.get("registry_count", 0)
                ds["engineering_result_summary"] = engineering_result_summary
                ds["lifecycle_summary"] = lifecycle_summary

    def _enrich_project_workspace_assets(
        self,
        model: dict[str, Any],
        asset_registry: dict[str, Any],
        engineering_result_summary: dict[str, Any],
        lifecycle_summary: dict[str, Any],
    ) -> None:
        project = dict(model.get("project_workspace", {}))
        project["asset_registry"] = asset_registry
        project["asset_registry_count"] = asset_registry.get("registry_count", 0)
        project["engineering_result_summary"] = engineering_result_summary
        project["lifecycle_summary"] = lifecycle_summary
        model["project_workspace"] = project

    def _enrich_drawing_sets_engineering_objects(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        object_registry: dict[str, Any],
        object_summary: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["engineering_object_registry"] = object_registry
                ds["engineering_object_summary"] = object_summary

    def _enrich_project_workspace_engineering_objects(
        self,
        model: dict[str, Any],
        object_registry: dict[str, Any],
        object_summary: dict[str, Any],
    ) -> None:
        project = dict(model.get("project_workspace", {}))
        project["engineering_object_registry"] = object_registry
        project["engineering_object_summary"] = object_summary
        model["project_workspace"] = project

    def _enrich_drawing_sets_semantic_roles(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        role_registry: dict[str, Any],
        role_summary: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["semantic_role_registry"] = role_registry
                ds["semantic_role_summary"] = role_summary

    def _enrich_project_workspace_semantic_roles(
        self,
        model: dict[str, Any],
        role_registry: dict[str, Any],
        role_summary: dict[str, Any],
    ) -> None:
        project = dict(model.get("project_workspace", {}))
        project["semantic_role_registry"] = role_registry
        project["semantic_role_summary"] = role_summary
        model["project_workspace"] = project

    def _enrich_drawing_sets_semantic_relationships(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        rel_registry: dict[str, Any],
        rel_summary: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["semantic_relationship_registry"] = rel_registry
                ds["semantic_relationship_summary"] = rel_summary

    def _enrich_project_workspace_semantic_relationships(
        self,
        model: dict[str, Any],
        rel_registry: dict[str, Any],
        rel_summary: dict[str, Any],
    ) -> None:
        project = dict(model.get("project_workspace", {}))
        project["semantic_relationship_registry"] = rel_registry
        project["semantic_relationship_summary"] = rel_summary
        model["project_workspace"] = project

    @staticmethod
    def _build_beam_match_graph(
        beam_matches: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
    ) -> dict[str, Any]:
        nodes = [
            {
                "id": m.get("beam_match_id"),
                "type": "BEAM_MATCH",
                "detail_identity_id": m.get("detail_identity_id"),
                "beam_context_id": m.get("beam_context_id"),
            }
            for m in beam_matches
        ]
        edges = []
        for dm in drawing_models:
            for rel in dm.get("match_relationships", []):
                rel_name = str(rel.get("relationship", ""))
                if rel_name == "DETAIL_MATCHED_TO":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "MATCHED_TO",
                        }
                    )
                elif rel_name == "BEAM_MATCH_REFERENCES":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "REFERENCES",
                        }
                    )
                elif rel_name == "BEAM_MATCH_TARGETS":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "TARGETS",
                        }
                    )
                elif rel_name == "BEAM_CONTEXT_HAS_REINFORCEMENT_MATCH":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "HAS_REINFORCEMENT_MATCH",
                        }
                    )
        return {
            "phase": PHASE,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def _enrich_drawing_sets_beam_matches(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        beam_match_registry: dict[str, Any],
    ) -> None:
        from src.project.drawing_set_state_machine import MATCHING_COMPLETED
        from src.reinforcement.beam_match import MATCHING_PROGRESS_COMPLETE

        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["beam_match_registry"] = beam_match_registry
                ds["matched_beam_count"] = beam_match_registry.get("matched_beam_count", 0)
                ds["matching_progress"] = MATCHING_PROGRESS_COMPLETE
                ds["matching_state"] = MATCHING_COMPLETED
                ds["beam_matching_context"] = {
                    "match_count": beam_match_registry.get("match_count", 0),
                    "matched_beam_count": beam_match_registry.get("matched_beam_count", 0),
                    "matching_progress": MATCHING_PROGRESS_COMPLETE,
                }

    def _enrich_project_workspace_beam_matches(
        self,
        model: dict[str, Any],
        beam_matches: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
    ) -> None:
        project = dict(model.get("project_workspace", {}))
        project["beam_match_registry"] = model.get("beam_match_registry", {})
        project["matching_summary"] = BeamMatchRegistry.build_summary_export(
            beam_matches,
            decisions,
        )
        model["project_workspace"] = project

    def _enrich_match_decisions(
        self,
        drawing_model: ReinforcementDrawingModel,
    ) -> ReinforcementDrawingModel:
        decisions, updated_identities, rels = MatchDecisionBuilder().build(
            drawing_model.drawing_set_id,
            drawing_model.floor_id,
            drawing_model.drawing_id,
            drawing_model.detail_identities,
            drawing_model.beam_match_candidates,
        )
        drawing_model.detail_identities = updated_identities
        drawing_model.match_decisions = decisions
        drawing_model.decision_relationships = rels
        drawing_model.relationships = list(drawing_model.relationships) + rels
        return drawing_model

    @staticmethod
    def _build_match_decision_graph(
        decisions: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
    ) -> dict[str, Any]:
        nodes = [
            {
                "id": d.get("decision_id"),
                "type": "MATCH_DECISION",
                "detail_identity_id": d.get("detail_identity_id"),
                "recommended_candidate_id": d.get("recommended_candidate_id"),
            }
            for d in decisions
        ]
        edges = []
        for dm in drawing_models:
            for rel in dm.get("decision_relationships", []):
                rel_name = str(rel.get("relationship", ""))
                if rel_name == "DETAIL_HAS_MATCH_DECISION":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "HAS_MATCH_DECISION",
                        }
                    )
                elif rel_name == "MATCH_DECISION_RECOMMENDS_CANDIDATE":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "RECOMMENDS",
                        }
                    )
                elif rel_name == "MATCH_DECISION_BELONGS_TO_DRAWING_SET":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "BELONGS_TO",
                        }
                    )
        return {
            "phase": PHASE,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def _enrich_beam_candidates(
        self,
        model: dict[str, Any],
        drawing_model: ReinforcementDrawingModel,
    ) -> tuple[ReinforcementDrawingModel, List[dict[str, Any]]]:
        candidates, rels = BeamCandidateBuilder().build(
            model,
            drawing_model.drawing_id,
            drawing_model.drawing_set_id,
            drawing_model.floor_id,
            drawing_model.detail_identities,
        )
        ranked, rankings, updated_identities = BeamCandidateRanker().rank(
            candidates,
            drawing_model.detail_identities,
        )
        drawing_model.detail_identities = updated_identities
        drawing_model.beam_match_candidates = ranked
        drawing_model.candidate_relationships = rels
        drawing_model.relationships = list(drawing_model.relationships) + rels
        return drawing_model, rankings

    @staticmethod
    def _build_candidate_graph(
        candidates: List[dict[str, Any]],
        drawing_models: List[dict[str, Any]],
    ) -> dict[str, Any]:
        nodes = [
            {
                "id": c.get("candidate_id"),
                "type": "MATCH_CANDIDATE",
                "detail_identity_id": c.get("detail_identity_id"),
                "beam_context_id": c.get("beam_context_id"),
            }
            for c in candidates
        ]
        edges = []
        for dm in drawing_models:
            for rel in dm.get("candidate_relationships", []):
                rel_name = str(rel.get("relationship", ""))
                if rel_name == "DETAIL_HAS_CANDIDATE":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "HAS_CANDIDATE",
                        }
                    )
                elif rel_name == "CANDIDATE_TARGETS_CONTEXT":
                    edges.append(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "TARGETS",
                        }
                    )
        return {
            "phase": PHASE,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def _enrich_detail_identities(
        self,
        drawing_model: ReinforcementDrawingModel,
    ) -> ReinforcementDrawingModel:
        identities, contexts, id_rels = DetailIdentityBuilder().build(
            drawing_model.drawing_id,
            drawing_model.detail_contexts,
        )
        fingerprints = DetailFingerprintBuilder().build(
            identities,
            contexts,
            drawing_model.regions,
            drawing_model.detail_views,
        )
        fp_rels: List[dict[str, Any]] = []
        for ident, fp in zip(identities, fingerprints):
            fp_rels.append(
                {
                    "source_id": ident["detail_identity_id"],
                    "target_id": fp["fingerprint_id"],
                    "relationship": "DETAIL_HAS_FINGERPRINT",
                    "type": "ENGINEERING",
                }
            )

        drawing_model.detail_contexts = contexts
        drawing_model.detail_identities = identities
        drawing_model.detail_fingerprints = fingerprints
        drawing_model.detail_identity_relationships = id_rels + fp_rels
        drawing_model.relationships = (
            list(drawing_model.relationships) + id_rels + fp_rels
        )
        return drawing_model

    def _enrich_detail_contexts(
        self,
        drawing_model: ReinforcementDrawingModel,
    ) -> ReinforcementDrawingModel:
        contexts, regions, views, ctx_rels = DetailContextBuilder().build(
            drawing_model.drawing_id,
            drawing_model.regions,
            drawing_model.detail_views,
        )
        drawing_model.regions = regions
        drawing_model.detail_views = views
        drawing_model.detail_contexts = contexts
        drawing_model.detail_context_relationships = ctx_rels
        drawing_model.relationships = list(drawing_model.relationships) + ctx_rels
        return drawing_model

    def _assemble_drawing_model(
        self,
        model: dict[str, Any],
        payload: dict[str, Any],
    ) -> ReinforcementDrawingModel:
        floor_slug = str(payload.get("floor_slug", ""))
        floor_id = str(payload.get("floor_id", ""))
        drawing_id = self._drawing_id_for_floor(model, floor_id)
        drawing_set_id = self._drawing_set_id_for_floor(model, floor_id)

        return ReinforcementDrawingModel(
            drawing_id=drawing_id,
            drawing_set_id=drawing_set_id,
            floor_id=floor_id,
            floor_slug=floor_slug,
            source_file=str(payload.get("source_file", "")),
            regions=list(payload.get("regions", [])),
            detail_views=list(payload.get("detail_views", [])),
            sketches=list(payload.get("sketches", [])),
            text_objects=list(payload.get("text_objects", [])),
            leaders=list(payload.get("leaders", [])),
            blocks=list(payload.get("blocks", [])),
            relationships=list(payload.get("relationships", [])),
        )

    def _populate_workspace(
        self,
        model: dict[str, Any],
        payload: dict[str, Any],
        drawing_model: ReinforcementDrawingModel,
    ) -> None:
        floor_id = payload.get("floor_id")
        workspace_dict = None
        for ws in model.get("reinforcement_workspaces", []):
            if ws.get("floor_id") == floor_id:
                workspace_dict = ws
                break
        if not workspace_dict:
            return

        workspace_dict["regions"] = drawing_model.regions
        workspace_dict["detail_contexts"] = drawing_model.detail_contexts
        workspace_dict["detail_identities"] = drawing_model.detail_identities
        workspace_dict["detail_fingerprints"] = drawing_model.detail_fingerprints
        workspace_dict["detail_context_registry"] = DetailContextRegistry.build(
            drawing_model.detail_contexts,
            drawing_id=drawing_model.drawing_id,
            floor_id=drawing_model.floor_id,
        )
        workspace_dict["detail_identity_registry"] = DetailIdentityRegistry.build_identities(
            drawing_model.detail_identities,
            drawing_id=drawing_model.drawing_id,
            floor_id=drawing_model.floor_id,
        )
        workspace_dict["detail_fingerprint_registry"] = DetailIdentityRegistry.build_fingerprints(
            drawing_model.detail_fingerprints,
            drawing_id=drawing_model.drawing_id,
            floor_id=drawing_model.floor_id,
        )
        workspace_dict["beam_match_candidates"] = drawing_model.beam_match_candidates
        workspace_dict["beam_candidate_registry"] = BeamCandidateRegistry.build(
            drawing_model.beam_match_candidates,
            drawing_id=drawing_model.drawing_id,
            drawing_set_id=drawing_model.drawing_set_id,
            floor_id=drawing_model.floor_id,
        )
        workspace_dict["match_decisions"] = drawing_model.match_decisions
        workspace_dict["decision_registry"] = MatchDecisionRegistry.build(
            drawing_model.match_decisions,
            drawing_id=drawing_model.drawing_id,
            drawing_set_id=drawing_model.drawing_set_id,
            floor_id=drawing_model.floor_id,
        )
        workspace_dict["match_decision_quality_registry"] = (
            MatchDecisionQualityRegistry.build_registry(drawing_model.match_decisions)
        )
        workspace_dict["beam_matches"] = drawing_model.beam_matches
        workspace_dict["beam_match_registry"] = BeamMatchRegistry.build(
            drawing_model.beam_matches,
            drawing_id=drawing_model.drawing_id,
            drawing_set_id=drawing_model.drawing_set_id,
            floor_id=drawing_model.floor_id,
            project_id=str(model.get("project_workspace", {}).get("project_id", "")),
        )
        workspace_dict["engineering_reinforcement_contexts"] = (
            drawing_model.engineering_reinforcement_contexts
        )
        workspace_dict["engineering_reinforcement_context_registry"] = (
            EngineeringReinforcementContextRegistry.build_registry(
                drawing_model.engineering_reinforcement_contexts,
                drawing_id=drawing_model.drawing_id,
                drawing_set_id=drawing_model.drawing_set_id,
                floor_id=drawing_model.floor_id,
                project_id=str(model.get("project_workspace", {}).get("project_id", "")),
            )
        )
        if drawing_model.engineering_reinforcement_contexts and drawing_model.engineering_reinforcement_contexts[0].get(
            "engineering_assets"
        ):
            registries = [
                EngineeringAssetRegistry.build_from_erc(erc)
                for erc in drawing_model.engineering_reinforcement_contexts
            ]
            asset_registry = EngineeringAssetRegistry.build_project_registry(
                registries,
                drawing_id=drawing_model.drawing_id,
                drawing_set_id=drawing_model.drawing_set_id,
                floor_id=drawing_model.floor_id,
                project_id=str(model.get("project_workspace", {}).get("project_id", "")),
            )
            workspace_dict["asset_registry"] = asset_registry
            workspace_dict["asset_registry_count"] = asset_registry.get("registry_count", 0)
            workspace_dict["engineering_result_summary"] = (
                EngineeringAssetRegistry.build_engineering_result_summary()
            )
            workspace_dict["lifecycle_summary"] = (
                EngineeringReinforcementLifecycleRegistry.build_summary(
                    drawing_model.engineering_reinforcement_contexts
                )
            )
        if drawing_model.engineering_reinforcement_contexts and drawing_model.engineering_reinforcement_contexts[0].get(
            "engineering_objects"
        ):
            workspace_dict["engineering_object_registry"] = (
                EngineeringObjectRegistry.build_project_registry(
                    drawing_model.engineering_reinforcement_contexts,
                    objects=[],
                    drawing_id=drawing_model.drawing_id,
                    drawing_set_id=drawing_model.drawing_set_id,
                    floor_id=drawing_model.floor_id,
                    project_id=str(model.get("project_workspace", {}).get("project_id", "")),
                )
            )
            workspace_dict["engineering_object_summary"] = (
                EngineeringObjectRegistry.build_summary(
                    drawing_model.engineering_reinforcement_contexts,
                    objects=[],
                )
            )
        if drawing_model.engineering_reinforcement_contexts and drawing_model.engineering_reinforcement_contexts[0].get(
            "semantic_role_registry"
        ):
            workspace_dict["semantic_role_registry"] = {
                "role_count": sum(
                    len(c.get("semantic_roles", []))
                    for c in drawing_model.engineering_reinforcement_contexts
                ),
                "erc_count": len(drawing_model.engineering_reinforcement_contexts),
            }
        workspace_dict["detail_views"] = drawing_model.detail_views
        workspace_dict["sketches"] = drawing_model.sketches
        workspace_dict["text_objects"] = drawing_model.text_objects
        workspace_dict["leaders"] = drawing_model.leaders
        workspace_dict["blocks"] = drawing_model.blocks
        workspace_dict["relationships"] = drawing_model.relationships
        workspace_dict["detail_context_relationships"] = drawing_model.detail_context_relationships
        workspace_dict["detail_identity_relationships"] = drawing_model.detail_identity_relationships
        workspace_dict["reinforcement_drawing_model_id"] = drawing_model.drawing_id
        workspace_dict["geometry_status"] = "READY"

        project = model.get("project_workspace", {})
        for floor in project.get("floors", []):
            if floor.get("floor_id") == floor_id:
                floor["reinforcement_workspace"] = dict(workspace_dict)

    def _update_drawing_registry(
        self,
        model: dict[str, Any],
        drawing_model: ReinforcementDrawingModel,
    ) -> None:
        registry = dict(model.get("drawing_registry", {}))
        registry["phase"] = PHASE
        for entry in registry.get("drawings", []):
            if entry.get("drawing_id") != drawing_model.drawing_id:
                continue
            entry["geometry_status"] = "READY"
            entry["region_count"] = len(drawing_model.regions)
            entry["detail_context_count"] = len(drawing_model.detail_contexts)
            entry["detail_identity_count"] = len(drawing_model.detail_identities)
            entry["detail_fingerprint_count"] = len(drawing_model.detail_fingerprints)
            entry["beam_match_candidate_count"] = len(drawing_model.beam_match_candidates)
            entry["match_decision_count"] = len(drawing_model.match_decisions)
            entry["beam_match_count"] = len(drawing_model.beam_matches)
            entry["engineering_reinforcement_context_count"] = len(
                drawing_model.engineering_reinforcement_contexts
            )
            entry["detail_view_count"] = len(drawing_model.detail_views)
            entry["sketch_count"] = len(drawing_model.sketches)
            entry["text_count"] = len(drawing_model.text_objects)
            entry["leader_count"] = len(drawing_model.leaders)
            entry["block_count"] = len(drawing_model.blocks)
        model["drawing_registry"] = registry

    def _enrich_drawing_sets(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        registry: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["detail_context_registry"] = registry
                ds["detail_context_count"] = registry.get("detail_context_count", 0)

    def _enrich_drawing_sets_identities(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        identity_registry: dict[str, Any],
        fingerprint_registry: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["detail_identity_registry"] = identity_registry
                ds["detail_identity_count"] = identity_registry.get("detail_identity_count", 0)
                ds["detail_fingerprint_registry"] = fingerprint_registry
                ds["detail_fingerprint_count"] = fingerprint_registry.get("fingerprint_count", 0)

    def _enrich_drawing_sets_candidates(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        candidate_registry: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["candidate_registry"] = candidate_registry
                ds["candidate_count"] = candidate_registry.get("candidate_count", 0)
                ds["matching_progress"] = "CANDIDATES_GENERATED"

    def _enrich_drawing_sets_decisions(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        decision_registry: dict[str, Any],
    ) -> None:
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["match_decision_registry"] = decision_registry
                ds["decision_count"] = decision_registry.get("decision_count", 0)
                ds["decision_progress"] = "DECISIONS_READY"

    def _enrich_drawing_sets_quality(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
    ) -> None:
        from src.reinforcement.match_decision_quality import (
            ALGORITHM_VERSION,
            build_quality_summary,
        )

        summary = build_quality_summary(decisions)
        floor_ids = {dm.get("floor_id") for dm in drawing_models}
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") in floor_ids:
                ds["decision_algorithm_version"] = ALGORITHM_VERSION
                ds["decision_quality_summary"] = summary

    def _enrich_project_workspace_quality(
        self,
        model: dict[str, Any],
        decisions: List[dict[str, Any]],
    ) -> None:
        from src.reinforcement.match_decision_quality import (
            ALGORITHM_VERSION,
            build_quality_summary,
        )

        project = dict(model.get("project_workspace", {}))
        project["decision_algorithm_version"] = ALGORITHM_VERSION
        project["decision_quality_summary"] = build_quality_summary(decisions)
        model["project_workspace"] = project

    def _update_project_graph(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
    ) -> None:
        graph = model.get("project_engineering_graph", {})
        if not graph:
            return

        graph["phase"] = PHASE
        nodes = list(graph.get("nodes", []))
        edges = list(graph.get("edges", []))
        existing_node_ids = {node.get("id") for node in nodes}

        def add_edge(edge: dict[str, Any]) -> None:
            if edge not in edges:
                edges.append(edge)

        for dm in drawing_models:
            drawing_id = dm.get("drawing_id")
            if not drawing_id:
                continue

            if drawing_id not in existing_node_ids:
                nodes.append(
                    {
                        "id": drawing_id,
                        "type": "REINFORCEMENT_DRAWING",
                        "parent": dm.get("drawing_set_id"),
                        "drawing_type": DRAWING_TYPE_BEAM_REINFORCEMENT,
                    }
                )
                existing_node_ids.add(drawing_id)

            ds_id = dm.get("drawing_set_id")
            if ds_id and not any(
                e.get("from") == ds_id and e.get("to") == drawing_id for e in edges
            ):
                add_edge(
                    {
                        "from": ds_id,
                        "to": drawing_id,
                        "relationship": "HAS_REINFORCEMENT_DRAWING",
                    }
                )

            for collection_key, node_type, rel in (
                ("regions", "REGION", "HAS_REGION"),
                ("detail_contexts", "DETAIL_CONTEXT", "HAS_DETAIL_CONTEXT"),
                ("detail_identities", "DETAIL", "HAS_DETAIL"),
                ("detail_fingerprints", "FINGERPRINT", "HAS_FINGERPRINT"),
                ("beam_match_candidates", "MATCH_CANDIDATE", "HAS_CANDIDATE"),
                ("match_decisions", "MATCH_DECISION", "HAS_MATCH_DECISION"),
                ("beam_matches", "BEAM_MATCH", "HAS_BEAM_MATCH"),
                ("engineering_reinforcement_contexts", "ENGINEERING_REINFORCEMENT_CONTEXT", "HAS_ERC"),
                ("detail_views", "VIEW", "HAS_VIEW"),
                ("sketches", "SKETCH", "HAS_SKETCH"),
                ("text_objects", "TEXT", "HAS_TEXT"),
                ("leaders", "LEADER", "HAS_LEADER"),
                ("blocks", "BLOCK", "HAS_BLOCK"),
            ):
                for item in dm.get(collection_key, []):
                    if collection_key == "detail_contexts":
                        gid = item.get("detail_context_id")
                    elif collection_key == "detail_identities":
                        gid = item.get("detail_identity_id")
                    elif collection_key == "detail_fingerprints":
                        gid = item.get("fingerprint_id")
                    elif collection_key == "beam_match_candidates":
                        gid = item.get("candidate_id")
                    elif collection_key == "match_decisions":
                        gid = item.get("decision_id")
                    elif collection_key == "beam_matches":
                        gid = item.get("beam_match_id")
                    elif collection_key == "engineering_reinforcement_contexts":
                        gid = item.get("reinforcement_context_id")
                    else:
                        gid = item.get("geometry_id")
                    if not gid or gid in existing_node_ids:
                        continue
                    parent = drawing_id
                    if collection_key == "detail_contexts":
                        parent = item.get("region_id", drawing_id)
                    elif collection_key == "detail_identities":
                        parent = item.get("detail_context_id", drawing_id)
                    elif collection_key == "detail_fingerprints":
                        parent = item.get("detail_identity_id", drawing_id)
                    elif collection_key == "beam_match_candidates":
                        parent = item.get("detail_identity_id", drawing_id)
                    elif collection_key == "match_decisions":
                        parent = item.get("detail_identity_id", drawing_id)
                    elif collection_key == "beam_matches":
                        parent = item.get("detail_identity_id", drawing_id)
                    elif collection_key == "engineering_reinforcement_contexts":
                        parent = item.get("beam_context_id", drawing_id)
                    nodes.append(
                        {
                            "id": gid,
                            "type": node_type,
                            "parent": parent,
                        }
                    )
                    existing_node_ids.add(gid)
                    if collection_key == "detail_contexts":
                        add_edge(
                            {
                                "from": item.get("region_id", ""),
                                "to": gid,
                                "relationship": "HAS_DETAIL_CONTEXT",
                            }
                        )
                        add_edge(
                            {
                                "from": gid,
                                "to": drawing_id,
                                "relationship": "BELONGS_TO",
                            }
                        )
                    elif collection_key == "detail_identities":
                        add_edge(
                            {
                                "from": item.get("detail_context_id", ""),
                                "to": gid,
                                "relationship": "HAS_DETAIL",
                            }
                        )
                        add_edge(
                            {
                                "from": gid,
                                "to": drawing_id,
                                "relationship": "BELONGS_TO",
                            }
                        )
                    elif collection_key == "detail_fingerprints":
                        add_edge(
                            {
                                "from": item.get("detail_identity_id", ""),
                                "to": gid,
                                "relationship": "HAS_FINGERPRINT",
                            }
                        )
                    elif collection_key == "beam_match_candidates":
                        add_edge(
                            {
                                "from": item.get("detail_identity_id", ""),
                                "to": gid,
                                "relationship": "HAS_CANDIDATE",
                            }
                        )
                        add_edge(
                            {
                                "from": gid,
                                "to": item.get("beam_context_id", ""),
                                "relationship": "TARGETS",
                            }
                        )
                    elif collection_key == "match_decisions":
                        add_edge(
                            {
                                "from": item.get("detail_identity_id", ""),
                                "to": gid,
                                "relationship": "HAS_MATCH_DECISION",
                            }
                        )
                        rec = item.get("recommended_candidate_id")
                        if rec:
                            add_edge(
                                {
                                    "from": gid,
                                    "to": rec,
                                    "relationship": "RECOMMENDS",
                                }
                            )
                        add_edge(
                            {
                                "from": gid,
                                "to": item.get("drawing_set_id", ""),
                                "relationship": "BELONGS_TO",
                            }
                        )
                    elif collection_key == "beam_matches":
                        add_edge(
                            {
                                "from": item.get("detail_identity_id", ""),
                                "to": gid,
                                "relationship": "MATCHED_TO",
                            }
                        )
                        add_edge(
                            {
                                "from": gid,
                                "to": item.get("match_decision_id", ""),
                                "relationship": "REFERENCES",
                            }
                        )
                        add_edge(
                            {
                                "from": gid,
                                "to": item.get("beam_context_id", ""),
                                "relationship": "TARGETS",
                            }
                        )
                        add_edge(
                            {
                                "from": item.get("beam_context_id", ""),
                                "to": gid,
                                "relationship": "HAS_REINFORCEMENT_MATCH",
                            }
                        )
                    else:
                        add_edge(
                            {
                                "from": drawing_id,
                                "to": gid,
                                "relationship": rel,
                            }
                        )

            for ctx in dm.get("detail_contexts", []):
                ctx_id = ctx.get("detail_context_id", "")
                ident_id = ctx.get("detail_identity_id", "")
                if ident_id:
                    add_edge(
                        {
                            "from": ctx_id,
                            "to": ident_id,
                            "relationship": "HAS_DETAIL",
                        }
                    )
                for view_id in ctx.get("view_ids", []):
                    add_edge(
                        {
                            "from": ctx_id,
                            "to": view_id,
                            "relationship": "HAS_VIEW",
                        }
                    )

            for rel in dm.get("match_relationships", []):
                add_edge(
                    {
                        "from": rel.get("source_id"),
                        "to": rel.get("target_id"),
                        "relationship": rel.get("relationship"),
                        "type": rel.get("type", "ENGINEERING"),
                    }
                )

            for rel in dm.get("ownership_relationships", []):
                rel_name = str(rel.get("relationship", ""))
                graph_rel = rel_name
                if rel_name == "BEAM_MATCH_CREATES_ERC":
                    graph_rel = "CREATES"
                elif rel_name == "BEAM_CONTEXT_HAS_REINFORCEMENT_CONTEXT":
                    graph_rel = "HAS_REINFORCEMENT_CONTEXT"
                elif rel_name.startswith("ERC_OWNS_"):
                    graph_rel = rel_name.replace("ERC_", "")
                add_edge(
                    {
                        "from": rel.get("source_id"),
                        "to": rel.get("target_id"),
                        "relationship": graph_rel,
                        "type": rel.get("type", "ENGINEERING"),
                    }
                )

            for rel in dm.get("relationships", []):
                add_edge(
                    {
                        "from": rel.get("source_id"),
                        "to": rel.get("target_id"),
                        "relationship": rel.get("relationship"),
                        "type": rel.get("type", "GEOMETRIC"),
                    }
                )

        from src.reinforcement.match_decision_quality import (
            SHARED_ALGORITHM_ID,
            format_decision_quality_id,
            shared_algorithm_node,
        )

        if SHARED_ALGORITHM_ID not in existing_node_ids:
            algo = shared_algorithm_node()
            nodes.append(
                {
                    "id": algo["id"],
                    "type": "MATCH_ALGORITHM",
                    "name": algo["name"],
                    "version": algo["version"],
                    "family": algo["family"],
                }
            )
            existing_node_ids.add(SHARED_ALGORITHM_ID)

        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                decision_id = str(decision.get("decision_id", ""))
                quality_id = format_decision_quality_id(decision_id)
                if quality_id not in existing_node_ids:
                    nodes.append(
                        {
                            "id": quality_id,
                            "type": "DECISION_QUALITY",
                            "parent": decision_id,
                        }
                    )
                    existing_node_ids.add(quality_id)

            for rel in dm.get("quality_relationships", []):
                rel_name = str(rel.get("relationship", ""))
                if rel_name == "MATCH_DECISION_HAS_QUALITY":
                    add_edge(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "HAS_QUALITY",
                        }
                    )
                elif rel_name == "MATCH_DECISION_GENERATED_BY":
                    add_edge(
                        {
                            "from": rel.get("source_id"),
                            "to": rel.get("target_id"),
                            "relationship": "GENERATED_BY",
                        }
                    )

        for dm in drawing_models:
            for erc in dm.get("engineering_reinforcement_contexts", []):
                erc_id = erc.get("reinforcement_context_id")
                beam_mark = str(erc.get("beam_mark", ""))
                if not erc_id or not beam_mark:
                    continue

                registry_id = erc.get("engineering_assets", {}).get("registry_id")
                if registry_id and registry_id not in existing_node_ids:
                    nodes.append(
                        {
                            "id": registry_id,
                            "type": "ENGINEERING_ASSET_REGISTRY",
                            "parent": erc_id,
                            "beam_mark": beam_mark,
                        }
                    )
                    existing_node_ids.add(registry_id)
                if registry_id:
                    add_edge(
                        {
                            "from": erc_id,
                            "to": registry_id,
                            "relationship": "HAS_ASSET_REGISTRY",
                        }
                    )

                lifecycle_id = format_erc_lifecycle_id(beam_mark)
                if lifecycle_id not in existing_node_ids:
                    nodes.append(
                        {
                            "id": lifecycle_id,
                            "type": "ERC_LIFECYCLE",
                            "parent": erc_id,
                            "current_state": erc.get("lifecycle", {}).get("current_state"),
                        }
                    )
                    existing_node_ids.add(lifecycle_id)
                add_edge(
                    {
                        "from": erc_id,
                        "to": lifecycle_id,
                        "relationship": "HAS_LIFECYCLE",
                    }
                )

                results_id = format_engineering_results_id(beam_mark)
                if results_id not in existing_node_ids:
                    nodes.append(
                        {
                            "id": results_id,
                            "type": "ENGINEERING_RESULTS_PLACEHOLDER",
                            "parent": erc_id,
                        }
                    )
                    existing_node_ids.add(results_id)
                add_edge(
                    {
                        "from": erc_id,
                        "to": results_id,
                        "relationship": "HAS_ENGINEERING_RESULTS",
                    }
                )

                sem_registry_id = erc.get("semantic_role_registry", {}).get("registry_id")
                if sem_registry_id and sem_registry_id not in existing_node_ids:
                    nodes.append(
                        {
                            "id": sem_registry_id,
                            "type": "SEMANTIC_ROLE_REGISTRY",
                            "parent": erc_id,
                            "beam_mark": beam_mark,
                        }
                    )
                    existing_node_ids.add(sem_registry_id)
                if sem_registry_id:
                    add_edge(
                        {
                            "from": erc_id,
                            "to": sem_registry_id,
                            "relationship": "HAS_SEMANTIC_ROLE_REGISTRY",
                        }
                    )
                    roles_by_id = {
                        r.get("semantic_role_id"): r
                        for r in model.get("engineering_semantic_role_registry", {}).get("roles", [])
                    }
                    for role_ref in erc.get("semantic_roles", []):
                        role_id = role_ref if isinstance(role_ref, str) else role_ref.get("semantic_role_id")
                        if not role_id:
                            continue
                        role_data = roles_by_id.get(role_id, {})
                        if role_id not in existing_node_ids:
                            nodes.append(
                                {
                                    "id": role_id,
                                    "type": "SEMANTIC_ROLE",
                                    "parent": erc_id,
                                    "role_type": role_data.get("role_type"),
                                    "engineering_priority": role_data.get("engineering_priority"),
                                }
                            )
                            existing_node_ids.add(role_id)
                        add_edge(
                            {
                                "from": erc_id,
                                "to": role_id,
                                "relationship": "HAS_SEMANTIC_ROLE",
                            }
                        )
                        for geom_id in role_data.get("geometry_asset_ids", []):
                            add_edge(
                                {
                                    "from": role_id,
                                    "to": geom_id,
                                    "relationship": "REFERENCES",
                                    "asset_kind": "geometry",
                                }
                            )
                        for text_id in role_data.get("text_asset_ids", []):
                            add_edge(
                                {
                                    "from": role_id,
                                    "to": text_id,
                                    "relationship": "REFERENCES",
                                    "asset_kind": "text",
                                }
                            )

                sem_rel_registry_id = erc.get("semantic_relationship_registry", {}).get(
                    "registry_id"
                )
                if sem_rel_registry_id and sem_rel_registry_id not in existing_node_ids:
                    nodes.append(
                        {
                            "id": sem_rel_registry_id,
                            "type": "SEMANTIC_RELATIONSHIP_REGISTRY",
                            "parent": erc_id,
                            "beam_mark": beam_mark,
                        }
                    )
                    existing_node_ids.add(sem_rel_registry_id)
                if sem_rel_registry_id:
                    add_edge(
                        {
                            "from": erc_id,
                            "to": sem_rel_registry_id,
                            "relationship": "HAS_SEMANTIC_RELATIONSHIP_REGISTRY",
                        }
                    )
                    rels_by_id = {
                        r.get("relationship_id"): r
                        for r in model.get("engineering_semantic_relationship_registry", {}).get(
                            "relationships", []
                        )
                    }
                    for rel_ref in erc.get("semantic_relationships", []):
                        rel_id = (
                            rel_ref
                            if isinstance(rel_ref, str)
                            else rel_ref.get("relationship_id")
                        )
                        if not rel_id:
                            continue
                        rel_data = rels_by_id.get(rel_id, {})
                        if rel_id not in existing_node_ids:
                            nodes.append(
                                {
                                    "id": rel_id,
                                    "type": "SEMANTIC_RELATIONSHIP",
                                    "parent": erc_id,
                                    "relationship_type": rel_data.get("relationship_type"),
                                }
                            )
                            existing_node_ids.add(rel_id)
                        add_edge(
                            {
                                "from": rel_data.get("source_role_id"),
                                "to": rel_id,
                                "relationship": "HAS_SEMANTIC_RELATIONSHIP",
                            }
                        )
                        add_edge(
                            {
                                "from": rel_id,
                                "to": rel_data.get("target_role_id"),
                                "relationship": rel_data.get("relationship_type", "REFERENCES"),
                            }
                        )

                obj_registry_id = erc.get("engineering_objects", {}).get("registry_id")
                if obj_registry_id and obj_registry_id not in existing_node_ids:
                    nodes.append(
                        {
                            "id": obj_registry_id,
                            "type": "ENGINEERING_OBJECT_REGISTRY",
                            "parent": erc_id,
                            "beam_mark": beam_mark,
                        }
                    )
                    existing_node_ids.add(obj_registry_id)
                if obj_registry_id:
                    add_edge(
                        {
                            "from": erc_id,
                            "to": obj_registry_id,
                            "relationship": "HAS_ENGINEERING_OBJECT_REGISTRY",
                        }
                    )
                    graph_node_id = f"ENG_OBJ_GRAPH::{beam_mark}"
                    if graph_node_id not in existing_node_ids:
                        nodes.append(
                            {
                                "id": graph_node_id,
                                "type": "ENGINEERING_OBJECT_GRAPH",
                                "parent": obj_registry_id,
                            }
                        )
                        existing_node_ids.add(graph_node_id)
                    add_edge(
                        {
                            "from": obj_registry_id,
                            "to": graph_node_id,
                            "relationship": "HAS_ENGINEERING_OBJECT_GRAPH",
                        }
                    )
                    add_edge(
                        {
                            "from": graph_node_id,
                            "to": results_id,
                            "relationship": "FEEDS",
                        }
                    )

                objects_by_id = {
                    o.get("engineering_object_id"): o
                    for o in model.get("engineering_object_registry", {}).get("objects", [])
                }
                for obj_ref in erc.get("engineering_objects", {}).get("objects", []):
                    obj_id = obj_ref if isinstance(obj_ref, str) else obj_ref.get("engineering_object_id")
                    if not obj_id:
                        continue
                    obj_data = objects_by_id.get(obj_id, {})
                    if obj_id not in existing_node_ids:
                        nodes.append(
                            {
                                "id": obj_id,
                                "type": "ENGINEERING_OBJECT",
                                "parent": erc_id,
                                "object_type": obj_data.get("object_type"),
                            }
                        )
                        existing_node_ids.add(obj_id)
                    add_edge(
                        {
                            "from": erc_id,
                            "to": obj_id,
                            "relationship": "HAS_ENGINEERING_OBJECT",
                        }
                    )
                    for geom_id in obj_data.get("asset_references", {}).get("geometry", []):
                        add_edge(
                            {
                                "from": obj_id,
                                "to": geom_id,
                                "relationship": "REFERENCES",
                            }
                        )
                    for text_id in obj_data.get("asset_references", {}).get("text", []):
                        add_edge(
                            {
                                "from": obj_id,
                                "to": text_id,
                                "relationship": "REFERENCES",
                            }
                        )
                    for leader_id in obj_data.get("asset_references", {}).get("leaders", []):
                        add_edge(
                            {
                                "from": obj_id,
                                "to": leader_id,
                                "relationship": "REFERENCES",
                            }
                        )

        graph["nodes"] = nodes
        graph["node_count"] = len(nodes)
        graph["edges"] = edges
        graph["edge_count"] = len(edges)
        model["project_engineering_graph"] = graph

    def _drawing_id_for_floor(self, model: dict[str, Any], floor_id: str) -> str:
        for item in model.get("drawing_identities", []):
            if item.get("floor_id") == floor_id and item.get("drawing_type") == DRAWING_TYPE_BEAM_REINFORCEMENT:
                return str(item.get("drawing_id", ""))
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") == floor_id:
                return str(ds.get("drawings", {}).get("reinforcement", ""))
        return ""

    def _drawing_set_id_for_floor(self, model: dict[str, Any], floor_id: str) -> str:
        for ds in model.get("drawing_sets", []):
            if ds.get("floor_id") == floor_id:
                return str(ds.get("drawing_set_id", ""))
        return ""
