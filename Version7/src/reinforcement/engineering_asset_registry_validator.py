"""Validate Phase G.4.1 engineering asset registry scaffolding."""

from __future__ import annotations

from typing import Any, List, Set

from src.reinforcement.engineering_asset_registry import (
    PREFIX_ASSET_REGISTRY,
    engineering_assets_applied,
)
from src.reinforcement.engineering_reinforcement_context import (
    ENGINEERING_RESULTS_PLACEHOLDERS,
)


class EngineeringAssetRegistryValidator:
    """Verify asset registry structure and ERC engineering_assets sections."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not engineering_assets_applied(model):
            return {
                "phase": "Phase G.4.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "engineering_asset_registry not applied"},
            }

        contexts = model.get("engineering_reinforcement_contexts", [])
        registry = model.get("engineering_asset_registry", {})
        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_erc_has_registry(contexts, registry))
        checks.append(self._check_registry_ids_unique(registry))
        checks.append(self._check_registry_references_owned_assets(contexts, registry))
        checks.append(self._check_no_duplicated_geometry_ids(registry))
        checks.append(self._check_engineering_results_exists(contexts))
        checks.append(self._check_engineering_results_placeholders_null(contexts))
        checks.append(self._check_engineering_assets_authoritative(contexts))
        checks.append(self._check_workspace_updated(model))
        checks.append(self._check_drawing_set_updated(model))
        checks.append(self._check_graph_updated(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.4.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "registry_count": registry.get("registry_count", 0),
            },
        }

    def _check_every_erc_has_registry(
        self,
        contexts: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        reg_by_erc = {
            r.get("reinforcement_context_id"): r
            for r in registry.get("registries", [])
        }
        missing = [
            c.get("reinforcement_context_id")
            for c in contexts
            if c.get("reinforcement_context_id") not in reg_by_erc
        ]
        return {
            "name": "Every ERC Has Registry",
            "status": "PASS" if contexts and not missing and len(reg_by_erc) == len(contexts) else "FAIL",
            "context_count": len(contexts),
            "registry_count": len(reg_by_erc),
            "missing": missing,
        }

    def _check_registry_ids_unique(self, registry: dict[str, Any]) -> dict[str, Any]:
        ids = [r.get("asset_registry_id") for r in registry.get("registries", [])]
        unique = len(ids) == len(set(ids))
        valid_prefix = all(
            str(rid or "").startswith(f"{PREFIX_ASSET_REGISTRY}::")
            for rid in ids
        )
        return {
            "name": "Registry IDs Unique",
            "status": "PASS" if ids and unique and valid_prefix else "FAIL",
            "count": len(ids),
            "unique": unique,
        }

    def _check_registry_references_owned_assets(
        self,
        contexts: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        invalid = []
        ctx_by_id = {c.get("reinforcement_context_id"): c for c in contexts}
        for reg in registry.get("registries", []):
            erc_id = reg.get("reinforcement_context_id")
            ctx = ctx_by_id.get(erc_id, {})
            for key, owned_key in (
                ("views", "owned_views"),
                ("geometry", "owned_geometry"),
                ("text", "owned_text"),
                ("leaders", "owned_leaders"),
                ("blocks", "owned_blocks"),
            ):
                if list(reg.get(key, [])) != list(ctx.get(owned_key, [])):
                    invalid.append(erc_id)
                    break
        return {
            "name": "Registry References Owned Assets Only",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_no_duplicated_geometry_ids(self, registry: dict[str, Any]) -> dict[str, Any]:
        seen: Set[str] = set()
        duplicates: Set[str] = set()
        for reg in registry.get("registries", []):
            for gid in reg.get("geometry", []):
                if gid in seen:
                    duplicates.add(gid)
                seen.add(gid)
        return {
            "name": "No Duplicated Geometry IDs",
            "status": "PASS" if not duplicates else "FAIL",
            "duplicates": list(duplicates)[:10],
        }

    def _check_engineering_results_exists(self, contexts: list) -> dict[str, Any]:
        missing = [
            c.get("reinforcement_context_id")
            for c in contexts
            if "engineering_results" not in c
        ]
        return {
            "name": "Engineering Results Exists",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing": missing,
        }

    def _check_engineering_results_placeholders_null(self, contexts: list) -> dict[str, Any]:
        invalid = []
        for ctx in contexts:
            results = ctx.get("engineering_results", {})
            for key in ENGINEERING_RESULTS_PLACEHOLDERS:
                if key not in results:
                    invalid.append(ctx.get("reinforcement_context_id"))
                    break
                if results.get(key) is not None:
                    invalid.append(ctx.get("reinforcement_context_id"))
                    break
        return {
            "name": "Engineering Results Placeholders Null",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_engineering_assets_authoritative(self, contexts: list) -> dict[str, Any]:
        invalid = []
        for ctx in contexts:
            assets = ctx.get("engineering_assets", {})
            if not assets:
                invalid.append(ctx.get("reinforcement_context_id"))
                continue
            for key, owned_key in (
                ("views", "owned_views"),
                ("geometry", "owned_geometry"),
                ("text", "owned_text"),
                ("leaders", "owned_leaders"),
                ("blocks", "owned_blocks"),
            ):
                if list(assets.get(key, [])) != list(ctx.get(owned_key, [])):
                    invalid.append(ctx.get("reinforcement_context_id"))
                    break
        return {
            "name": "Engineering Assets Authoritative",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    def _check_workspace_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        project = model.get("project_workspace", {})
        if not project.get("asset_registry"):
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "asset_registry"}
        if project.get("asset_registry_count", 0) <= 0:
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "asset_registry_count"}
        if not project.get("engineering_result_summary"):
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "engineering_result_summary"}
        if not project.get("lifecycle_summary"):
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "lifecycle_summary"}
        return {"name": "Workspace Updated", "status": "PASS"}

    def _check_drawing_set_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for ds in model.get("drawing_sets", []):
            if not ds.get("asset_registry"):
                invalid.append(ds.get("drawing_set_id"))
            if ds.get("asset_registry_count", 0) <= 0:
                invalid.append(ds.get("drawing_set_id"))
            if not ds.get("engineering_result_summary"):
                invalid.append(ds.get("drawing_set_id"))
            if not ds.get("lifecycle_summary"):
                invalid.append(ds.get("drawing_set_id"))
        return {
            "name": "DrawingSet Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_graph_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_types = {n.get("type") for n in nodes}
        has_registry = "ENGINEERING_ASSET_REGISTRY" in node_types
        has_lifecycle = "ERC_LIFECYCLE" in node_types
        has_results = "ENGINEERING_RESULTS_PLACEHOLDER" in node_types
        has_asset_edge = any(e.get("relationship") == "HAS_ASSET_REGISTRY" for e in edges)
        has_lifecycle_edge = any(e.get("relationship") == "HAS_LIFECYCLE" for e in edges)
        has_results_edge = any(
            e.get("relationship") == "HAS_ENGINEERING_RESULTS" for e in edges
        )
        ok = has_registry and has_lifecycle and has_results and has_asset_edge and has_lifecycle_edge and has_results_edge
        return {
            "name": "Graph Updated",
            "status": "PASS" if ok else "FAIL",
            "has_registry": has_registry,
            "has_lifecycle": has_lifecycle,
            "has_results": has_results,
        }
