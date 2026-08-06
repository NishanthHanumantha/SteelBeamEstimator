"""Reference integrity validation — Phase H.1.1."""

from __future__ import annotations

from typing import Any, List

from src.engineering_specifications.engineering_specification import (
    engineering_specifications_applied,
)
from src.engineering_specifications.reference_contract import (
    CONTRACT_PHASE,
    assert_specification_reference_integrity,
    build_reference_contract,
)
from src.engineering_specifications.reference_interfaces import (
    build_beam_geometry_reference,
    build_coordinate_reference,
    build_geometry_reference,
    build_section_reference,
    build_support_reference,
    validate_reference_interfaces,
)
from src.engineering_specifications.specification_field_contract import (
    CALCULATED_ENGINEERING_FIELDS,
    FORBIDDEN_SPECIFICATION_EMBEDDED_FIELDS,
    GEOMETRY_OWNED_FIELDS,
    SPECIFICATION_OWNED_TOP_LEVEL_FIELDS,
    SPECIFICATION_REGISTRY_SCHEMA_KEYS,
)


class SpecificationReferenceValidator:
    """Verify reference-oriented specification architecture without changing H.1 outputs."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not engineering_specifications_applied(model) and not model.get(
            "engineering_specifications"
        ):
            return {
                "phase": CONTRACT_PHASE,
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "engineering specifications not applied"},
            }

        specifications = model.get("engineering_specifications", [])
        registry = model.get("specification_registry", {})
        contract = build_reference_contract()

        checks: List[dict[str, Any]] = []
        checks.append(self._check_no_duplicated_geometry(specifications))
        checks.append(self._check_reference_interfaces_ids_only())
        checks.append(self._check_no_calculated_values(specifications))
        checks.append(self._check_registry_schema_unchanged(registry))
        checks.append(self._check_specification_top_level_owned_fields(specifications))
        checks.append(self._check_reference_contract(contract))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": CONTRACT_PHASE,
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "specification_count": len(specifications),
            },
        }

    @staticmethod
    def _check_no_duplicated_geometry(specifications: list) -> dict[str, Any]:
        invalid = []
        for spec in specifications:
            violations = assert_specification_reference_integrity(spec)
            geometry_violations = [
                item
                for item in violations
                if any(field in item for field in GEOMETRY_OWNED_FIELDS)
            ]
            if geometry_violations:
                invalid.append(spec.get("specification_id"))
        return {
            "name": "Specification Contains No Duplicated Geometry",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_reference_interfaces_ids_only() -> dict[str, Any]:
        samples = [
            build_geometry_reference("BEAM_GEO::B1"),
            build_beam_geometry_reference(
                beam_geometry_id="BEAM_GEO::B1",
                clear_span_id="CLEAR_SPAN::B1",
                effective_span_id="EFF_SPAN::B1",
                beam_section_id="SECTION::B1",
                stationing_id="STATION::B1",
                coordinate_system_id="COORD::B1",
                support_start_id="SUPPORT::B1_START",
                support_end_id="SUPPORT::B1_END",
            ),
            build_support_reference("SUPPORT::B1_START", "FACE::B1_START"),
            build_coordinate_reference("COORD::B1", "ORIGIN::B1"),
            build_section_reference("SECTION::B1", "PROFILE::B1"),
        ]
        ok = validate_reference_interfaces(samples)
        return {
            "name": "Geometry Reference Interfaces Contain IDs Only",
            "status": "PASS" if ok else "FAIL",
            "sample_count": len(samples),
        }

    @staticmethod
    def _check_no_calculated_values(specifications: list) -> dict[str, Any]:
        invalid = []
        for spec in specifications:
            embedded = sorted(
                field_name
                for field_name in spec
                if field_name in CALCULATED_ENGINEERING_FIELDS
            )
            if embedded:
                invalid.append(
                    {
                        "specification_id": spec.get("specification_id"),
                        "fields": embedded,
                    }
                )
        return {
            "name": "No Calculated Engineering Values Stored",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_registry_schema_unchanged(registry: dict[str, Any]) -> dict[str, Any]:
        extra_keys = sorted(set(registry.keys()) - SPECIFICATION_REGISTRY_SCHEMA_KEYS)
        missing_keys = sorted(SPECIFICATION_REGISTRY_SCHEMA_KEYS - set(registry.keys()))
        ok = registry.get("phase") == "Phase H.1" and not extra_keys and not missing_keys
        return {
            "name": "Registry Schema Unchanged",
            "status": "PASS" if registry and ok else "FAIL",
            "extra_keys": extra_keys,
            "missing_keys": missing_keys,
        }

    @staticmethod
    def _check_specification_top_level_owned_fields(specifications: list) -> dict[str, Any]:
        invalid = []
        allowed = SPECIFICATION_OWNED_TOP_LEVEL_FIELDS
        forbidden = FORBIDDEN_SPECIFICATION_EMBEDDED_FIELDS
        for spec in specifications:
            unknown = sorted(set(spec.keys()) - allowed - forbidden)
            embedded_forbidden = sorted(set(spec.keys()) & forbidden)
            if unknown or embedded_forbidden:
                invalid.append(
                    {
                        "specification_id": spec.get("specification_id"),
                        "unknown_fields": unknown,
                        "forbidden_fields": embedded_forbidden,
                    }
                )
        return {
            "name": "Specification Top-Level Fields Reference-Ready",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_reference_contract(contract: dict[str, Any]) -> dict[str, Any]:
        ok = (
            contract.get("contract_version") == "H.1.1"
            and contract.get("reference_flow")
            and contract.get("reference_interface_examples")
            and contract.get("specification_owned_fields")
            and contract.get("geometry_owned_fields")
        )
        return {
            "name": "Reference Contract Valid",
            "status": "PASS" if ok else "FAIL",
        }
