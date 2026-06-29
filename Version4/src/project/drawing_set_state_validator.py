"""Validate drawing set lifecycle, beam index, and versioning."""

from __future__ import annotations

from typing import Any, List

from src.project.beam_index_builder import BeamIndexBuilder
from src.project.drawing_set_state_machine import is_valid_lifecycle, LIFECYCLE_FIELD_MAP


class DrawingSetStateValidator:
    """Verify G.1.3 drawing set state, index, and version enrichment."""

    def validate(
        self,
        model: dict[str, Any],
        drawing_sets: List[dict[str, Any]],
    ) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.append(self._check_lifecycle_exists(drawing_sets))
        checks.append(self._check_lifecycle_values(drawing_sets))
        checks.append(self._check_beam_index_exists(drawing_sets))
        checks.append(self._check_beam_count_matches(model, drawing_sets))
        checks.append(self._check_unique_beam_marks(model, drawing_sets))
        checks.append(self._check_beam_lookup(model, drawing_sets))
        checks.append(self._check_version_exists(drawing_sets))
        checks.append(self._check_version_hash(drawing_sets))
        checks.append(self._check_created_from(drawing_sets))
        checks.append(self._check_future_placeholders(drawing_sets))
        checks.append(self._check_graph_updated(model))
        checks.append(self._check_backward_compatibility(drawing_sets))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.1.3",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "drawing_set_count": len(drawing_sets),
            },
        }

    def _check_lifecycle_exists(self, drawing_sets: list) -> dict[str, Any]:
        missing = [
            ds.get("drawing_set_id")
            for ds in drawing_sets
            if not all(field in ds for field in LIFECYCLE_FIELD_MAP)
        ]
        ok = len(drawing_sets) > 0 and len(missing) == 0
        return {
            "name": "Lifecycle Exists",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_lifecycle_values(self, drawing_sets: list) -> dict[str, Any]:
        invalid = []
        for ds in drawing_sets:
            lifecycle = {k: ds.get(k) for k in LIFECYCLE_FIELD_MAP}
            if not is_valid_lifecycle(lifecycle):
                invalid.append(ds.get("drawing_set_id"))
        ok = len(invalid) == 0
        return {
            "name": "Lifecycle Values Valid",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_beam_index_exists(self, drawing_sets: list) -> dict[str, Any]:
        missing = [
            ds.get("drawing_set_id")
            for ds in drawing_sets
            if not ds.get("beam_index")
        ]
        ok = len(drawing_sets) > 0 and len(missing) == 0
        return {
            "name": "Beam Index Exists",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_beam_count_matches(
        self,
        model: dict[str, Any],
        drawing_sets: list,
    ) -> dict[str, Any]:
        mismatched = []
        for ds in drawing_sets:
            ds_id = ds.get("drawing_set_id")
            indexed = len(ds.get("beam_index", {}))
            context_count = sum(
                1 for c in model.get("beam_engineering_contexts", [])
                if c.get("drawing_set_id") == ds_id
            )
            if indexed != context_count:
                mismatched.append({
                    "drawing_set_id": ds_id,
                    "indexed": indexed,
                    "contexts": context_count,
                })
        ok = len(mismatched) == 0
        return {
            "name": "Beam Count Matches Contexts",
            "status": "PASS" if ok else "FAIL",
            "mismatched": mismatched,
        }

    def _check_unique_beam_marks(
        self,
        model: dict[str, Any],
        drawing_sets: list,
    ) -> dict[str, Any]:
        duplicates = []
        builder = BeamIndexBuilder()
        for ds in drawing_sets:
            try:
                builder.build(ds.get("drawing_set_id", ""), model.get("beam_engineering_contexts", []))
            except ValueError as exc:
                duplicates.append(str(exc))
        ok = len(duplicates) == 0
        return {
            "name": "Unique Beam Marks",
            "status": "PASS" if ok else "FAIL",
            "errors": duplicates,
        }

    def _check_beam_lookup(
        self,
        model: dict[str, Any],
        drawing_sets: list,
    ) -> dict[str, Any]:
        builder = BeamIndexBuilder()
        contexts = model.get("beam_engineering_contexts", [])
        failed = []
        for ds in drawing_sets:
            ds_id = ds.get("drawing_set_id", "")
            try:
                api = builder.build(ds_id, contexts)
            except ValueError:
                failed.append(ds_id)
                continue
            marks = ds.get("beam_index_meta", {}).get("marks", [])
            for mark in marks[:3]:
                if not api.contains(mark) or not api.get_context_id(mark):
                    failed.append(f"{ds_id}:{mark}")
        ok = len(drawing_sets) > 0 and len(failed) == 0
        return {
            "name": "Beam Lookup Operational",
            "status": "PASS" if ok else "FAIL",
            "failed": failed,
        }

    def _check_version_exists(self, drawing_sets: list) -> dict[str, Any]:
        missing = [
            ds.get("drawing_set_id")
            for ds in drawing_sets
            if not ds.get("drawing_set_version")
        ]
        ok = len(missing) == 0
        return {
            "name": "Version Object Exists",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_version_hash(self, drawing_sets: list) -> dict[str, Any]:
        missing = [
            ds.get("drawing_set_id")
            for ds in drawing_sets
            if not ds.get("drawing_set_version", {}).get("version_hash")
        ]
        ok = len(missing) == 0
        return {
            "name": "Version Hash Generated",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_created_from(self, drawing_sets: list) -> dict[str, Any]:
        incomplete = [
            ds.get("drawing_set_id")
            for ds in drawing_sets
            if len(ds.get("drawing_set_version", {}).get("created_from", [])) < 2
        ]
        ok = len(incomplete) == 0
        return {
            "name": "Created From Complete",
            "status": "PASS" if ok else "FAIL",
            "incomplete": incomplete,
        }

    def _check_future_placeholders(self, drawing_sets: list) -> dict[str, Any]:
        missing = [
            ds.get("drawing_set_id")
            for ds in drawing_sets
            if "beam_matching_context" not in ds
            or "reinforcement_contexts" not in ds
            or "engineering_results" not in ds
        ]
        ok = len(missing) == 0
        return {
            "name": "Future Placeholders Exist",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_graph_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        nodes = graph.get("nodes", [])
        has_version = any(n.get("type") == "DRAWING_SET_VERSION" for n in nodes)
        has_index = any(n.get("type") == "BEAM_INDEX" for n in nodes)
        ok = has_version and has_index
        return {
            "name": "Project Graph Updated",
            "status": "PASS" if ok else "FAIL",
            "version_nodes": sum(1 for n in nodes if n.get("type") == "DRAWING_SET_VERSION"),
            "index_nodes": sum(1 for n in nodes if n.get("type") == "BEAM_INDEX"),
        }

    def _check_backward_compatibility(self, drawing_sets: list) -> dict[str, Any]:
        missing_status = [ds.get("drawing_set_id") for ds in drawing_sets if not ds.get("status")]
        ok = len(missing_status) == 0
        return {
            "name": "Backward Compatibility Maintained",
            "status": "PASS" if ok else "FAIL",
            "missing_status": missing_status,
        }
