"""Validate project workspace structure."""

from __future__ import annotations

from typing import Any, List


class ProjectValidator:
    """Verify project workspace completeness."""

    def validate(self, workspace: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.append(self._check_project_id(workspace))
        checks.append(self._check_general_notes(workspace))
        checks.append(self._check_floors(workspace))
        checks.append(self._check_services(workspace))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase F.7",
            "scope": "project",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
        }

    def _check_project_id(self, workspace: dict[str, Any]) -> dict[str, Any]:
        ok = bool(workspace.get("project_id")) and workspace.get("project_id").startswith("PROJECT::")
        return {
            "name": "Project ID",
            "status": "PASS" if ok else "FAIL",
            "project_id": workspace.get("project_id"),
        }

    def _check_general_notes(self, workspace: dict[str, Any]) -> dict[str, Any]:
        gn = workspace.get("general_notes", {})
        ok = bool(gn.get("knowledge_id") or gn.get("document_id"))
        return {
            "name": "General Notes Reference",
            "status": "PASS" if ok else "FAIL",
            "knowledge_id": gn.get("knowledge_id"),
        }

    def _check_floors(self, workspace: dict[str, Any]) -> dict[str, Any]:
        floors = workspace.get("floors", [])
        ok = len(floors) >= 1
        return {
            "name": "Floor Registry",
            "status": "PASS" if ok else "FAIL",
            "floor_count": len(floors),
        }

    def _check_services(self, workspace: dict[str, Any]) -> dict[str, Any]:
        services = workspace.get("services", {})
        ok = bool(services.get("service_id") or services.get("initialized"))
        return {
            "name": "Services Reference",
            "status": "PASS" if ok else "FAIL",
            "service_id": services.get("service_id"),
        }
