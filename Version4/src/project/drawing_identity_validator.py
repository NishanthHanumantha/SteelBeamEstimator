"""Validate drawing identity and floor detection."""

from __future__ import annotations

from typing import Any, List

from src.framing.engineering_ids import DEFAULT_FLOOR_SLUG, floor_id
from src.project.drawing_identity import (
    DRAWING_TYPE_BEAM_REINFORCEMENT,
    DRAWING_TYPE_FRAMING_PLAN,
    DRAWING_TYPE_GENERAL_NOTES,
    STATUS_IDENTIFIED,
)


class DrawingIdentityValidator:
    """Verify drawing identity extraction and floor detection."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        identities = model.get("drawing_identities", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_title_extracted(identities))
        checks.append(self._check_type_identified(identities))
        checks.append(self._check_floor_detected(identities))
        checks.append(self._check_floor_normalized(identities))
        checks.append(self._check_drawing_ids_created(identities))
        checks.append(self._check_workspace_assigned(model))
        checks.append(self._check_registry_updated(model))
        checks.append(self._check_no_hardcoded_ground_floor(model, identities))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.1.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "identity_count": len(identities),
            },
        }

    def _check_title_extracted(self, identities: list) -> dict[str, Any]:
        missing = [
            item.get("drawing_id")
            for item in identities
            if not item.get("drawing_title")
        ]
        ok = len(identities) > 0 and len(missing) == 0
        return {
            "name": "Drawing Title Extracted",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_type_identified(self, identities: list) -> dict[str, Any]:
        invalid = [
            item.get("drawing_id")
            for item in identities
            if not item.get("drawing_type")
        ]
        ok = len(identities) > 0 and len(invalid) == 0
        return {
            "name": "Drawing Type Identified",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_floor_detected(self, identities: list) -> dict[str, Any]:
        floor_drawings = [
            item for item in identities
            if item.get("drawing_type") != DRAWING_TYPE_GENERAL_NOTES
        ]
        missing = [
            item.get("drawing_id")
            for item in floor_drawings
            if not item.get("floor_name")
        ]
        ok = len(floor_drawings) > 0 and len(missing) == 0
        return {
            "name": "Floor Detected",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_floor_normalized(self, identities: list) -> dict[str, Any]:
        invalid = []
        for item in identities:
            if item.get("drawing_type") == DRAWING_TYPE_GENERAL_NOTES:
                continue
            slug = item.get("floor_slug")
            fid = item.get("floor_id")
            if not slug or not fid or not fid.startswith("FLOOR::"):
                invalid.append(item.get("drawing_id"))
        floor_drawings = [
            item for item in identities
            if item.get("drawing_type") != DRAWING_TYPE_GENERAL_NOTES
        ]
        ok = len(floor_drawings) > 0 and len(invalid) == 0
        return {
            "name": "Floor Normalized",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_drawing_ids_created(self, identities: list) -> dict[str, Any]:
        invalid = [
            item.get("source_file")
            for item in identities
            if not item.get("drawing_id", "").startswith("DRAWING::")
        ]
        ok = len(identities) > 0 and len(invalid) == 0
        return {
            "name": "Drawing ID Created",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_workspace_assigned(self, model: dict[str, Any]) -> dict[str, Any]:
        project = model.get("project_workspace", {})
        floors = project.get("floors", [])
        framing_assigned = sum(
            1 for floor in floors
            if floor.get("framing_plan", {}).get("drawing_id")
        )
        framing_identities = [
            item for item in model.get("drawing_identities", [])
            if item.get("drawing_type") == DRAWING_TYPE_FRAMING_PLAN
        ]
        ok = framing_assigned >= len(framing_identities) and framing_assigned > 0
        return {
            "name": "Workspace Assigned",
            "status": "PASS" if ok else "FAIL",
            "framing_assigned": framing_assigned,
            "framing_expected": len(framing_identities),
        }

    def _check_registry_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        reg = model.get("drawing_registry", {})
        ok = bool(reg.get("drawings"))
        return {
            "name": "Registry Updated",
            "status": "PASS" if ok else "FAIL",
            "drawing_count": reg.get("drawing_count", 0),
        }

    def _check_no_hardcoded_ground_floor(
        self,
        model: dict[str, Any],
        identities: list,
    ) -> dict[str, Any]:
        floor_source = model.get("workspace_manager", {}).get("floor_source", "")
        framing = [
            item for item in identities
            if item.get("drawing_type") == DRAWING_TYPE_FRAMING_PLAN
        ]
        config_default_only = floor_source == "config_default"
        ground_from_config = any(
            item.get("floor_slug") == DEFAULT_FLOOR_SLUG
            and item.get("detection_source") == "FILENAME"
            for item in framing
        )
        detected_non_ground = any(
            item.get("floor_slug") != DEFAULT_FLOOR_SLUG
            for item in framing
            if item.get("drawing_type") in (DRAWING_TYPE_FRAMING_PLAN, DRAWING_TYPE_BEAM_REINFORCEMENT)
        )
        hardcoded = config_default_only or (
            ground_from_config and not detected_non_ground
        )
        ok = not hardcoded and detected_non_ground
        return {
            "name": "No Hardcoded Ground Floor",
            "status": "PASS" if ok else "FAIL",
            "floor_source": floor_source,
            "detected_floor_ids": [
                item.get("floor_id")
                for item in framing
            ],
            "expected_not": floor_id(DEFAULT_FLOOR_SLUG),
        }
