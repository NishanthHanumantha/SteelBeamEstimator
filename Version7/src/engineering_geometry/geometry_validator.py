"""Validate geometry associations — Phase H.2."""

from __future__ import annotations

from typing import Any, List, Set

from src.engineering_geometry.geometry_association import geometry_associations_applied
from src.engineering_geometry.geometry_association_builder import GeometryAssociationBuilder
from src.engineering_geometry.geometry_reporting import GeometryAssociationReporting
from src.engineering_geometry.geometry_types import (
    ASSOCIATION_REFERENCE_FIELDS,
    GEOMETRY_OWNED_VALUE_KEYS,
    REGISTRY_SCHEMA_KEYS,
    VALID_ASSOCIATION_STATUSES,
)
from src.engineering_geometry.phase_f_registry_index import PhaseFRegistryIndex
from src.engineering_specifications.reference_contract import CONTRACT_VERSION
from src.engineering_specifications.specification_field_contract import (
    GEOMETRY_OWNED_FIELDS,
)


class GeometryAssociationValidator:
    """Verify geometry association integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not geometry_associations_applied(model) and not model.get("geometry_associations"):
            return {
                "phase": "Phase H.2",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "geometry association not applied"},
            }

        specifications = model.get("engineering_specifications", [])
        associations = model.get("geometry_associations", [])
        registry = model.get("geometry_registry", {})
        index = PhaseFRegistryIndex(model)

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_specification_evaluated(specifications, registry))
        checks.append(self._check_unique_associations(associations))
        checks.append(self._check_registry_integrity(registry, associations, specifications))
        checks.append(self._check_beam_references_valid(associations, index))
        checks.append(self._check_geometry_references_valid(associations, index))
        checks.append(self._check_section_references_valid(associations, index))
        checks.append(self._check_span_references_valid(associations, index))
        checks.append(self._check_support_references_valid(associations))
        checks.append(self._check_coordinate_references_valid(associations, index))
        checks.append(self._check_knowledge_graph_references_valid(associations, index))
        checks.append(self._check_reference_contract_honored(associations))
        checks.append(self._check_no_duplicated_geometry_values(associations))
        checks.append(self._check_traceability_preserved(associations))
        checks.append(self._check_export_consistency(model, associations))
        checks.append(self._check_deterministic_ids(model))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase H.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "specification_count": len(specifications),
                "association_count": len(associations),
            },
        }

    @staticmethod
    def _check_every_specification_evaluated(
        specifications: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        spec_ids = {item.get("specification_id") for item in specifications}
        processed = set(registry.get("processed_specification_ids", []))
        missing = sorted(spec_ids - processed)
        return {
            "name": "Every Specification Evaluated",
            "status": "PASS" if specifications and not missing else "FAIL",
            "missing": missing[:10],
            "processed_count": len(processed),
            "specification_count": len(spec_ids),
        }

    @staticmethod
    def _check_unique_associations(associations: list) -> dict[str, Any]:
        ids = [item.get("association_id") for item in associations]
        spec_ids = [item.get("specification_id") for item in associations]
        return {
            "name": "Every Association Unique",
            "status": "PASS"
            if len(ids) == len(set(ids)) and len(spec_ids) == len(set(spec_ids))
            else "FAIL",
            "association_count": len(ids),
        }

    @staticmethod
    def _check_registry_integrity(
        registry: dict[str, Any],
        associations: list,
        specifications: list,
    ) -> dict[str, Any]:
        ok = (
            registry.get("association_count") == len(associations)
            and registry.get("specification_count") == len(specifications)
            and len(registry.get("processed_specification_ids", [])) == len(specifications)
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if associations and ok else "FAIL",
            "registry_association_count": registry.get("association_count"),
            "actual_association_count": len(associations),
        }

    @staticmethod
    def _check_beam_references_valid(associations: list, index: PhaseFRegistryIndex) -> dict[str, Any]:
        invalid = [
            item.get("association_id")
            for item in associations
            if item.get("beam_id")
            and not index.validate_reference(
                str(item.get("beam_geometry_id", "")),
                "beam_geometry",
                str(item.get("beam_id", "")),
            )
            and item.get("association_status") not in {"MISSING_BEAM", "MISSING_GEOMETRY"}
        ]
        return {
            "name": "Beam References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_geometry_references_valid(
        associations: list,
        index: PhaseFRegistryIndex,
    ) -> dict[str, Any]:
        invalid = [
            item.get("association_id")
            for item in associations
            if item.get("association_status") == "VALID"
            and not index.has_beam_mark(str(item.get("beam_id", "")))
        ]
        return {
            "name": "Geometry References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_section_references_valid(
        associations: list,
        index: PhaseFRegistryIndex,
    ) -> dict[str, Any]:
        invalid = []
        for item in associations:
            if item.get("association_status") != "VALID":
                continue
            beam_mark = str(item.get("beam_id", ""))
            if not index.validate_reference(
                str(item.get("beam_section_id", "")),
                "section",
                beam_mark,
            ):
                invalid.append(item.get("association_id"))
        return {
            "name": "Section References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_span_references_valid(
        associations: list,
        index: PhaseFRegistryIndex,
    ) -> dict[str, Any]:
        invalid = []
        for item in associations:
            if item.get("association_status") != "VALID":
                continue
            beam_mark = str(item.get("beam_id", ""))
            if not index.validate_reference(
                str(item.get("clear_span_id", "")),
                "clear_span",
                beam_mark,
            ) or not index.validate_reference(
                str(item.get("effective_span_id", "")),
                "effective_span",
                beam_mark,
            ):
                invalid.append(item.get("association_id"))
        return {
            "name": "Span References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_support_references_valid(associations: list) -> dict[str, Any]:
        invalid = [
            item.get("association_id")
            for item in associations
            if item.get("association_status") == "VALID"
            and (not item.get("support_start_id") or not item.get("support_end_id"))
        ]
        return {
            "name": "Support References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_coordinate_references_valid(
        associations: list,
        index: PhaseFRegistryIndex,
    ) -> dict[str, Any]:
        invalid = []
        for item in associations:
            if item.get("association_status") != "VALID":
                continue
            beam_mark = str(item.get("beam_id", ""))
            if not index.validate_reference(
                str(item.get("coordinate_system_id", "")),
                "coordinate_system",
                beam_mark,
            ):
                invalid.append(item.get("association_id"))
        return {
            "name": "Coordinate References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_knowledge_graph_references_valid(
        associations: list,
        index: PhaseFRegistryIndex,
    ) -> dict[str, Any]:
        invalid = []
        for item in associations:
            if item.get("association_status") != "VALID":
                continue
            if not index.validate_reference(
                str(item.get("knowledge_graph_node_id", "")),
                "knowledge_graph",
                str(item.get("beam_id", "")),
            ):
                invalid.append(item.get("association_id"))
        return {
            "name": "Knowledge Graph References Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_reference_contract_honored(associations: list) -> dict[str, Any]:
        invalid = [
            item.get("association_id")
            for item in associations
            if item.get("reference_contract_version") != CONTRACT_VERSION
        ]
        embedded_geometry = [
            item.get("association_id")
            for item in associations
            for field in item
            if field in GEOMETRY_OWNED_FIELDS
        ]
        return {
            "name": "Reference Contract Honored",
            "status": "PASS" if not invalid and not embedded_geometry else "FAIL",
            "invalid_contract": invalid[:10],
            "embedded_geometry_fields": embedded_geometry[:10],
        }

    @staticmethod
    def _check_no_duplicated_geometry_values(associations: list) -> dict[str, Any]:
        invalid = []
        for item in associations:
            for field, value in item.items():
                if field in GEOMETRY_OWNED_VALUE_KEYS:
                    invalid.append(item.get("association_id"))
                    break
                if isinstance(value, dict):
                    if any(key in GEOMETRY_OWNED_VALUE_KEYS for key in value):
                        invalid.append(item.get("association_id"))
                        break
                if isinstance(value, (int, float)) and field in ASSOCIATION_REFERENCE_FIELDS:
                    invalid.append(item.get("association_id"))
                    break
        return {
            "name": "No Duplicated Geometry Values",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_traceability_preserved(associations: list) -> dict[str, Any]:
        invalid = []
        for item in associations:
            trace = item.get("traceability") or {}
            if not trace.get("lineage") or not trace.get("specification_id"):
                invalid.append(item.get("association_id"))
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_export_consistency(model: dict[str, Any], associations: list) -> dict[str, Any]:
        summary = model.get("geometry_summary", {})
        reporting = model.get("geometry_reporting") or GeometryAssociationReporting.build(
            associations,
            model.get("geometry_registry", {}),
            summary,
        )
        ok = (
            summary.get("associations_created") == len(associations)
            and reporting.get("association_count") == len(associations)
        )
        return {
            "name": "Export Consistency",
            "status": "PASS" if summary and ok else "FAIL",
            "summary_count": summary.get("associations_created"),
            "actual_count": len(associations),
        }

    @staticmethod
    def _check_deterministic_ids(model: dict[str, Any]) -> dict[str, Any]:
        builder = GeometryAssociationBuilder()
        first, _ = builder.build(
            model.get("engineering_specifications", []),
            model,
        )
        second, _ = builder.build(
            model.get("engineering_specifications", []),
            model,
        )
        first_ids = [item.get("association_id") for item in first]
        second_ids = [item.get("association_id") for item in second]
        return {
            "name": "Deterministic IDs",
            "status": "PASS" if first_ids == second_ids else "FAIL",
            "first_count": len(first_ids),
            "second_count": len(second_ids),
        }

    @staticmethod
    def _check_association_status_valid(associations: list) -> dict[str, Any]:
        invalid = [
            item.get("association_id")
            for item in associations
            if item.get("association_status") not in VALID_ASSOCIATION_STATUSES
        ]
        return {
            "name": "Association Status Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }
