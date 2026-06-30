"""Validate Phase G.2.4 engineering detail identity and fingerprinting."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.detail_identity import MATCHING_STATUS_NOT_MATCHED
from src.reinforcement.reinforcement_geometry_entity import ENGINEERING_STATUS_GEOMETRY_ONLY


class DetailIdentityValidator:
    """Verify detail identity layer without beam matching or ownership."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        drawing_models = model.get("reinforcement_drawing_models", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_identities_created(drawing_models))
        checks.append(self._check_every_context_has_identity(drawing_models))
        checks.append(self._check_every_identity_has_fingerprint(drawing_models))
        checks.append(self._check_identity_ids_unique(drawing_models))
        checks.append(self._check_fingerprint_ids_unique(drawing_models))
        checks.append(self._check_fingerprints_deterministic(model, drawing_models))
        checks.append(self._check_overall_hash_unique(drawing_models))
        checks.append(self._check_matching_status_initialized(drawing_models))
        checks.append(self._check_engineering_owner_null(drawing_models))
        checks.append(self._check_engineering_status_geometry_only(drawing_models))
        checks.append(self._check_no_beam_context_references(model, drawing_models))
        checks.append(self._check_no_ownership(drawing_models))
        checks.append(self._check_no_parsing(drawing_models))
        checks.append(self._check_no_quantities(model))
        checks.append(self._check_no_engineering_computation(model))
        checks.append(self._check_no_duplicated_fingerprints(drawing_models))
        checks.append(self._check_graph_relationships(model))
        checks.append(self._check_identity_registry_complete(model, drawing_models))
        checks.append(self._check_fingerprint_registry_complete(model, drawing_models))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.2.4",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "detail_identity_count": sum(
                    dm.get("detail_identity_count", 0) for dm in drawing_models
                ),
                "fingerprint_count": sum(
                    dm.get("detail_fingerprint_count", 0) for dm in drawing_models
                ),
            },
        }

    def _check_identities_created(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("detail_identity_count", 0) for dm in drawing_models)
        return {
            "name": "DetailIdentities Created",
            "status": "PASS" if count > 0 else "FAIL",
            "count": count,
        }

    def _check_every_context_has_identity(self, drawing_models: list) -> dict[str, Any]:
        missing = []
        for dm in drawing_models:
            for ctx in dm.get("detail_contexts", []):
                if not ctx.get("detail_identity_id"):
                    missing.append(ctx.get("detail_context_id"))
        return {
            "name": "Every DetailContext Has DetailIdentity",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    def _check_every_identity_has_fingerprint(self, drawing_models: list) -> dict[str, Any]:
        missing = []
        fp_by_identity = {}
        for dm in drawing_models:
            for fp in dm.get("detail_fingerprints", []):
                fp_by_identity[fp.get("detail_identity_id")] = fp
            for ident in dm.get("detail_identities", []):
                iid = ident.get("detail_identity_id")
                if iid not in fp_by_identity:
                    missing.append(iid)
        return {
            "name": "Every DetailIdentity Has Fingerprint",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    def _check_identity_ids_unique(self, drawing_models: list) -> dict[str, Any]:
        ids: list[str] = []
        for dm in drawing_models:
            for item in dm.get("detail_identities", []):
                ids.append(str(item.get("detail_identity_id", "")))
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        return {
            "name": "DetailIdentity IDs Unique",
            "status": "PASS" if ids and not duplicates else "FAIL",
            "duplicates": duplicates,
        }

    def _check_fingerprint_ids_unique(self, drawing_models: list) -> dict[str, Any]:
        ids: list[str] = []
        for dm in drawing_models:
            for item in dm.get("detail_fingerprints", []):
                ids.append(str(item.get("fingerprint_id", "")))
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        return {
            "name": "Fingerprint IDs Unique",
            "status": "PASS" if ids and not duplicates else "FAIL",
            "duplicates": duplicates,
        }

    def _check_fingerprints_deterministic(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        from src.reinforcement.detail_fingerprint_builder import DetailFingerprintBuilder

        invalid = []
        for dm in drawing_models:
            rebuilt = DetailFingerprintBuilder().build(
                dm.get("detail_identities", []),
                dm.get("detail_contexts", []),
                dm.get("regions", []),
                dm.get("detail_views", []),
            )
            rebuilt_by_id = {fp["detail_identity_id"]: fp for fp in rebuilt}
            for fp in dm.get("detail_fingerprints", []):
                iid = fp.get("detail_identity_id")
                expected = rebuilt_by_id.get(iid)
                if not expected or expected.get("overall_hash") != fp.get("overall_hash"):
                    invalid.append(iid)
        return {
            "name": "Fingerprints Deterministic",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_overall_hash_unique(self, drawing_models: list) -> dict[str, Any]:
        hashes: list[str] = []
        for dm in drawing_models:
            for fp in dm.get("detail_fingerprints", []):
                hashes.append(str(fp.get("overall_hash", "")))
        duplicates = sorted({h for h in hashes if hashes.count(h) > 1})
        return {
            "name": "Overall Hash Unique",
            "status": "PASS" if hashes and not duplicates else "FAIL",
            "duplicates": duplicates,
        }

    def _check_matching_status_initialized(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if ident.get("matching_status") != MATCHING_STATUS_NOT_MATCHED:
                    invalid.append(ident.get("detail_identity_id"))
        return {
            "name": "Matching Status Initialized NOT_MATCHED",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_engineering_owner_null(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if ident.get("engineering_owner") is not None:
                    invalid.append(ident.get("detail_identity_id"))
        return {
            "name": "Engineering Owner NULL",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_engineering_status_geometry_only(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if ident.get("engineering_status") != ENGINEERING_STATUS_GEOMETRY_ONLY:
                    invalid.append(ident.get("detail_identity_id"))
        return {
            "name": "Engineering Status GEOMETRY_ONLY",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_beam_context_references(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if ident.get("beam_context_id") or ident.get("matched_beam_id"):
                    invalid.append(ident.get("detail_identity_id"))
        for ctx in model.get("beam_engineering_contexts", []):
            if ctx.get("detail_identity_id"):
                invalid.append(ctx.get("beam_context_id", "beam_context"))
        return {
            "name": "No BeamContext References",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_ownership(self, drawing_models: list) -> dict[str, Any]:
        for dm in drawing_models:
            for rel in dm.get("detail_identity_relationships", []):
                if "OWN" in str(rel.get("relationship", "")).upper():
                    return {"name": "No Ownership", "status": "FAIL"}
        return {"name": "No Ownership", "status": "PASS"}

    def _check_no_parsing(self, drawing_models: list) -> dict[str, Any]:
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if "parsed" in ident or "engineering_type" in ident:
                    return {"name": "No Parsing", "status": "FAIL"}
        return {"name": "No Parsing", "status": "PASS"}

    def _check_no_quantities(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("quantities", "steel_weight", "boq") if k in model]
        return {
            "name": "No Quantities",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_engineering_computation(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("engineering_objects", "parsed_bars") if k in model]
        return {
            "name": "No Engineering Computation",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_duplicated_fingerprints(self, drawing_models: list) -> dict[str, Any]:
        seen: dict[str, str] = {}
        duplicates = []
        for dm in drawing_models:
            for fp in dm.get("detail_fingerprints", []):
                oh = fp.get("overall_hash", "")
                fid = fp.get("fingerprint_id", "")
                if oh in seen and seen[oh] != fid:
                    duplicates.append(oh)
                seen[oh] = fid
        return {
            "name": "No Duplicated Fingerprints",
            "status": "PASS" if not duplicates else "FAIL",
            "duplicates": duplicates,
        }

    def _check_graph_relationships(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        detail_nodes = [n for n in graph.get("nodes", []) if n.get("type") == "DETAIL"]
        fp_nodes = [n for n in graph.get("nodes", []) if n.get("type") == "FINGERPRINT"]
        has_detail_edge = any(
            e.get("relationship") == "HAS_DETAIL" for e in graph.get("edges", [])
        )
        has_fp_edge = any(
            e.get("relationship") == "HAS_FINGERPRINT" for e in graph.get("edges", [])
        )
        ok = len(detail_nodes) > 0 and len(fp_nodes) > 0 and has_detail_edge and has_fp_edge
        return {
            "name": "Graph Identity Relationships Valid",
            "status": "PASS" if ok else "FAIL",
            "detail_nodes": len(detail_nodes),
            "fingerprint_nodes": len(fp_nodes),
            "has_detail_edge": has_detail_edge,
            "has_fingerprint_edge": has_fp_edge,
        }

    def _check_identity_registry_complete(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        registry = model.get("detail_identity_registry", {})
        expected = sum(dm.get("detail_identity_count", 0) for dm in drawing_models)
        actual = registry.get("detail_identity_count", 0)
        return {
            "name": "DetailIdentity Registry Complete",
            "status": "PASS" if expected > 0 and actual == expected else "FAIL",
            "expected": expected,
            "actual": actual,
        }

    def _check_fingerprint_registry_complete(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        registry = model.get("detail_fingerprint_registry", {})
        expected = sum(dm.get("detail_fingerprint_count", 0) for dm in drawing_models)
        actual = registry.get("fingerprint_count", 0)
        return {
            "name": "Fingerprint Registry Complete",
            "status": "PASS" if expected > 0 and actual == expected else "FAIL",
            "expected": expected,
            "actual": actual,
        }
