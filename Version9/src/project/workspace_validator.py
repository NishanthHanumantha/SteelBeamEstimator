"""Validate workspace assembly."""

from __future__ import annotations

from typing import Any, List

from src.framing.engineering_ids import SERVICES_ID
from src.framing.engineering_state_machine import VALID_COMPUTATION_STATES


class WorkspaceValidator:
    """Verify F.7 workspace integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.append(self._check_project_exists(model))
        checks.append(self._check_general_notes(model))
        checks.append(self._check_floors(model))
        checks.append(self._check_floor_contexts(model))
        checks.append(self._check_services(model))
        checks.append(self._check_rule_references(model))
        checks.append(self._check_no_duplicated_knowledge(model))
        checks.append(self._check_contexts_belong_to_floor(model))
        checks.append(self._check_floors_belong_to_project(model))

        checks.append(self._check_computation_states(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase F.7",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
            },
        }

    def _check_project_exists(self, model: dict[str, Any]) -> dict[str, Any]:
        ws = model.get("project_workspace", {})
        ok = bool(ws.get("project_id"))
        return {
            "name": "Project Exists",
            "status": "PASS" if ok else "FAIL",
            "project_id": ws.get("project_id"),
        }

    def _check_general_notes(self, model: dict[str, Any]) -> dict[str, Any]:
        ws = model.get("project_workspace", {})
        gn_count = 1 if ws.get("general_notes", {}).get("knowledge_id") else 0
        ok = gn_count == 1
        return {
            "name": "One General Notes",
            "status": "PASS" if ok else "FAIL",
            "count": gn_count,
        }

    def _check_floors(self, model: dict[str, Any]) -> dict[str, Any]:
        floors = model.get("project_workspace", {}).get("floors", [])
        ok = len(floors) >= 1
        return {
            "name": "Floors Allowed",
            "status": "PASS" if ok else "FAIL",
            "floor_count": len(floors),
        }

    def _check_floor_contexts(self, model: dict[str, Any]) -> dict[str, Any]:
        contexts = model.get("beam_engineering_contexts", [])
        ok = len(contexts) > 0
        return {
            "name": "Floor Contexts Valid",
            "status": "PASS" if ok else "FAIL",
            "context_count": len(contexts),
        }

    def _check_services(self, model: dict[str, Any]) -> dict[str, Any]:
        reg = model.get("engineering_services_registry", {})
        ok = reg.get("initialized") and reg.get("service_count", 0) >= 5
        return {
            "name": "Services Initialized",
            "status": "PASS" if ok else "FAIL",
            "service_count": reg.get("service_count"),
        }

    def _check_rule_references(self, model: dict[str, Any]) -> dict[str, Any]:
        missing = 0
        for ctx in model.get("beam_engineering_contexts", []):
            ref = ctx.get("rule_reference", {})
            if not ref.get("rule_id") or not ref.get("knowledge_id"):
                missing += 1
            if ctx.get("services") != SERVICES_ID:
                missing += 1
        ok = missing == 0
        return {
            "name": "Rule References Valid",
            "status": "PASS" if ok else "FAIL",
            "invalid": missing,
        }

    def _check_no_duplicated_knowledge(self, model: dict[str, Any]) -> dict[str, Any]:
        embedded = 0
        for ctx in model.get("beam_engineering_contexts", []):
            if ctx.get("project_engineering_rules"):
                embedded += 1
            if ctx.get("estimator_rules"):
                embedded += 1
            if ctx.get("project_defaults"):
                embedded += 1
        ok = embedded == 0
        return {
            "name": "No Duplicated Knowledge",
            "status": "PASS" if ok else "FAIL",
            "embedded_copies": embedded,
        }

    def _check_contexts_belong_to_floor(self, model: dict[str, Any]) -> dict[str, Any]:
        floor_ids = {
            f.get("floor_id")
            for f in model.get("project_workspace", {}).get("floors", [])
        }
        mismatched = [
            c.get("context_id")
            for c in model.get("beam_engineering_contexts", [])
            if c.get("floor_id") not in floor_ids
        ]
        ok = len(mismatched) == 0
        return {
            "name": "Contexts Belong To Floor",
            "status": "PASS" if ok else "FAIL",
            "mismatched": mismatched[:5],
        }

    def _check_floors_belong_to_project(self, model: dict[str, Any]) -> dict[str, Any]:
        pid = model.get("project_workspace", {}).get("project_id")
        mismatched = [
            f.get("floor_id")
            for f in model.get("project_workspace", {}).get("floors", [])
            if f.get("metadata", {}).get("project_id") != pid
        ]
        ok = len(mismatched) == 0
        return {
            "name": "Floors Belong To Project",
            "status": "PASS" if ok else "FAIL",
            "mismatched": mismatched,
        }

    def _check_computation_states(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = 0
        for beam in model.get("beams", []):
            for key in ("reinforcement", "quantities", "boq"):
                st = beam.get(key, {}).get("status")
                if st and st not in VALID_COMPUTATION_STATES:
                    invalid += 1
        ok = invalid == 0
        return {
            "name": "Computation States Valid",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }
