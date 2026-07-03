"""Validate Phase G.5.0.1 Engineering Semantic Relationship layer."""

from __future__ import annotations

from typing import Any, List, Set

from src.reinforcement.engineering_semantic_relationship import (
    ENGINEERING_STATUS_RELATIONSHIP_CLASSIFIED,
    semantic_relationships_applied,
)
from src.reinforcement.engineering_semantic_relationship_types import (
    REL_UNKNOWN,
    STATE_CLASSIFIED,
    VALID_RELATIONSHIP_LIFECYCLE,
    VALID_SEMANTIC_RELATIONSHIP_TYPES,
)
from src.reinforcement.engineering_semantic_role_types import (
    VALID_ENGINEERING_PRIORITIES,
)


class EngineeringSemanticRelationshipValidator:
    """Verify semantic relationship integrity."""

    def __init__(self, unknown_threshold: float = 0.15) -> None:
        self._unknown_threshold = unknown_threshold

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not semantic_relationships_applied(model):
            return {
                "phase": "Phase G.5.0.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "semantic_relationships not applied"},
            }

        contexts = model.get("engineering_reinforcement_contexts", [])
        registry = model.get("engineering_semantic_relationship_registry", {})
        relationships = registry.get("relationships", [])
        role_registry = model.get("engineering_semantic_role_registry", {})
        roles = role_registry.get("roles", [])
        role_ids = {r.get("semantic_role_id") for r in roles}

        checks: List[dict[str, Any]] = []
        checks.append(self._check_belongs_to_erc(relationships, contexts))
        checks.append(self._check_source_role_exists(relationships, role_ids))
        checks.append(self._check_target_role_exists(relationships, role_ids))
        checks.append(self._check_no_orphan_relationships(relationships, contexts))
        checks.append(self._check_registry_counts(registry, contexts))
        checks.append(self._check_graph_connected(registry, contexts, role_ids))
        checks.append(self._check_no_duplicates(relationships))
        checks.append(self._check_no_cross_erc(relationships, roles))
        checks.append(self._check_priority_assigned(roles))
        checks.append(self._check_lifecycle(relationships))
        checks.append(self._check_engineering_status(relationships))
        checks.append(self._check_unknown_threshold(relationships))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.5.0.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "relationship_count": len(relationships),
            },
        }

    def _check_belongs_to_erc(
        self,
        relationships: list,
        contexts: list,
    ) -> dict[str, Any]:
        erc_ids = {c.get("reinforcement_context_id") for c in contexts}
        invalid = [
            r.get("relationship_id")
            for r in relationships
            if r.get("owner_context_id") not in erc_ids
        ]
        return {
            "name": "Every Relationship Belongs To One ERC",
            "status": "PASS" if relationships and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_source_role_exists(
        self,
        relationships: list,
        role_ids: Set[str],
    ) -> dict[str, Any]:
        invalid = [
            r.get("relationship_id")
            for r in relationships
            if r.get("source_role_id") not in role_ids
        ]
        return {
            "name": "Source Role Exists",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_target_role_exists(
        self,
        relationships: list,
        role_ids: Set[str],
    ) -> dict[str, Any]:
        invalid = [
            r.get("relationship_id")
            for r in relationships
            if r.get("target_role_id") not in role_ids
        ]
        return {
            "name": "Target Role Exists",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_no_orphan_relationships(
        self,
        relationships: list,
        contexts: list,
    ) -> dict[str, Any]:
        rel_ids = {r.get("relationship_id") for r in relationships}
        orphans = []
        for ctx in contexts:
            for rid in ctx.get("semantic_relationships", []):
                if rid not in rel_ids:
                    orphans.append(rid)
        return {
            "name": "No Orphan Relationships",
            "status": "PASS" if not orphans else "FAIL",
            "orphans": orphans[:10],
        }

    def _check_registry_counts(
        self,
        registry: dict[str, Any],
        contexts: list,
    ) -> dict[str, Any]:
        mismatch = []
        erc_counts = {
            e.get("reinforcement_context_id"): e.get("relationship_count", 0)
            for e in registry.get("erc_registries", [])
        }
        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id")
            expected = len(ctx.get("semantic_relationships", []))
            if erc_counts.get(erc_id) != expected:
                mismatch.append(erc_id)
        ok = (
            registry.get("relationship_count") == len(registry.get("relationships", []))
            and len(registry.get("erc_registries", [])) == len(contexts)
            and not mismatch
        )
        return {
            "name": "Relationship Registry Counts Correct",
            "status": "PASS" if contexts and ok else "FAIL",
            "mismatch": mismatch,
        }

    def _check_graph_connected(
        self,
        registry: dict[str, Any],
        contexts: list,
        role_ids: Set[str],
    ) -> dict[str, Any]:
        rels = registry.get("relationships", [])
        multi_role_ercs = [
            c.get("reinforcement_context_id")
            for c in contexts
            if len(c.get("semantic_roles", [])) > 1
        ]
        ercs_with_rels = {r.get("owner_context_id") for r in rels}
        missing = [e for e in multi_role_ercs if e not in ercs_with_rels]
        return {
            "name": "Relationship Graph Connected",
            "status": "PASS" if not missing else "FAIL",
            "disconnected_ercs": missing[:10],
        }

    def _check_no_duplicates(self, relationships: list) -> dict[str, Any]:
        seen_ids: set[str] = set()
        seen_sigs: set[tuple] = set()
        duplicates: set[str] = set()
        for rel in relationships:
            rid = str(rel.get("relationship_id", ""))
            if rid in seen_ids:
                duplicates.add(rid)
            seen_ids.add(rid)
            sig = (
                rel.get("owner_context_id"),
                rel.get("relationship_type"),
                rel.get("source_role_id"),
                rel.get("target_role_id"),
            )
            if sig in seen_sigs:
                duplicates.add(rid)
            seen_sigs.add(sig)
        return {
            "name": "No Duplicate Relationships",
            "status": "PASS" if not duplicates else "FAIL",
            "duplicates": list(duplicates)[:10],
        }

    def _check_no_cross_erc(
        self,
        relationships: list,
        roles: list,
    ) -> dict[str, Any]:
        role_erc = {r.get("semantic_role_id"): r.get("owner_context_id") for r in roles}
        cross = []
        for rel in relationships:
            erc = rel.get("owner_context_id")
            src_erc = role_erc.get(rel.get("source_role_id"))
            tgt_erc = role_erc.get(rel.get("target_role_id"))
            if src_erc != erc or tgt_erc != erc:
                cross.append(rel.get("relationship_id"))
        return {
            "name": "No Cross-ERC Relationships",
            "status": "PASS" if not cross else "FAIL",
            "cross_erc": cross[:10],
        }

    def _check_priority_assigned(self, roles: list) -> dict[str, Any]:
        invalid = [
            r.get("semantic_role_id")
            for r in roles
            if r.get("engineering_priority") not in VALID_ENGINEERING_PRIORITIES
        ]
        return {
            "name": "Priority Assigned To Every Role",
            "status": "PASS" if roles and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_lifecycle(self, relationships: list) -> dict[str, Any]:
        not_classified = [
            r.get("relationship_id")
            for r in relationships
            if r.get("lifecycle") not in VALID_RELATIONSHIP_LIFECYCLE
            or r.get("lifecycle") != STATE_CLASSIFIED
        ]
        return {
            "name": "Lifecycle DISCOVERED To CLASSIFIED",
            "status": "PASS" if relationships and not not_classified else "FAIL",
            "invalid": not_classified[:10],
        }

    def _check_engineering_status(self, relationships: list) -> dict[str, Any]:
        invalid = [
            r.get("relationship_id")
            for r in relationships
            if r.get("engineering_status") != ENGINEERING_STATUS_RELATIONSHIP_CLASSIFIED
            or r.get("relationship_type") not in VALID_SEMANTIC_RELATIONSHIP_TYPES
        ]
        return {
            "name": "Engineering Status RELATIONSHIP_CLASSIFIED",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_unknown_threshold(self, relationships: list) -> dict[str, Any]:
        total = len(relationships)
        unknown = sum(1 for r in relationships if r.get("relationship_type") == REL_UNKNOWN)
        ratio = unknown / total if total else 0.0
        return {
            "name": "Unknown Relationships Below Threshold",
            "status": "PASS" if ratio <= self._unknown_threshold else "FAIL",
            "unknown_ratio": round(ratio, 4),
            "threshold": self._unknown_threshold,
        }
