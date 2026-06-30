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
from src.reinforcement.match_decision_validator import MatchDecisionValidator
from src.reinforcement.reinforcement_drawing_validator import ReinforcementDrawingValidator


PHASE = "Phase G.2.7"
MODEL_VERSION = "2.7"


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
            "regions": list(self.regions),
            "detail_contexts": list(self.detail_contexts),
            "detail_identities": list(self.detail_identities),
            "detail_fingerprints": list(self.detail_fingerprints),
            "beam_match_candidates": list(self.beam_match_candidates),
            "match_decisions": list(self.match_decisions),
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
            all_identities.extend(drawing_model.detail_identities)
            all_fingerprints.extend(drawing_model.detail_fingerprints)
            all_candidates.extend(drawing_model.beam_match_candidates)
            all_decisions.extend(drawing_model.match_decisions)

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
            "Reinforcement drawing models — count={}, regions={}, contexts={}, identities={}, candidates={}, decisions={}",
            len(drawing_models),
            sum(dm.get("region_count", 0) for dm in drawing_models),
            sum(dm.get("detail_context_count", 0) for dm in drawing_models),
            sum(dm.get("detail_identity_count", 0) for dm in drawing_models),
            sum(dm.get("beam_match_candidate_count", 0) for dm in drawing_models),
            sum(dm.get("match_decision_count", 0) for dm in drawing_models),
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
