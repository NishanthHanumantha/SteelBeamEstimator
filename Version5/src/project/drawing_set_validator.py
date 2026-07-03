"""Validate drawing set assembly and beam context identity."""

from __future__ import annotations

from typing import Any, List

from src.project.drawing_identity import DRAWING_TYPE_GENERAL_NOTES
from src.project.drawing_set import DrawingSet, STATUS_COMPLETE


class DrawingSetValidator:
    """Verify drawing sets, workspace links, and beam context identity."""

    def validate(
        self,
        model: dict[str, Any],
        drawing_sets: List[DrawingSet],
    ) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.append(self._check_sets_created(drawing_sets))
        checks.append(self._check_framing_attached(drawing_sets))
        checks.append(self._check_reinforcement_attached(drawing_sets))
        checks.append(self._check_general_notes_referenced(drawing_sets))
        checks.append(self._check_floor_workspace_linked(model, drawing_sets))
        checks.append(self._check_context_drawing_set_id(model))
        checks.append(self._check_context_drawing_id(model))
        checks.append(self._check_one_set_per_floor(drawing_sets))
        checks.append(self._check_no_duplicated_general_notes(drawing_sets))
        checks.append(self._check_project_graph_updated(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.1.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "drawing_set_count": len(drawing_sets),
            },
        }

    def _check_sets_created(self, drawing_sets: list) -> dict[str, Any]:
        ok = len(drawing_sets) > 0
        return {
            "name": "Drawing Set Created",
            "status": "PASS" if ok else "FAIL",
            "count": len(drawing_sets),
        }

    def _check_framing_attached(self, drawing_sets: list) -> dict[str, Any]:
        missing = [
            ds.drawing_set_id
            for ds in drawing_sets
            if not ds.drawings.get("framing")
        ]
        ok = len(missing) == 0
        return {
            "name": "Framing Drawing Attached",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_reinforcement_attached(self, drawing_sets: list) -> dict[str, Any]:
        missing = [
            ds.drawing_set_id
            for ds in drawing_sets
            if not ds.drawings.get("reinforcement")
        ]
        ok = len(missing) == 0
        return {
            "name": "Reinforcement Drawing Attached",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_general_notes_referenced(self, drawing_sets: list) -> dict[str, Any]:
        gn_id = None
        for ds in drawing_sets:
            ref = ds.drawings.get("general_notes")
            if ref:
                gn_id = ref
                break
        missing = [
            ds.drawing_set_id
            for ds in drawing_sets
            if not ds.drawings.get("general_notes")
        ]
        ok = gn_id is not None and len(missing) == 0
        return {
            "name": "General Notes Referenced",
            "status": "PASS" if ok else "FAIL",
            "general_notes_id": gn_id,
            "missing": missing,
        }

    def _check_floor_workspace_linked(
        self,
        model: dict[str, Any],
        drawing_sets: list,
    ) -> dict[str, Any]:
        floor_ids = {
            f.get("floor_id")
            for f in model.get("project_workspace", {}).get("floors", [])
        }
        unlinked = [ds.drawing_set_id for ds in drawing_sets if ds.floor_id not in floor_ids]
        ok = len(unlinked) == 0
        return {
            "name": "Floor Workspace Linked",
            "status": "PASS" if ok else "FAIL",
            "unlinked": unlinked,
        }

    def _check_context_drawing_set_id(self, model: dict[str, Any]) -> dict[str, Any]:
        missing = [
            ctx.get("context_id")
            for ctx in model.get("beam_engineering_contexts", [])
            if not ctx.get("drawing_set_id")
        ]
        ok = len(model.get("beam_engineering_contexts", [])) > 0 and len(missing) == 0
        return {
            "name": "Beam Contexts Reference drawing_set_id",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_context_drawing_id(self, model: dict[str, Any]) -> dict[str, Any]:
        missing = [
            ctx.get("context_id")
            for ctx in model.get("beam_engineering_contexts", [])
            if not ctx.get("drawing_id")
        ]
        ok = len(model.get("beam_engineering_contexts", [])) > 0 and len(missing) == 0
        return {
            "name": "Beam Contexts Reference drawing_id",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_one_set_per_floor(self, drawing_sets: list) -> dict[str, Any]:
        floor_ids = [ds.floor_id for ds in drawing_sets]
        ok = len(floor_ids) == len(set(floor_ids))
        return {
            "name": "One Drawing Set Per Floor",
            "status": "PASS" if ok else "FAIL",
            "floor_ids": floor_ids,
        }

    def _check_no_duplicated_general_notes(self, drawing_sets: list) -> dict[str, Any]:
        gn_ids = [ds.drawings.get("general_notes") for ds in drawing_sets]
        unique = {gid for gid in gn_ids if gid}
        ok = len(unique) <= 1
        return {
            "name": "No Duplicated General Notes",
            "status": "PASS" if ok else "FAIL",
            "unique_general_notes_ids": list(unique),
        }

    def _check_project_graph_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        nodes = graph.get("nodes", [])
        has_set = any(n.get("type") == "DRAWING_SET" for n in nodes)
        ok = has_set and bool(model.get("drawing_sets"))
        return {
            "name": "Project Graph Updated",
            "status": "PASS" if ok else "FAIL",
            "drawing_set_nodes": sum(1 for n in nodes if n.get("type") == "DRAWING_SET"),
        }
