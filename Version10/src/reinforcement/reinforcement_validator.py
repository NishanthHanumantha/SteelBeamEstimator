"""Validate reinforcement loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

from src.reinforcement.reinforcement_document import STATUS_LOADED
from src.reinforcement.reinforcement_workspace import ReinforcementWorkspace


class ReinforcementValidator:
    """Verify reinforcement DXF loading and workspace attachment."""

    def validate(
        self,
        model: dict[str, Any],
        workspaces: List[ReinforcementWorkspace],
    ) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.append(self._check_workspaces_created(workspaces))
        checks.append(self._check_status_loaded(workspaces))
        checks.append(self._check_metadata(workspaces))
        checks.append(self._check_counts(workspaces))
        checks.append(self._check_floor_attachment(model, workspaces))
        checks.append(self._check_project_consistency(model, workspaces))
        checks.append(self._check_registry_exported(model))
        checks.append(self._check_files_exist(workspaces))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "workspace_count": len(workspaces),
            },
        }

    def _check_workspaces_created(self, workspaces: list) -> dict[str, Any]:
        ok = len(workspaces) > 0
        return {
            "name": "Workspace Created",
            "status": "PASS" if ok else "FAIL",
            "count": len(workspaces),
        }

    def _check_status_loaded(self, workspaces: list) -> dict[str, Any]:
        invalid = [ws.workspace_id for ws in workspaces if ws.status != STATUS_LOADED]
        ok = len(invalid) == 0
        return {
            "name": "Status LOADED",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_metadata(self, workspaces: list) -> dict[str, Any]:
        missing = [
            ws.workspace_id
            for ws in workspaces
            if not ws.document.metadata or not ws.document.drawing_name
        ]
        ok = len(missing) == 0
        return {
            "name": "Metadata Present",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_counts(self, workspaces: list) -> dict[str, Any]:
        invalid = [
            ws.workspace_id
            for ws in workspaces
            if ws.document.entity_count <= 0 or ws.document.layer_count <= 0
        ]
        ok = len(invalid) == 0
        return {
            "name": "Entity And Layer Counts",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_floor_attachment(
        self,
        model: dict[str, Any],
        workspaces: list,
    ) -> dict[str, Any]:
        project = model.get("project_workspace", {})
        floor_ids = {f.get("floor_id") for f in project.get("floors", [])}
        mismatched = [ws.workspace_id for ws in workspaces if ws.floor_id not in floor_ids]
        attached = 0
        for floor in project.get("floors", []):
            if floor.get("reinforcement_workspace"):
                attached += 1
        ok = len(mismatched) == 0 and attached == len(workspaces)
        return {
            "name": "Attached To FloorWorkspace",
            "status": "PASS" if ok else "FAIL",
            "attached": attached,
            "mismatched": mismatched,
        }

    def _check_project_consistency(
        self,
        model: dict[str, Any],
        workspaces: list,
    ) -> dict[str, Any]:
        pid = model.get("project_workspace", {}).get("project_id")
        ok = bool(pid) and len(workspaces) > 0
        return {
            "name": "Project Consistency",
            "status": "PASS" if ok else "FAIL",
            "project_id": pid,
        }

    def _check_registry_exported(self, model: dict[str, Any]) -> dict[str, Any]:
        reg = model.get("reinforcement_registry", {})
        ok = bool(reg.get("documents"))
        return {
            "name": "Registry Exported",
            "status": "PASS" if ok else "FAIL",
            "document_count": reg.get("document_count", 0),
        }

    def _check_files_exist(self, workspaces: list) -> dict[str, Any]:
        missing = []
        for ws in workspaces:
            path = Path(ws.document.source_file)
            if not path.exists():
                missing.append(ws.document.document_id)
        ok = len(missing) == 0
        return {
            "name": "Reinforcement File Exists",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }
