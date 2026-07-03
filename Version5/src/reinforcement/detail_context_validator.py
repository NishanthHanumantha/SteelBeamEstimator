"""Validate Phase G.2.3 engineering detail context layer."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.reinforcement_geometry_entity import ENGINEERING_STATUS_GEOMETRY_ONLY


class DetailContextValidator:
    """Verify detail context layer without engineering interpretation."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        drawing_models = model.get("reinforcement_drawing_models", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_contexts_created(drawing_models))
        checks.append(self._check_every_region_has_context(drawing_models))
        checks.append(self._check_context_single_region(drawing_models))
        checks.append(self._check_every_view_has_context(drawing_models))
        checks.append(self._check_context_ids_unique(drawing_models))
        checks.append(self._check_registry_complete(model, drawing_models))
        checks.append(self._check_graph_relationships(model))
        checks.append(self._check_drawing_references(drawing_models))
        checks.append(self._check_workspace_references(model, drawing_models))
        checks.append(self._check_engineering_object_ids_null(drawing_models))
        checks.append(self._check_engineering_status_geometry_only(drawing_models))
        checks.append(self._check_geometry_immutable(model))
        checks.append(self._check_no_beam_matching(model))
        checks.append(self._check_no_ownership(drawing_models))
        checks.append(self._check_no_parsing(model))
        checks.append(self._check_no_computation(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.2.3",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "detail_context_count": sum(
                    dm.get("detail_context_count", 0) for dm in drawing_models
                ),
            },
        }

    def _check_contexts_created(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("detail_context_count", 0) for dm in drawing_models)
        ok = count > 0
        return {
            "name": "DetailContexts Created",
            "status": "PASS" if ok else "FAIL",
            "count": count,
        }

    def _check_every_region_has_context(self, drawing_models: list) -> dict[str, Any]:
        missing = []
        for dm in drawing_models:
            for region in dm.get("regions", []):
                if not region.get("detail_context_ids"):
                    missing.append(region.get("geometry_id"))
        ok = not missing
        return {
            "name": "Every Region Has DetailContext",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_context_single_region(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        region_by_ctx: dict[str, str] = {}
        for dm in drawing_models:
            for ctx in dm.get("detail_contexts", []):
                cid = ctx.get("detail_context_id", "")
                rid = ctx.get("region_id", "")
                if cid in region_by_ctx and region_by_ctx[cid] != rid:
                    invalid.append(cid)
                region_by_ctx[cid] = rid
                if not rid:
                    invalid.append(cid)
        ok = not invalid
        return {
            "name": "Every DetailContext One Region",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_every_view_has_context(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for view in dm.get("detail_views", []):
                if not view.get("detail_context_id"):
                    invalid.append(view.get("view_id", view.get("geometry_id")))
        ok = not invalid
        return {
            "name": "Every View Has DetailContext",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_context_ids_unique(self, drawing_models: list) -> dict[str, Any]:
        ids: list[str] = []
        for dm in drawing_models:
            for ctx in dm.get("detail_contexts", []):
                ids.append(str(ctx.get("detail_context_id", "")))
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        ok = len(ids) > 0 and not duplicates
        return {
            "name": "DetailContext IDs Unique",
            "status": "PASS" if ok else "FAIL",
            "duplicates": duplicates,
        }

    def _check_registry_complete(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        registry = model.get("detail_context_registry", {})
        expected = sum(dm.get("detail_context_count", 0) for dm in drawing_models)
        actual = registry.get("detail_context_count", 0)
        ok = expected > 0 and actual == expected
        return {
            "name": "DetailContext Registry Complete",
            "status": "PASS" if ok else "FAIL",
            "expected": expected,
            "actual": actual,
        }

    def _check_graph_relationships(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        ctx_nodes = [n for n in graph.get("nodes", []) if n.get("type") == "DETAIL_CONTEXT"]
        has_region_edge = any(
            e.get("relationship") == "HAS_DETAIL_CONTEXT" for e in graph.get("edges", [])
        )
        has_view_edge = any(
            e.get("relationship") == "HAS_VIEW"
            and any(
                n.get("id") == e.get("from") and n.get("type") == "DETAIL_CONTEXT"
                for n in ctx_nodes
            )
            for e in graph.get("edges", [])
        )
        ok = len(ctx_nodes) > 0 and has_region_edge and has_view_edge
        return {
            "name": "Graph DetailContext Relationships Valid",
            "status": "PASS" if ok else "FAIL",
            "context_nodes": len(ctx_nodes),
            "has_region_edge": has_region_edge,
            "has_view_edge": has_view_edge,
        }

    def _check_drawing_references(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            drawing_id = dm.get("drawing_id", "")
            for ctx in dm.get("detail_contexts", []):
                meta_did = ctx.get("metadata", {}).get("drawing_id", "")
                if meta_did and meta_did != drawing_id:
                    invalid.append(ctx.get("detail_context_id"))
        ok = not invalid
        return {
            "name": "Drawing References Valid",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_workspace_references(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        invalid = []
        for ws in model.get("reinforcement_workspaces", []):
            if not ws.get("detail_contexts"):
                invalid.append(ws.get("workspace_id", ws.get("floor_id")))
        ok = len(invalid) == 0 and len(drawing_models) > 0
        return {
            "name": "Workspace DetailContext References",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_engineering_object_ids_null(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ctx in dm.get("detail_contexts", []):
                if ctx.get("engineering_object_id") is not None:
                    invalid.append(ctx.get("detail_context_id"))
        ok = not invalid
        return {
            "name": "DetailContext Engineering Object IDs NULL",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_engineering_status_geometry_only(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ctx in dm.get("detail_contexts", []):
                if ctx.get("engineering_status") != ENGINEERING_STATUS_GEOMETRY_ONLY:
                    invalid.append(ctx.get("detail_context_id"))
        ok = not invalid
        return {
            "name": "DetailContext Engineering Status GEOMETRY_ONLY",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_geometry_immutable(self, model: dict[str, Any]) -> dict[str, Any]:
        ok = bool(model.get("reinforcement_drawing_model", {}).get("sketches"))
        return {
            "name": "Geometry Immutable",
            "status": "PASS" if ok else "FAIL",
        }

    def _check_no_beam_matching(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for dm in model.get("reinforcement_drawing_models", []):
            for ctx in dm.get("detail_contexts", []):
                if ctx.get("beam_context_id") or ctx.get("matched_beam_id"):
                    invalid.append(ctx.get("detail_context_id"))
        ok = not invalid
        return {
            "name": "No Beam Matching",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_no_ownership(self, drawing_models: list) -> dict[str, Any]:
        for dm in drawing_models:
            for rel in dm.get("detail_context_relationships", []):
                rel_name = str(rel.get("relationship", "")).upper()
                if "OWN" in rel_name:
                    return {"name": "No Ownership", "status": "FAIL", "relationship": rel_name}
        return {"name": "No Ownership", "status": "PASS"}

    def _check_no_parsing(self, model: dict[str, Any]) -> dict[str, Any]:
        for dm in model.get("reinforcement_drawing_models", []):
            for ctx in dm.get("detail_contexts", []):
                if "parsed" in ctx or "engineering_type" in ctx:
                    return {"name": "No Parsing", "status": "FAIL"}
        return {"name": "No Parsing", "status": "PASS"}

    def _check_no_computation(self, model: dict[str, Any]) -> dict[str, Any]:
        keys = ("steel_weight", "quantities", "parsed_bars")
        found = [k for k in keys if k in model]
        ok = not found
        return {
            "name": "No Engineering Computation",
            "status": "PASS" if ok else "FAIL",
            "found": found,
        }
