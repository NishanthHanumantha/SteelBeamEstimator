"""Validate Phase G.4.2 engineering object framework scaffolding."""

from __future__ import annotations

from typing import Any, List, Set

from src.reinforcement.engineering_object import (
    ENGINEERING_STATUS_PLACEHOLDER,
    VALID_OBJECT_TYPES,
    empty_asset_references,
    engineering_object_applied,
    engineering_object_instantiation_applied,
)
from src.reinforcement.engineering_object_lifecycle import (
    STATE_READY_FOR_PARSING,
    VALID_OBJECT_LIFECYCLE_STATES,
)
from src.reinforcement.engineering_relationships import VALID_RELATIONSHIPS


class EngineeringObjectValidator:
    """Verify engineering object framework integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if engineering_object_instantiation_applied(model):
            return {
                "phase": "Phase G.4.2",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "superseded by G.5.1 instantiation"},
            }
        if not engineering_object_applied(model):
            return {
                "phase": "Phase G.4.2",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "engineering_object_framework not applied"},
            }

        contexts = model.get("engineering_reinforcement_contexts", [])
        registry = model.get("engineering_object_registry", {})
        objects = registry.get("objects", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_unique_ids(objects))
        checks.append(self._check_registry_integrity(registry, contexts))
        checks.append(self._check_valid_owner_erc(objects, contexts))
        checks.append(self._check_registry_references_exist(registry, contexts))
        checks.append(self._check_no_duplicated_ids(objects))
        checks.append(self._check_lifecycle_valid(objects, model))
        checks.append(self._check_asset_references_empty(objects))
        checks.append(self._check_object_type_valid(objects))
        checks.append(self._check_placeholder_state(objects))
        checks.append(self._check_graph_consistency(model, contexts))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.4.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "object_count": len(objects),
            },
        }

    def _check_unique_ids(self, objects: list) -> dict[str, Any]:
        ids = [o.get("engineering_object_id") for o in objects]
        unique = len(ids) == len(set(ids))
        return {
            "name": "Unique IDs",
            "status": "PASS" if unique else "FAIL",
            "count": len(ids),
        }

    def _check_registry_integrity(
        self,
        registry: dict[str, Any],
        contexts: list,
    ) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == "ENGINEERING_OBJECT"
            and registry.get("object_count", -1) == len(registry.get("objects", []))
            and len(registry.get("erc_registries", [])) == len(contexts)
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if contexts and ok else "FAIL",
            "object_count": registry.get("object_count", 0),
            "erc_registry_count": len(registry.get("erc_registries", [])),
        }

    def _check_valid_owner_erc(self, objects: list, contexts: list) -> dict[str, Any]:
        erc_ids = {c.get("reinforcement_context_id") for c in contexts}
        invalid = [
            o.get("engineering_object_id")
            for o in objects
            if o.get("owner_context_id") not in erc_ids
        ]
        return {
            "name": "Valid Owner ERC",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_registry_references_exist(
        self,
        registry: dict[str, Any],
        contexts: list,
    ) -> dict[str, Any]:
        erc_ids = {c.get("reinforcement_context_id") for c in contexts}
        missing = [
            e.get("reinforcement_context_id")
            for e in registry.get("erc_registries", [])
            if e.get("reinforcement_context_id") not in erc_ids
        ]
        ctx_missing = [
            c.get("reinforcement_context_id")
            for c in contexts
            if "engineering_objects" not in c
        ]
        return {
            "name": "Registry References Exist",
            "status": "PASS" if not missing and not ctx_missing else "FAIL",
            "missing_erc": missing,
            "missing_section": ctx_missing,
        }

    def _check_no_duplicated_ids(self, objects: list) -> dict[str, Any]:
        seen: Set[str] = set()
        duplicates: Set[str] = set()
        for obj in objects:
            oid = str(obj.get("engineering_object_id", ""))
            if oid in seen:
                duplicates.add(oid)
            seen.add(oid)
        return {
            "name": "No Duplicated IDs",
            "status": "PASS" if not duplicates else "FAIL",
            "duplicates": list(duplicates),
        }

    def _check_lifecycle_valid(self, objects: list, model: dict[str, Any]) -> dict[str, Any]:
        invalid = [
            o.get("engineering_object_id")
            for o in objects
            if o.get("lifecycle") not in VALID_OBJECT_LIFECYCLE_STATES
        ]
        lifecycle_registry = model.get("engineering_object_lifecycle_registry", {})
        framework_ok = (
            lifecycle_registry.get("current_state") == STATE_READY_FOR_PARSING
        )
        return {
            "name": "Lifecycle Valid",
            "status": "PASS" if not invalid and framework_ok else "FAIL",
            "invalid": invalid,
        }

    def _check_asset_references_empty(self, objects: list) -> dict[str, Any]:
        invalid = []
        for obj in objects:
            refs = obj.get("asset_references", {})
            empty = empty_asset_references()
            for key in empty:
                if refs.get(key):
                    invalid.append(obj.get("engineering_object_id"))
                    break
        return {
            "name": "Asset References Empty",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_object_type_valid(self, objects: list) -> dict[str, Any]:
        invalid = [
            o.get("engineering_object_id")
            for o in objects
            if o.get("object_type") not in VALID_OBJECT_TYPES
        ]
        return {
            "name": "Object Type Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_placeholder_state(self, objects: list) -> dict[str, Any]:
        invalid = [
            o.get("engineering_object_id")
            for o in objects
            if o.get("engineering_status") != ENGINEERING_STATUS_PLACEHOLDER
        ]
        return {
            "name": "Placeholder State",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_graph_consistency(
        self,
        model: dict[str, Any],
        contexts: list,
    ) -> dict[str, Any]:
        graph = model.get("engineering_object_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_types = {n.get("type") for n in nodes}
        has_registry = "ENGINEERING_OBJECT_REGISTRY" in node_types
        has_graph = "ENGINEERING_OBJECT_GRAPH" in node_types
        has_erc = any(n.get("type") == "ENGINEERING_REINFORCEMENT_CONTEXT" for n in nodes)
        has_registry_edge = any(
            e.get("relationship") == "HAS_ENGINEERING_OBJECT_REGISTRY" for e in edges
        )
        relationships = model.get("engineering_object_relationships", {})
        rel_valid = all(
            r.get("relationship") in VALID_RELATIONSHIPS
            for r in relationships.get("relationships", [])
        )
        erc_sections = all(
            len(c.get("engineering_objects", {}).get("objects", [])) == 0 for c in contexts
        )
        ok = (
            has_registry
            and has_graph
            and has_erc
            and has_registry_edge
            and rel_valid
            and erc_sections
            and len(nodes) > 0
        )
        return {
            "name": "Graph Consistency",
            "status": "PASS" if contexts and ok else "FAIL",
            "has_registry": has_registry,
            "has_graph": has_graph,
            "has_erc": has_erc,
            "empty_objects": erc_sections,
        }
