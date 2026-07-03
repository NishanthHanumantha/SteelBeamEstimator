"""Validate property graph — Phase G.5.2."""

from __future__ import annotations

from typing import Any, List, Set

from src.engineering_objects.engineering_object import erc_engineering_object_ids
from src.property_graph.property_candidate import property_graph_applied
from src.property_graph.property_graph_types import (
    VALID_CANDIDATE_STATUSES,
    VALID_CANDIDATE_TYPES,
    VALID_DISCOVERY_METHODS,
)


class PropertyGraphValidator:
    """Verify property graph candidate integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not property_graph_applied(model):
            return {
                "phase": "Phase G.5.2",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "property graph not applied"},
            }

        contexts = model.get("engineering_reinforcement_contexts", [])
        registry = model.get("property_registry", {})
        candidates = registry.get("candidates") or model.get("property_candidates", [])
        objects = model.get("engineering_objects", [])
        graph = model.get("property_graph", {})
        known_entities = self._entity_index(model, contexts)

        checks: List[dict[str, Any]] = []
        checks.append(self._check_objects_have_registry(contexts, objects))
        checks.append(self._check_unique_candidate_ids(candidates))
        checks.append(self._check_valid_engineering_object_refs(candidates, objects))
        checks.append(self._check_source_entities_exist(candidates, known_entities))
        checks.append(self._check_registry_counts(registry, contexts, candidates))
        checks.append(self._check_graph_connectivity(graph, candidates, objects))
        checks.append(self._check_no_orphan_candidates(candidates, contexts))
        checks.append(self._check_candidate_type_valid(candidates))
        checks.append(self._check_discovery_method_valid(candidates))
        checks.append(self._check_confidence_assigned(candidates))
        checks.append(self._check_relationship_distance_valid(candidates))
        checks.append(self._check_outputs_generated(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.5.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "candidate_count": len(candidates),
            },
        }

    @staticmethod
    def _entity_index(
        model: dict[str, Any],
        contexts: list,
    ) -> Set[str]:
        ids: Set[str] = set()
        for ctx in contexts:
            for key in ("owned_geometry", "owned_text", "owned_leaders", "owned_blocks"):
                ids.update(ctx.get(key, []))
        for role in model.get("engineering_semantic_role_registry", {}).get("roles", []):
            for key in (
                "geometry_asset_ids",
                "text_asset_ids",
                "leader_asset_ids",
                "block_asset_ids",
                "source_geometry_ids",
            ):
                ids.update(role.get(key, []))
        for dm in model.get("reinforcement_drawing_models", []):
            for key in ("sketches", "text_objects", "leaders", "blocks"):
                for item in dm.get(key, []):
                    gid = item.get("geometry_id")
                    if gid:
                        ids.add(gid)
        return ids

    def _check_objects_have_registry(
        self,
        contexts: list,
        objects: list,
    ) -> dict[str, Any]:
        missing = []
        for ctx in contexts:
            if not erc_engineering_object_ids(ctx):
                continue
            section = ctx.get("property_candidate_registry")
            if not isinstance(section, dict) or not section.get("registry_id"):
                missing.append(ctx.get("reinforcement_context_id"))
        return {
            "name": "Every Engineering Object Has Registry",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing": missing[:10],
        }

    @staticmethod
    def _check_unique_candidate_ids(candidates: list) -> dict[str, Any]:
        ids = [c.get("candidate_id") for c in candidates]
        return {
            "name": "Candidate IDs Unique",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "count": len(ids),
        }

    @staticmethod
    def _check_valid_engineering_object_refs(
        candidates: list,
        objects: list,
    ) -> dict[str, Any]:
        object_ids = {
            o.get("object_id") or o.get("engineering_object_id") for o in objects
        }
        invalid = [
            c.get("candidate_id")
            for c in candidates
            if c.get("engineering_object_id") not in object_ids
        ]
        return {
            "name": "Candidates Reference Valid Engineering Objects",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_source_entities_exist(
        candidates: list,
        known_entities: Set[str],
    ) -> dict[str, Any]:
        invalid = [
            c.get("candidate_id")
            for c in candidates
            if c.get("source_entity_id") and c.get("source_entity_id") not in known_entities
        ]
        return {
            "name": "Every Source Entity Exists",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_registry_counts(
        registry: dict[str, Any],
        contexts: list,
        candidates: list,
    ) -> dict[str, Any]:
        mismatch = []
        erc_counts = {
            e.get("reinforcement_context_id"): e.get("candidate_count", 0)
            for e in registry.get("erc_registries", [])
        }
        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id")
            expected = len(ctx.get("property_candidates", []))
            if erc_counts.get(erc_id) != expected:
                mismatch.append(erc_id)
        ok = (
            registry.get("candidate_count") == len(candidates)
            and len(registry.get("erc_registries", [])) == len(contexts)
            and not mismatch
        )
        return {
            "name": "Registry Counts Correct",
            "status": "PASS" if contexts and ok else "FAIL",
            "mismatch": mismatch,
        }

    @staticmethod
    def _check_graph_connectivity(
        graph: dict[str, Any],
        candidates: list,
        objects: list,
    ) -> dict[str, Any]:
        node_ids = {n.get("id") for n in graph.get("nodes", [])}
        missing_candidates = [
            c.get("candidate_id")
            for c in candidates
            if c.get("candidate_id") not in node_ids
        ]
        missing_objects = [
            o.get("object_id") or o.get("engineering_object_id")
            for o in objects
            if (o.get("object_id") or o.get("engineering_object_id")) not in node_ids
        ]
        has_edges = len(graph.get("edges", [])) > 0
        ok = not missing_candidates and not missing_objects and has_edges
        return {
            "name": "Graph Connectivity Valid",
            "status": "PASS" if candidates and ok else "FAIL",
            "missing_candidates": missing_candidates[:10],
            "missing_objects": missing_objects[:10],
        }

    @staticmethod
    def _check_no_orphan_candidates(
        candidates: list,
        contexts: list,
    ) -> dict[str, Any]:
        registered: Set[str] = set()
        for ctx in contexts:
            registered.update(ctx.get("property_candidates", []))
        orphans = [
            c.get("candidate_id")
            for c in candidates
            if c.get("candidate_id") not in registered
        ]
        return {
            "name": "No Orphan Candidates",
            "status": "PASS" if not orphans else "FAIL",
            "orphans": orphans[:10],
        }

    @staticmethod
    def _check_candidate_type_valid(candidates: list) -> dict[str, Any]:
        invalid = [
            c.get("candidate_id")
            for c in candidates
            if c.get("candidate_type") not in VALID_CANDIDATE_TYPES
        ]
        return {
            "name": "Candidate Type Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_discovery_method_valid(candidates: list) -> dict[str, Any]:
        invalid = [
            c.get("candidate_id")
            for c in candidates
            if c.get("discovery_method") not in VALID_DISCOVERY_METHODS
        ]
        return {
            "name": "Discovery Method Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_confidence_assigned(candidates: list) -> dict[str, Any]:
        invalid = [
            c.get("candidate_id")
            for c in candidates
            if c.get("confidence") is None or float(c.get("confidence", -1)) < 0
        ]
        return {
            "name": "Confidence Assigned",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_relationship_distance_valid(candidates: list) -> dict[str, Any]:
        invalid = [
            c.get("candidate_id")
            for c in candidates
            if c.get("relationship_distance") is None
            or int(c.get("relationship_distance", -1)) < 0
        ]
        return {
            "name": "Relationship Distance Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_outputs_generated(model: dict[str, Any]) -> dict[str, Any]:
        ok = bool(
            model.get("property_candidates")
            and model.get("property_registry")
            and model.get("property_graph")
            and model.get("property_summary")
        )
        return {
            "name": "Output JSON Generated",
            "status": "PASS" if ok else "FAIL",
        }
