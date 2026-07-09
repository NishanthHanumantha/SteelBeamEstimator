"""Validate graph-instantiated Engineering Objects — Phase G.5.1."""

from __future__ import annotations

from typing import Any, List, Set

from src.engineering_objects.engineering_object import (
    engineering_objects_applied,
    erc_engineering_object_count,
    erc_engineering_object_ids,
)
from src.engineering_objects.engineering_object_types import (
    ENGINEERING_STATUS_OBJECT_CREATED,
    ENGINEERING_STATUS_UNKNOWN_OBJECT,
    LIFECYCLE_OBJECT_CREATED,
    OBJECT_UNKNOWN,
    VALID_ENGINEERING_STATUSES,
    VALID_OBJECT_LIFECYCLE,
    VALID_OBJECT_TYPES,
)


class EngineeringObjectG51Validator:
    """Verify graph-based engineering object instantiation integrity."""

    def __init__(self, unknown_threshold: float = 0.15) -> None:
        self._unknown_threshold = unknown_threshold

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not engineering_objects_applied(model):
            return {
                "phase": "Phase G.5.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "engineering objects not applied"},
            }

        contexts = model.get("engineering_reinforcement_contexts", [])
        registry = model.get("engineering_object_registry", {})
        objects = registry.get("objects") or model.get("engineering_objects", [])
        graph = model.get("engineering_object_graph", {})

        checks: List[dict[str, Any]] = []
        checks.append(self._check_source_role(objects))
        checks.append(self._check_one_object_per_role(objects))
        checks.append(self._check_registry_counts(registry, contexts))
        checks.append(self._check_graph_connectivity(graph, objects))
        checks.append(self._check_no_duplicates(objects))
        checks.append(self._check_no_orphans(objects, contexts))
        checks.append(self._check_unique_ids(objects))
        checks.append(self._check_belongs_to_erc(objects, contexts))
        checks.append(self._check_lifecycle(objects))
        checks.append(self._check_engineering_status(objects))
        checks.append(self._check_confidence(objects))
        checks.append(self._check_unknown_threshold(objects))

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

    def _check_source_role(self, objects: list) -> dict[str, Any]:
        invalid = [o.get("object_id") for o in objects if not o.get("source_role_id")]
        return {
            "name": "Every Object Has One Source Role",
            "status": "PASS" if objects and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_one_object_per_role(self, objects: list) -> dict[str, Any]:
        seen: Set[str] = set()
        dup_roles: Set[str] = set()
        for obj in objects:
            rid = obj.get("source_role_id")
            if rid in seen:
                dup_roles.add(rid)
            seen.add(rid)
        return {
            "name": "Each Source Role Creates At Most One Object",
            "status": "PASS" if not dup_roles else "FAIL",
            "duplicate_roles": list(dup_roles)[:10],
        }

    def _check_registry_counts(
        self,
        registry: dict[str, Any],
        contexts: list,
    ) -> dict[str, Any]:
        mismatch = []
        erc_counts = {
            e.get("reinforcement_context_id"): e.get("object_count", 0)
            for e in registry.get("erc_registries", [])
        }
        for ctx in contexts:
            erc_id = ctx.get("reinforcement_context_id")
            expected = erc_engineering_object_count(ctx)
            if erc_counts.get(erc_id) != expected:
                mismatch.append(erc_id)
        ok = (
            registry.get("object_count") == len(registry.get("objects", []))
            and len(registry.get("erc_registries", [])) == len(contexts)
            and not mismatch
        )
        return {
            "name": "Object Registry Counts Correct",
            "status": "PASS" if contexts and ok else "FAIL",
            "mismatch": mismatch,
        }

    def _check_graph_connectivity(
        self,
        graph: dict[str, Any],
        objects: list,
    ) -> dict[str, Any]:
        node_ids = {n.get("id") for n in graph.get("nodes", [])}
        missing = [
            o.get("object_id")
            for o in objects
            if o.get("object_id") not in node_ids
        ]
        return {
            "name": "Graph Connectivity Valid",
            "status": "PASS" if objects and not missing else "FAIL",
            "missing_nodes": missing[:10],
        }

    def _check_no_duplicates(self, objects: list) -> dict[str, Any]:
        seen: Set[str] = set()
        duplicates: Set[str] = set()
        for obj in objects:
            oid = str(obj.get("object_id", ""))
            if oid in seen:
                duplicates.add(oid)
            seen.add(oid)
        return {
            "name": "No Duplicate Objects",
            "status": "PASS" if not duplicates else "FAIL",
            "duplicates": list(duplicates)[:10],
        }

    def _check_no_orphans(self, objects: list, contexts: list) -> dict[str, Any]:
        obj_ids = {o.get("object_id") for o in objects}
        orphans = []
        for ctx in contexts:
            for oid in erc_engineering_object_ids(ctx):
                if oid not in obj_ids:
                    orphans.append(oid)
        return {
            "name": "No Orphan Objects",
            "status": "PASS" if not orphans else "FAIL",
            "orphans": orphans[:10],
        }

    def _check_unique_ids(self, objects: list) -> dict[str, Any]:
        ids = [o.get("object_id") for o in objects]
        return {
            "name": "All Object IDs Unique",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
        }

    def _check_belongs_to_erc(self, objects: list, contexts: list) -> dict[str, Any]:
        erc_ids = {c.get("reinforcement_context_id") for c in contexts}
        invalid = [
            o.get("object_id") for o in objects if o.get("owner_context_id") not in erc_ids
        ]
        return {
            "name": "Every Object Belongs To One ERC",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_lifecycle(self, objects: list) -> dict[str, Any]:
        invalid = [
            o.get("object_id")
            for o in objects
            if o.get("lifecycle") not in VALID_OBJECT_LIFECYCLE
            or o.get("lifecycle") != LIFECYCLE_OBJECT_CREATED
        ]
        return {
            "name": "Lifecycle OBJECT_CREATED",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_engineering_status(self, objects: list) -> dict[str, Any]:
        bad = []
        for o in objects:
            if o.get("engineering_status") not in VALID_ENGINEERING_STATUSES:
                bad.append(o.get("object_id"))
            elif o.get("object_type") not in VALID_OBJECT_TYPES:
                bad.append(o.get("object_id"))
        return {
            "name": "Engineering Status Valid",
            "status": "PASS" if not bad else "FAIL",
            "invalid": bad[:10],
        }

    def _check_confidence(self, objects: list) -> dict[str, Any]:
        invalid = [
            o.get("object_id")
            for o in objects
            if o.get("confidence") is None or float(o.get("confidence", -1)) < 0
        ]
        return {
            "name": "Confidence Assigned",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_unknown_threshold(self, objects: list) -> dict[str, Any]:
        total = len(objects)
        unknown = sum(1 for o in objects if o.get("object_type") == OBJECT_UNKNOWN)
        ratio = unknown / total if total else 0.0
        return {
            "name": "Unknown Object Ratio Below Threshold",
            "status": "PASS" if ratio <= self._unknown_threshold else "FAIL",
            "unknown_ratio": round(ratio, 4),
            "threshold": self._unknown_threshold,
        }
