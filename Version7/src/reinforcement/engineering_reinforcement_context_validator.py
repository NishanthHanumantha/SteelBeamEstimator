"""Validate Phase G.4 engineering reinforcement context and ownership resolution."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.engineering_object import engineering_object_instantiation_applied
from src.reinforcement.engineering_reinforcement_context import (
    ENGINEERING_STATUS_OWNERSHIP_READY,
    FUTURE_PLACEHOLDERS,
    OWNERSHIP_STATUS_RESOLVED,
    PREFIX_ERC,
)


class EngineeringReinforcementContextValidator:
    """Verify ERC creation and complete ownership resolution."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        drawing_models = model.get("reinforcement_drawing_models", [])
        contexts = model.get("engineering_reinforcement_contexts", [])
        beam_matches = model.get("beam_matches", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_one_erc_per_beam_match(beam_matches, contexts))
        checks.append(self._check_one_erc_per_matched_beam(contexts))
        checks.append(self._check_every_view_owned(drawing_models, model))
        checks.append(self._check_every_sketch_owned(drawing_models, model))
        checks.append(self._check_every_text_owned(drawing_models, model))
        checks.append(self._check_every_leader_owned(drawing_models, model))
        checks.append(self._check_every_block_owned(drawing_models, model))
        checks.append(self._check_no_duplicate_ownership(model))
        checks.append(self._check_no_orphan_entities(drawing_models, model))
        checks.append(self._check_beam_context_updated(model, contexts))
        checks.append(self._check_graph_relationships(model))
        checks.append(self._check_registry_complete(model, contexts))
        checks.append(self._check_workspace_updated(model))
        checks.append(self._check_drawing_set_updated(model))
        checks.append(self._check_ownership_status_resolved(contexts))
        checks.append(self._check_future_placeholders(contexts))
        checks.append(self._check_no_parsing(model))
        checks.append(self._check_no_engineering_objects(model))
        checks.append(self._check_no_quantities(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.4",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "context_count": len(contexts),
            },
        }

    def _owned_entity_ids(self, drawing_models: list) -> set[str]:
        owned: set[str] = set()
        for dm in drawing_models:
            for key in ("detail_views", "sketches", "text_objects", "leaders", "blocks"):
                for item in dm.get(key, []):
                    if item.get("ownership"):
                        owned.add(str(item.get("geometry_id", item.get("view_id", ""))))
        return owned

    def _check_one_erc_per_beam_match(
        self,
        beam_matches: list,
        contexts: list,
    ) -> dict[str, Any]:
        match_ids = {m.get("beam_match_id") for m in beam_matches}
        erc_by_match = {c.get("beam_match_id"): c for c in contexts}
        missing = [mid for mid in match_ids if mid not in erc_by_match]
        return {
            "name": "One ERC Per BeamMatch",
            "status": "PASS" if beam_matches and not missing and len(contexts) == len(beam_matches) else "FAIL",
            "matches": len(beam_matches),
            "contexts": len(contexts),
            "missing": missing,
        }

    def _check_one_erc_per_matched_beam(self, contexts: list) -> dict[str, Any]:
        beam_ids = [c.get("beam_context_id") for c in contexts]
        duplicates = sorted({b for b in beam_ids if beam_ids.count(b) > 1})
        return {
            "name": "One ERC Per Matched Beam",
            "status": "PASS" if contexts and not duplicates else "FAIL",
            "duplicates": duplicates,
        }

    def _detail_scoped_entity_ids(
        self,
        drawing_models: list,
        model: dict[str, Any],
    ) -> set[str]:
        scoped: set[str] = set()
        for dm in drawing_models:
            for view in dm.get("detail_views", []):
                scoped.add(str(view.get("view_id", view.get("geometry_id", ""))))
                scoped.update(str(gid) for gid in view.get("geometry_entities", []))
                scoped.update(str(gid) for gid in view.get("text_entities", []))
                scoped.update(str(gid) for gid in view.get("leader_entities", []))
                scoped.update(str(gid) for gid in view.get("block_entities", []))
        for rel in model.get("ownership_relationships", []):
            pass
        drawing_model = model.get("reinforcement_drawing_model", {})
        for rel in drawing_model.get("relationships", []):
            rel_name = str(rel.get("relationship", ""))
            if rel_name.startswith(("REGION_CONTAINS_", "SKETCH_CONTAINS_")):
                scoped.add(str(rel.get("target_id", "")))
        return {item for item in scoped if item}

    def _check_entities_owned(
        self,
        drawing_models: list,
        model: dict[str, Any],
        collection_key: str,
        label: str,
    ) -> dict[str, Any]:
        scoped = self._detail_scoped_entity_ids(drawing_models, model)
        missing = []
        for dm in drawing_models:
            for item in dm.get(collection_key, []):
                gid = str(item.get("geometry_id", item.get("view_id", "")))
                if gid not in scoped:
                    continue
                if not item.get("ownership"):
                    missing.append(gid)
        return {
            "name": label,
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
            "missing": missing[:10],
        }

    def _check_every_view_owned(
        self,
        drawing_models: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        return self._check_entities_owned(drawing_models, model, "detail_views", "Every DetailView Owned")

    def _check_every_sketch_owned(
        self,
        drawing_models: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        return self._check_entities_owned(drawing_models, model, "sketches", "Every Sketch Owned")

    def _check_every_text_owned(
        self,
        drawing_models: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        return self._check_entities_owned(drawing_models, model, "text_objects", "Every Text Owned")

    def _check_every_leader_owned(
        self,
        drawing_models: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        return self._check_entities_owned(drawing_models, model, "leaders", "Every Leader Owned")

    def _check_every_block_owned(
        self,
        drawing_models: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        return self._check_entities_owned(drawing_models, model, "blocks", "Every Block Owned")

    def _check_no_duplicate_ownership(self, model: dict[str, Any]) -> dict[str, Any]:
        registry = model.get("ownership_registry", {})
        entries = registry.get("entries", [])
        geometry_ids = [e.get("geometry_id") for e in entries]
        duplicates = sorted({g for g in geometry_ids if geometry_ids.count(g) > 1})
        return {
            "name": "No Duplicate Ownership",
            "status": "PASS" if entries and not duplicates else "FAIL",
            "duplicates": duplicates,
        }

    def _check_no_orphan_entities(
        self,
        drawing_models: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        scoped = self._detail_scoped_entity_ids(drawing_models, model)
        orphans = []
        for dm in drawing_models:
            for key in ("detail_views", "sketches", "text_objects", "leaders", "blocks"):
                for item in dm.get(key, []):
                    gid = str(item.get("geometry_id", item.get("view_id", "")))
                    if gid not in scoped:
                        continue
                    if not item.get("ownership"):
                        orphans.append(gid)
        return {
            "name": "No Orphan Entities",
            "status": "PASS" if not orphans else "FAIL",
            "orphan_count": len(orphans),
            "orphans": orphans[:10],
        }

    def _check_beam_context_updated(
        self,
        model: dict[str, Any],
        contexts: list,
    ) -> dict[str, Any]:
        erc_by_beam = {c.get("beam_context_id"): c for c in contexts}
        invalid = []
        for ctx in model.get("beam_engineering_contexts", []):
            cid = ctx.get("context_id")
            erc = erc_by_beam.get(cid)
            if not erc:
                continue
            if ctx.get("reinforcement_context_id") != erc.get("reinforcement_context_id"):
                invalid.append(cid)
            if ctx.get("ownership_status") != OWNERSHIP_STATUS_RESOLVED:
                invalid.append(cid)
        return {
            "name": "BeamContext Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_graph_relationships(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("erc_ownership_graph", {})
        edges = graph.get("edges", [])
        has_creates = any(e.get("relationship") == "CREATES" for e in edges)
        has_has_context = any(
            e.get("relationship") == "HAS_REINFORCEMENT_CONTEXT" for e in edges
        )
        has_owns = any(
            e.get("relationship", "").startswith("OWNS_") for e in edges
        )
        ok = len(graph.get("nodes", [])) > 0 and has_creates and has_has_context and has_owns
        return {
            "name": "Graph Relationships Valid",
            "status": "PASS" if ok else "FAIL",
            "has_creates": has_creates,
            "has_has_context": has_has_context,
            "has_owns": has_owns,
        }

    def _check_registry_complete(
        self,
        model: dict[str, Any],
        contexts: list,
    ) -> dict[str, Any]:
        registry = model.get("engineering_reinforcement_context_registry", {})
        expected = len(contexts)
        actual = registry.get("context_count", 0)
        return {
            "name": "Registry Complete",
            "status": "PASS" if expected > 0 and actual == expected else "FAIL",
            "expected": expected,
            "actual": actual,
        }

    def _check_workspace_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        project = model.get("project_workspace", {})
        if not project.get("engineering_reinforcement_context_registry"):
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "registry"}
        if not project.get("ownership_summary"):
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "summary"}
        return {"name": "Workspace Updated", "status": "PASS"}

    def _check_drawing_set_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for ds in model.get("drawing_sets", []):
            if not ds.get("engineering_reinforcement_context_registry"):
                invalid.append(ds.get("drawing_set_id"))
            if not ds.get("ownership_summary"):
                invalid.append(ds.get("drawing_set_id"))
        return {
            "name": "DrawingSet Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_ownership_status_resolved(self, contexts: list) -> dict[str, Any]:
        invalid = [
            c.get("reinforcement_context_id")
            for c in contexts
            if c.get("ownership_status") != OWNERSHIP_STATUS_RESOLVED
            or c.get("engineering_status") != ENGINEERING_STATUS_OWNERSHIP_READY
        ]
        return {
            "name": "Ownership Status RESOLVED",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_future_placeholders(self, contexts: list) -> dict[str, Any]:
        invalid = []
        for ctx in contexts:
            future = ctx.get("future", {})
            for key in FUTURE_PLACEHOLDERS:
                if key not in future:
                    invalid.append(ctx.get("reinforcement_context_id"))
        return {
            "name": "Future Placeholders Exist",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_parsing(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("parsed_bars", "bar_schedule") if k in model]
        return {
            "name": "No Reinforcement Parsing",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_engineering_objects(self, model: dict[str, Any]) -> dict[str, Any]:
        if engineering_object_instantiation_applied(model):
            return {
                "name": "No Engineering Objects",
                "status": "PASS",
                "note": "G.5.1 instantiation applied",
            }
        found = [k for k in ("engineering_objects",) if k in model]
        return {
            "name": "No Engineering Objects",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_quantities(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("quantities", "steel_weight", "boq") if k in model]
        return {
            "name": "No Quantity Computation",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }
