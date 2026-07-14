"""Validate parsed Engineering Properties — Phase G.5.3.1."""

from __future__ import annotations

from typing import Any, List, Set

from src.property_parser.engineering_property import property_parser_applied
from src.property_parser.property_parser_types import (
    PARSE_STATUS_PARSED,
    PARSER_NAME_TEXT,
    PARSER_VERSION,
    UNIT_COUNT,
    UNIT_MILLIMETRE,
    VALID_PARSE_STATUSES,
    VALID_PROPERTY_TYPES,
)


class PropertyParserValidator:
    """Verify property parser integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not property_parser_applied(model) and not model.get("engineering_properties"):
            return {
                "phase": "Phase G.5.3.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "property parser not applied"},
            }

        candidates = model.get("property_candidates", [])
        properties = model.get("engineering_properties", [])
        if not properties:
            properties = model.get("property_parser_registry", {}).get("properties", [])

        registry = model.get("property_parser_registry", {})
        checks: List[dict[str, Any]] = []
        checks.append(self._check_candidate_coverage(candidates, properties))
        checks.append(self._check_property_references_candidate(properties, candidates))
        checks.append(self._check_candidate_references_object(properties, candidates))
        checks.append(self._check_units_normalized(properties))
        checks.append(self._check_parsed_values_valid(properties))
        checks.append(self._check_unique_property_ids(properties))
        checks.append(self._check_parser_metadata(properties))
        checks.append(self._check_source_trace(properties, candidates))
        checks.append(self._check_registry_valid(registry, candidates, properties))
        checks.append(self._check_exports_generated(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.5.3.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "property_count": len(properties),
                "candidates_processed": len(candidates),
            },
        }

    @staticmethod
    def _check_candidate_coverage(
        candidates: list,
        properties: list,
    ) -> dict[str, Any]:
        candidate_ids = {c.get("candidate_id") for c in candidates}
        referenced = {p.get("candidate_id") for p in properties}
        missing = sorted(candidate_ids - referenced)
        return {
            "name": "Candidate Coverage",
            "status": "PASS" if candidates and not missing else "FAIL",
            "missing": missing[:10],
            "processed": len(candidate_ids) - len(missing),
            "total": len(candidate_ids),
        }

    @staticmethod
    def _check_property_references_candidate(
        properties: list,
        candidates: list,
    ) -> dict[str, Any]:
        candidate_ids = {c.get("candidate_id") for c in candidates}
        invalid = [
            p.get("property_id")
            for p in properties
            if p.get("candidate_id") not in candidate_ids
        ]
        return {
            "name": "Property Coverage",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_candidate_references_object(
        properties: list,
        candidates: list,
    ) -> dict[str, Any]:
        candidate_objects = {c.get("candidate_id"): c.get("engineering_object_id") for c in candidates}
        invalid = [
            p.get("property_id")
            for p in properties
            if candidate_objects.get(p.get("candidate_id")) != p.get("engineering_object_id")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_units_normalized(properties: list) -> dict[str, Any]:
        invalid = []
        for prop in properties:
            if prop.get("parse_status") != PARSE_STATUS_PARSED:
                continue
            ptype = prop.get("property_type")
            unit = prop.get("unit", "")
            if ptype == "DIAMETER" and unit != UNIT_MILLIMETRE:
                invalid.append(prop.get("property_id"))
            elif ptype == "SPACING" and unit != UNIT_MILLIMETRE:
                invalid.append(prop.get("property_id"))
            elif ptype == "QUANTITY" and unit != UNIT_COUNT:
                invalid.append(prop.get("property_id"))
        return {
            "name": "Units Normalized",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_parsed_values_valid(properties: list) -> dict[str, Any]:
        invalid = []
        for prop in properties:
            if prop.get("parse_status") != PARSE_STATUS_PARSED:
                continue
            if prop.get("parsed_value") is None and prop.get("normalized_value") is None:
                invalid.append(prop.get("property_id"))
            if prop.get("property_type") not in VALID_PROPERTY_TYPES:
                invalid.append(prop.get("property_id"))
        return {
            "name": "Parsed Values Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_unique_property_ids(properties: list) -> dict[str, Any]:
        ids = [p.get("property_id") for p in properties]
        return {
            "name": "Unique IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "count": len(ids),
        }

    @staticmethod
    def _check_parser_metadata(properties: list) -> dict[str, Any]:
        invalid = [
            p.get("property_id")
            for p in properties
            if p.get("parser_name") != PARSER_NAME_TEXT
            or p.get("parser_version") != PARSER_VERSION
        ]
        return {
            "name": "Parser Metadata Assigned",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_source_trace(properties: list, candidates: list) -> dict[str, Any]:
        candidate_map = {c.get("candidate_id"): c for c in candidates}
        invalid = []
        for prop in properties:
            cand = candidate_map.get(prop.get("candidate_id"), {})
            if prop.get("source_entity_id") != cand.get("source_entity_id"):
                invalid.append(prop.get("property_id"))
            if not prop.get("source_role_id") and cand.get("source_role_id"):
                invalid.append(prop.get("property_id"))
            if prop.get("parse_status") not in VALID_PARSE_STATUSES:
                invalid.append(prop.get("property_id"))
        return {
            "name": "Source Trace Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_registry_valid(
        registry: dict[str, Any],
        candidates: list,
        properties: list,
    ) -> dict[str, Any]:
        ok = (
            registry.get("property_count") == len(properties)
            and registry.get("candidate_count") == len(candidates)
            and registry.get("candidates_processed") == len(candidates)
        )
        return {
            "name": "Property Registry Valid",
            "status": "PASS" if candidates and ok else "FAIL",
            "registry_property_count": registry.get("property_count"),
            "actual_property_count": len(properties),
        }

    @staticmethod
    def _check_exports_generated(model: dict[str, Any]) -> dict[str, Any]:
        ok = bool(
            model.get("engineering_properties") is not None
            and model.get("property_parser_registry")
            and model.get("property_parser_summary")
            and model.get("unparsed_candidates") is not None
        )
        return {
            "name": "Export Generated",
            "status": "PASS" if ok else "FAIL",
        }
