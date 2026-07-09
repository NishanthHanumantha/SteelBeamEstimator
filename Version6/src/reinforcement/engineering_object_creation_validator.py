"""Validate Phase G.5.1 engineering object instantiation."""

from __future__ import annotations

from typing import Any, List, Set

from src.engineering_objects.engineering_object_validator import EngineeringObjectG51Validator
from src.reinforcement.engineering_object import (
    ENGINEERING_STATUS_OBJECT_CREATED,
    VALID_OBJECT_TYPES,
    engineering_object_instantiation_applied,
)
from src.reinforcement.engineering_object_lifecycle import (
    STATE_CREATED,
    VALID_OBJECT_LIFECYCLE_STATES,
)
from src.reinforcement.engineering_object_types import G51_OBJECT_TYPES


class EngineeringObjectCreationValidator:
    """Verify engineering object instantiation integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not engineering_object_instantiation_applied(model):
            return {
                "phase": "Phase G.5.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "engineering_object_instantiation not applied"},
            }

        registry = model.get("engineering_object_registry", {})
        objects = registry.get("objects", [])
        if objects and objects[0].get("source_role_id"):
            existing = model.get("engineering_object_instantiation_validation")
            if existing and existing.get("checks"):
                return existing
            return EngineeringObjectG51Validator().validate(model)

        contexts = model.get("engineering_reinforcement_contexts", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_erc_has_registry(contexts, registry))
        checks.append(self._check_objects_belong_to_one_erc(objects))
        checks.append(self._check_unique_ids(objects))
        checks.append(self._check_valid_lifecycle(objects))
        checks.append(self._check_valid_object_type(objects))
        checks.append(self._check_geometry_references_exist(objects, model))
        checks.append(self._check_text_references_exist(objects, model))
        checks.append(self._check_registry_integrity(registry, contexts, objects))
        checks.append(self._check_no_duplicated_assets(objects))
        checks.append(self._check_graph_consistency(model, contexts, objects))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.5.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "object_count": len(objects),
            },
        }

    def _erc_object_count(self, ctx: dict[str, Any]) -> int:
        eng = ctx.get("engineering_objects")
        if isinstance(eng, list):
            return len(eng)
        if isinstance(eng, dict):
            return eng.get("object_count", len(eng.get("objects", [])))
        return 0

    def _check_every_erc_has_registry(
        self,
        contexts: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        erc_reg = {
            e.get("reinforcement_context_id"): e
            for e in registry.get("erc_registries", [])
        }
        missing = []
        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id")
            section = ctx.get("engineering_object_registry", ctx.get("engineering_objects", {}))
            registry_id = (
                section.get("registry_id")
                if isinstance(section, dict)
                else ctx.get("engineering_object_registry", {}).get("registry_id")
            )
            if not registry_id:
                missing.append(erc_id)
            elif erc_id not in erc_reg:
                missing.append(erc_id)
        return {
            "name": "Every ERC Has Registry",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing": missing,
        }

    def _check_objects_belong_to_one_erc(self, objects: list) -> dict[str, Any]:
        invalid = []
        for obj in objects:
            if not obj.get("owner_context_id"):
                invalid.append(obj.get("engineering_object_id") or obj.get("object_id"))
        return {
            "name": "Objects Belong To One ERC",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_unique_ids(self, objects: list) -> dict[str, Any]:
        ids = [o.get("engineering_object_id") or o.get("object_id") for o in objects]
        return {
            "name": "Unique IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "count": len(ids),
        }

    def _check_valid_lifecycle(self, objects: list) -> dict[str, Any]:
        invalid = [
            o.get("engineering_object_id") or o.get("object_id")
            for o in objects
            if o.get("lifecycle") not in VALID_OBJECT_LIFECYCLE_STATES
            and o.get("lifecycle") != "OBJECT_CREATED"
        ]
        return {
            "name": "Valid Lifecycle",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_valid_object_type(self, objects: list) -> dict[str, Any]:
        from src.engineering_objects.engineering_object_types import VALID_OBJECT_TYPES as G51_TYPES

        invalid = [
            o.get("engineering_object_id") or o.get("object_id")
            for o in objects
            if o.get("object_type") not in VALID_OBJECT_TYPES
            and o.get("object_type") not in G51_OBJECT_TYPES
            and o.get("object_type") not in G51_TYPES
        ]
        return {
            "name": "Valid Object Type",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
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

    def _check_geometry_references_exist(
        self,
        objects: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        if objects and objects[0].get("source_role_id"):
            return {"name": "Geometry References Exist", "status": "PASS", "note": "graph-based"}
        known = self._entity_index(model)
        invalid = []
        for obj in objects:
            for gid in obj.get("asset_references", {}).get("geometry", []):
                if gid not in known:
                    invalid.append(gid)
        return {
            "name": "Geometry References Exist",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_text_references_exist(
        self,
        objects: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        if objects and objects[0].get("source_role_id"):
            return {"name": "Text References Exist", "status": "PASS", "note": "graph-based"}
        known = self._entity_index(model)
        invalid = []
        for obj in objects:
            for tid in obj.get("asset_references", {}).get("text", []):
                if tid not in known:
                    invalid.append(tid)
        return {
            "name": "Text References Exist",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_registry_integrity(
        self,
        registry: dict[str, Any],
        contexts: list,
        objects: list,
    ) -> dict[str, Any]:
        erc_object_counts = {
            ctx.get("reinforcement_context_id"): self._erc_object_count(ctx)
            for ctx in contexts
        }
        registry_counts = {
            e.get("reinforcement_context_id"): e.get("object_count", 0)
            for e in registry.get("erc_registries", [])
        }
        mismatch = [
            erc_id
            for erc_id, count in erc_object_counts.items()
            if registry_counts.get(erc_id) != count
        ]
        ok = (
            registry.get("object_count") == len(objects)
            and len(registry.get("erc_registries", [])) == len(contexts)
            and not mismatch
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if contexts and ok else "FAIL",
            "mismatch": mismatch,
        }

    def _check_no_duplicated_assets(self, objects: list) -> dict[str, Any]:
        if objects and objects[0].get("source_role_id"):
            return {"name": "No Duplicated Assets", "status": "PASS", "note": "graph-based"}
        seen: Set[str] = set()
        duplicates: Set[str] = set()
        for obj in objects:
            refs = obj.get("asset_references", {})
            for key in ("geometry", "text", "leaders", "blocks"):
                for asset_id in refs.get(key, []):
                    if asset_id in seen:
                        duplicates.add(asset_id)
                    seen.add(asset_id)
        return {
            "name": "No Duplicated Assets",
            "status": "PASS" if not duplicates else "FAIL",
            "duplicates": list(duplicates)[:10],
        }

    def _check_graph_consistency(
        self,
        model: dict[str, Any],
        contexts: list,
        objects: list,
    ) -> dict[str, Any]:
        graph = model.get("engineering_object_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_ids = {n.get("id") for n in nodes}
        has_obj_nodes = all(
            (obj.get("engineering_object_id") or obj.get("object_id")) in node_ids
            for obj in objects
        )
        has_edges = len(edges) > 0
        object_status_ok = all(
            o.get("engineering_status") == ENGINEERING_STATUS_OBJECT_CREATED
            or o.get("engineering_status") == "UNKNOWN_OBJECT"
            for o in objects
        )
        return {
            "name": "Graph Consistency",
            "status": "PASS"
            if contexts
            and objects
            and has_obj_nodes
            and has_edges
            and object_status_ok
            else "FAIL",
            "has_obj_nodes": has_obj_nodes,
            "has_edges": has_edges,
        }
