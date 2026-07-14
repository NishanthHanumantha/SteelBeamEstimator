"""Validate Phase G.5.0 Engineering Semantic Role layer."""

from __future__ import annotations

from typing import Any, List, Set

from src.reinforcement.engineering_semantic_role import (
    ENGINEERING_STATUS_ROLE_CLASSIFIED,
    semantic_roles_applied,
)
from src.reinforcement.engineering_semantic_role_lifecycle import (
    EngineeringSemanticRoleLifecycle,
    VALID_SEMANTIC_ROLE_LIFECYCLE,
)
from src.reinforcement.engineering_semantic_role_types import (
    ROLE_UNKNOWN,
    VALID_SEMANTIC_ROLE_TYPES,
)


class EngineeringSemanticRoleValidator:
    """Verify semantic role classification integrity."""

    def __init__(self, unknown_threshold: float = 0.15) -> None:
        self._unknown_threshold = unknown_threshold

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not semantic_roles_applied(model):
            return {
                "phase": "Phase G.5.0",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "semantic_roles not applied"},
            }

        contexts = model.get("engineering_reinforcement_contexts", [])
        registry = model.get("engineering_semantic_role_registry", {})
        roles = registry.get("roles", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_roles_belong_to_erc(roles, contexts))
        checks.append(self._check_no_orphan_roles(roles, contexts))
        checks.append(self._check_geometry_references(roles, model))
        checks.append(self._check_text_references(roles, model))
        checks.append(self._check_leader_references(roles, model))
        checks.append(self._check_registry_counts(registry, contexts))
        checks.append(self._check_lifecycle_classified(roles))
        checks.append(self._check_engineering_status(roles))
        checks.append(self._check_unknown_threshold(registry, roles))
        checks.append(self._check_no_duplicate_roles(roles))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.5.0",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "role_count": len(roles),
            },
        }

    def _check_roles_belong_to_erc(
        self,
        roles: list,
        contexts: list,
    ) -> dict[str, Any]:
        erc_ids = {c.get("reinforcement_context_id") for c in contexts}
        invalid = [r.get("semantic_role_id") for r in roles if r.get("owner_context_id") not in erc_ids]
        return {
            "name": "Every Semantic Role Belongs To One ERC",
            "status": "PASS" if roles and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_no_orphan_roles(self, roles: list, contexts: list) -> dict[str, Any]:
        role_ids = {r.get("semantic_role_id") for r in roles}
        orphans = []
        for ctx in contexts:
            for rid in ctx.get("semantic_roles", []):
                if rid not in role_ids:
                    orphans.append(rid)
        return {
            "name": "No Orphan Semantic Roles",
            "status": "PASS" if not orphans else "FAIL",
            "orphans": orphans[:10],
        }

    def _entity_index(self, model: dict[str, Any]) -> Set[str]:
        ids: Set[str] = set()
        for dm in model.get("reinforcement_drawing_models", []):
            for key in ("sketches", "text_objects", "leaders", "blocks"):
                for item in dm.get(key, []):
                    gid = item.get("geometry_id")
                    if gid:
                        ids.add(gid)
        return ids

    def _check_geometry_references(self, roles: list, model: dict[str, Any]) -> dict[str, Any]:
        known = self._entity_index(model)
        invalid = [
            gid
            for r in roles
            for gid in r.get("geometry_asset_ids", [])
            if gid not in known
        ]
        return {
            "name": "Geometry References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_text_references(self, roles: list, model: dict[str, Any]) -> dict[str, Any]:
        known = self._entity_index(model)
        invalid = [
            tid
            for r in roles
            for tid in r.get("text_asset_ids", [])
            if tid not in known
        ]
        return {
            "name": "Text References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_leader_references(self, roles: list, model: dict[str, Any]) -> dict[str, Any]:
        known = self._entity_index(model)
        invalid = [
            lid
            for r in roles
            for lid in r.get("leader_asset_ids", [])
            if lid not in known
        ]
        return {
            "name": "Leader References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_registry_counts(
        self,
        registry: dict[str, Any],
        contexts: list,
    ) -> dict[str, Any]:
        mismatch = []
        erc_counts = {
            e.get("reinforcement_context_id"): e.get("role_count", 0)
            for e in registry.get("erc_registries", [])
        }
        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id")
            expected = len(ctx.get("semantic_roles", []))
            if erc_counts.get(erc_id) != expected:
                mismatch.append(erc_id)
        ok = (
            registry.get("role_count") == len(registry.get("roles", []))
            and len(registry.get("erc_registries", [])) == len(contexts)
            and not mismatch
        )
        return {
            "name": "Registry Counts Correct",
            "status": "PASS" if contexts and ok else "FAIL",
            "mismatch": mismatch,
        }

    def _check_lifecycle_classified(self, roles: list) -> dict[str, Any]:
        expected = EngineeringSemanticRoleLifecycle.current_phase_state()
        invalid = [
            r.get("semantic_role_id")
            for r in roles
            if r.get("lifecycle") not in VALID_SEMANTIC_ROLE_LIFECYCLE
            or r.get("lifecycle") != expected
        ]
        return {
            "name": "Lifecycle CLASSIFIED",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_engineering_status(self, roles: list) -> dict[str, Any]:
        invalid = [
            r.get("semantic_role_id")
            for r in roles
            if r.get("engineering_status") != ENGINEERING_STATUS_ROLE_CLASSIFIED
            or r.get("role_type") not in VALID_SEMANTIC_ROLE_TYPES
            or r.get("future_engineering_object_id") is not None
        ]
        return {
            "name": "Engineering Status ROLE_CLASSIFIED",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_unknown_threshold(
        self,
        registry: dict[str, Any],
        roles: list,
    ) -> dict[str, Any]:
        total = len(roles)
        unknown = sum(1 for r in roles if r.get("role_type") == ROLE_UNKNOWN)
        ratio = unknown / total if total else 0.0
        return {
            "name": "Unknown Roles Below Threshold",
            "status": "PASS" if ratio <= self._unknown_threshold else "FAIL",
            "unknown_ratio": round(ratio, 4),
            "threshold": self._unknown_threshold,
        }

    def _check_no_duplicate_roles(self, roles: list) -> dict[str, Any]:
        seen_ids: set[str] = set()
        seen_signatures: set[tuple] = set()
        duplicates: set[str] = set()
        for role in roles:
            rid = str(role.get("semantic_role_id", ""))
            if rid in seen_ids:
                duplicates.add(rid)
            seen_ids.add(rid)
            asset_sig = (
                role.get("role_type"),
                tuple(sorted(role.get("geometry_asset_ids", []))),
                tuple(sorted(role.get("text_asset_ids", []))),
                tuple(sorted(role.get("leader_asset_ids", []))),
            )
            if asset_sig in seen_signatures:
                duplicates.add(rid)
            seen_signatures.add(asset_sig)
        return {
            "name": "Duplicate Semantic Roles Rejected",
            "status": "PASS" if not duplicates else "FAIL",
            "duplicates": list(duplicates)[:10],
        }
