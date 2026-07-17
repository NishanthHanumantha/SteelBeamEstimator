"""Validate Engineering Specifications — Phase H.1."""

from __future__ import annotations

from typing import Any, List, Set

from src.engineering_specifications.engineering_specification import (
    engineering_specifications_applied,
)
from src.engineering_specifications.specification_builder import SpecificationBuilder
from src.engineering_specifications.specification_reporting import SpecificationReporting
from src.engineering_specifications.specification_types import (
    FORBIDDEN_SPECIFICATION_FIELDS,
    VALID_SPECIFICATION_STATUSES,
    VALID_SPECIFICATION_TYPES,
)


class SpecificationValidator:
    """Verify engineering specification integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not engineering_specifications_applied(model) and not model.get(
            "engineering_specifications"
        ):
            return {
                "phase": "Phase H.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "engineering specification builder not applied"},
            }

        objects = model.get("engineering_objects", [])
        specifications = model.get("engineering_specifications", [])
        registry = model.get("specification_registry", {})
        resolved = model.get("resolved_engineering_properties", [])

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_object_processed(objects, registry))
        checks.append(self._check_unique_specification_ids(specifications))
        checks.append(self._check_registry_integrity(registry, specifications, objects))
        checks.append(self._check_traceability_preserved(specifications))
        checks.append(self._check_property_references_valid(specifications, resolved))
        checks.append(self._check_no_duplicate_specifications(specifications))
        checks.append(self._check_specification_status_valid(specifications))
        checks.append(self._check_lifecycle_summary_valid(specifications))
        checks.append(self._check_property_status_summary_valid(specifications))
        checks.append(self._check_resolution_summary_valid(specifications))
        checks.append(self._check_exports_generated(model))
        checks.append(self._check_reporting_consistency(model, specifications))
        checks.append(self._check_deterministic_ids(model))
        checks.append(self._check_specification_object_coverage(specifications, objects))
        checks.append(self._check_no_forbidden_fields(specifications))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase H.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "engineering_object_count": len(objects),
                "specification_count": len(specifications),
            },
        }

    @staticmethod
    def _check_every_object_processed(
        objects: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        object_ids = {
            str(item.get("engineering_object_id") or item.get("object_id"))
            for item in objects
        }
        processed = set(registry.get("processed_object_ids", []))
        missing = sorted(object_ids - processed)
        return {
            "name": "Every Engineering Object Processed",
            "status": "PASS" if objects and not missing else "FAIL",
            "missing": missing[:10],
            "processed_count": len(processed),
            "object_count": len(object_ids),
        }

    @staticmethod
    def _check_unique_specification_ids(specifications: list) -> dict[str, Any]:
        ids = [item.get("specification_id") for item in specifications]
        return {
            "name": "Every Specification Has Unique ID",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "count": len(ids),
        }

    @staticmethod
    def _check_registry_integrity(
        registry: dict[str, Any],
        specifications: list,
        objects: list,
    ) -> dict[str, Any]:
        ok = (
            registry.get("specification_count") == len(specifications)
            and registry.get("engineering_object_count") == len(objects)
            and registry.get("processed_object_count") == len(objects)
            and len(registry.get("specification_ids", [])) == len(specifications)
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if specifications and ok else "FAIL",
            "registry_specification_count": registry.get("specification_count"),
            "actual_specification_count": len(specifications),
        }

    @staticmethod
    def _check_traceability_preserved(specifications: list) -> dict[str, Any]:
        invalid = []
        for spec in specifications:
            trace = spec.get("traceability") or {}
            chains = trace.get("property_chains") or []
            if not trace.get("lineage") or len(chains) != len(spec.get("resolved_properties", [])):
                invalid.append(spec.get("specification_id"))
                continue
            for chain in chains:
                if not chain.get("resolved_property_id"):
                    invalid.append(spec.get("specification_id"))
                    break
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_property_references_valid(
        specifications: list,
        resolved: list,
    ) -> dict[str, Any]:
        resolved_ids = {item.get("resolved_property_id") for item in resolved}
        invalid = []
        for spec in specifications:
            for prop_id in spec.get("resolved_property_ids", []):
                if prop_id not in resolved_ids:
                    invalid.append(spec.get("specification_id"))
                    break
        return {
            "name": "Property References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_no_duplicate_specifications(specifications: list) -> dict[str, Any]:
        object_ids = [spec.get("engineering_object_id") for spec in specifications]
        duplicates = len(object_ids) - len(set(object_ids))
        return {
            "name": "No Duplicate Specifications",
            "status": "PASS" if duplicates == 0 else "FAIL",
            "duplicate_count": duplicates,
        }

    @staticmethod
    def _check_specification_status_valid(specifications: list) -> dict[str, Any]:
        invalid = [
            spec.get("specification_id")
            for spec in specifications
            if spec.get("specification_status") not in VALID_SPECIFICATION_STATUSES
        ]
        invalid_types = [
            spec.get("specification_id")
            for spec in specifications
            if spec.get("reinforcement_type") not in VALID_SPECIFICATION_TYPES
        ]
        return {
            "name": "Specification Status Valid",
            "status": "PASS" if not invalid and not invalid_types else "FAIL",
            "invalid_status": invalid[:10],
            "invalid_types": invalid_types[:10],
        }

    @staticmethod
    def _check_lifecycle_summary_valid(specifications: list) -> dict[str, Any]:
        invalid = []
        for spec in specifications:
            summary = spec.get("property_lifecycle_summary") or {}
            total = sum(int(value) for value in summary.values())
            if total != len(spec.get("resolved_properties", [])):
                invalid.append(spec.get("specification_id"))
        return {
            "name": "Lifecycle Summary Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_property_status_summary_valid(specifications: list) -> dict[str, Any]:
        invalid = []
        for spec in specifications:
            summary = spec.get("property_status_summary") or {}
            total = sum(int(value) for value in summary.values())
            if total != len(spec.get("resolved_properties", [])):
                invalid.append(spec.get("specification_id"))
        return {
            "name": "Property Status Summary Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_resolution_summary_valid(specifications: list) -> dict[str, Any]:
        invalid = []
        for spec in specifications:
            summary = spec.get("resolution_summary") or {}
            total = sum(int(value) for value in summary.values())
            if total != len(spec.get("resolved_properties", [])):
                invalid.append(spec.get("specification_id"))
        return {
            "name": "Resolution Summary Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_exports_generated(model: dict[str, Any]) -> dict[str, Any]:
        ok = bool(
            model.get("engineering_specifications") is not None
            and model.get("specification_registry")
            and model.get("specification_summary")
        )
        return {
            "name": "Export Files Created",
            "status": "PASS" if ok else "FAIL",
        }

    @staticmethod
    def _check_reporting_consistency(
        model: dict[str, Any],
        specifications: list,
    ) -> dict[str, Any]:
        summary = model.get("specification_summary", {})
        registry = model.get("specification_registry", {})
        reporting = model.get("specification_reporting") or SpecificationReporting.build(
            specifications,
            registry,
            summary,
        )
        ok = (
            summary.get("specifications_created") == len(specifications)
            and reporting.get("specification_count") == len(specifications)
            and summary.get("engineering_object_count") == registry.get("engineering_object_count")
            and summary.get("specifications_created") == registry.get("specification_count")
        )
        return {
            "name": "Reporting Consistency",
            "status": "PASS" if summary and ok else "FAIL",
            "summary_count": summary.get("specifications_created"),
            "actual_count": len(specifications),
        }

    @staticmethod
    def _check_deterministic_ids(model: dict[str, Any]) -> dict[str, Any]:
        builder = SpecificationBuilder()
        first_specs, _ = builder.build(
            model.get("engineering_objects", []),
            model.get("resolved_engineering_properties", []),
            model.get("engineering_properties", []),
            model.get("property_candidates", []),
            model.get("engineering_reinforcement_contexts", []),
            model.get("semantic_roles", []),
        )
        second_specs, _ = builder.build(
            model.get("engineering_objects", []),
            model.get("resolved_engineering_properties", []),
            model.get("engineering_properties", []),
            model.get("property_candidates", []),
            model.get("engineering_reinforcement_contexts", []),
            model.get("semantic_roles", []),
        )
        first_ids = [item.get("specification_id") for item in first_specs]
        second_ids = [item.get("specification_id") for item in second_specs]
        return {
            "name": "IDs Deterministic",
            "status": "PASS" if first_ids == second_ids else "FAIL",
            "first_count": len(first_ids),
            "second_count": len(second_ids),
        }

    @staticmethod
    def _check_specification_object_coverage(
        specifications: list,
        objects: list,
    ) -> dict[str, Any]:
        object_ids: Set[str] = {
            str(item.get("engineering_object_id") or item.get("object_id")) for item in objects
        }
        invalid = [
            spec.get("specification_id")
            for spec in specifications
            if spec.get("engineering_object_id") not in object_ids
        ]
        return {
            "name": "Specification Object Coverage",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_no_forbidden_fields(specifications: list) -> dict[str, Any]:
        invalid = [
            spec.get("specification_id")
            for spec in specifications
            if any(field in spec for field in FORBIDDEN_SPECIFICATION_FIELDS)
        ]
        return {
            "name": "No Forbidden Specification Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }
