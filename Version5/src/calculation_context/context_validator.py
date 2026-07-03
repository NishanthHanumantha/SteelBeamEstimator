"""Validate engineering calculation contexts — Phase I.1."""

from __future__ import annotations

from typing import Any, List, Set

from src.calculation_context.calculation_context_types import (
    MATERIAL_FIELDS,
    REFERENCE_FIELDS,
    REGISTRY_SCHEMA_KEYS,
    SCALAR_GEOMETRY_FIELDS,
    STATUS_COMPLETE,
    VALID_CALCULATION_STATUSES,
)
from src.calculation_context.context_models import calculation_contexts_applied
from src.calculation_context.context_registry import CalculationContextRegistry
from src.engineering_geometry.geometry_types import STATUS_VALID
from src.engineering_geometry.phase_f_registry_index import PhaseFRegistryIndex
from src.framing.engineering_ids import RULE_ESTIMATOR, RULE_PROJECT


class CalculationContextValidator:
    """Verify calculation context integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not calculation_contexts_applied(model) and not model.get("calculation_contexts"):
            return {
                "phase": "Phase I.1",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "calculation context not applied"},
            }

        specifications = model.get("engineering_specifications", [])
        associations = model.get("geometry_associations", [])
        contexts = model.get("calculation_contexts", [])
        registry = model.get("calculation_context_registry", {})
        index = PhaseFRegistryIndex(model)

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_specification_has_context(specifications, registry))
        checks.append(self._check_every_association_has_context(associations, contexts))
        checks.append(self._check_unique_contexts(contexts))
        checks.append(self._check_registry_integrity(registry, contexts, specifications))
        checks.append(self._check_geometry_resolved(contexts, associations))
        checks.append(self._check_beam_dimensions_available(contexts))
        checks.append(self._check_spans_available(contexts))
        checks.append(self._check_concrete_grade_available(contexts))
        checks.append(self._check_steel_grade_available(contexts))
        checks.append(self._check_cover_resolved(contexts))
        checks.append(self._check_estimator_rules_loaded(contexts))
        checks.append(self._check_general_notes_referenced(contexts))
        checks.append(self._check_references_preserved(contexts, associations))
        checks.append(self._check_deterministic_ids(contexts))
        checks.append(self._check_registry_lookup_integrity(contexts, registry))
        checks.append(self._check_no_duplicated_geometry_objects(contexts))
        checks.append(self._check_no_duplicated_rule_tables(contexts))
        checks.append(self._check_traceability_preserved(contexts))
        checks.append(self._check_export_consistency(model, contexts))
        checks.append(self._check_immutable_structure(contexts))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.1",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "specification_count": len(specifications),
                "context_count": len(contexts),
            },
        }

    @staticmethod
    def _check_every_specification_has_context(
        specifications: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        spec_ids = {item.get("specification_id") for item in specifications}
        processed = set(registry.get("processed_specification_ids", []))
        missing = sorted(spec_ids - processed)
        return {
            "name": "Every Specification Has Context",
            "status": "PASS" if specifications and not missing else "FAIL",
            "missing": missing[:10],
            "processed_count": len(processed),
            "specification_count": len(spec_ids),
        }

    @staticmethod
    def _check_every_association_has_context(
        associations: list,
        contexts: list,
    ) -> dict[str, Any]:
        assoc_ids = {item.get("association_id") for item in associations if item.get("association_id")}
        context_assoc_ids = {
            item.get("association_id") for item in contexts if item.get("association_id")
        }
        missing = sorted(assoc_ids - context_assoc_ids)
        return {
            "name": "Every Association Has Context",
            "status": "PASS" if associations and not missing else "FAIL",
            "missing": missing[:10],
            "association_count": len(assoc_ids),
        }

    @staticmethod
    def _check_unique_contexts(contexts: list) -> dict[str, Any]:
        ids = [item.get("context_id") for item in contexts]
        spec_ids = [item.get("specification_id") for item in contexts]
        return {
            "name": "Every Context Unique",
            "status": "PASS"
            if len(ids) == len(set(ids)) and len(spec_ids) == len(set(spec_ids))
            else "FAIL",
            "context_count": len(ids),
        }

    @staticmethod
    def _check_registry_integrity(
        registry: dict[str, Any],
        contexts: list,
        specifications: list,
    ) -> dict[str, Any]:
        ok = (
            registry.get("context_count") == len(contexts)
            and registry.get("specification_count") == len(specifications)
            and len(registry.get("processed_specification_ids", [])) == len(specifications)
            and registry.get("namespace") == "CALCULATION_CONTEXT"
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if contexts and ok else "FAIL",
            "registry_context_count": registry.get("context_count"),
            "actual_context_count": len(contexts),
        }

    @staticmethod
    def _check_geometry_resolved(contexts: list, associations: list) -> dict[str, Any]:
        valid_assoc_ids = {
            item.get("association_id")
            for item in associations
            if item.get("association_status") == STATUS_VALID
        }
        unresolved = [
            item.get("context_id")
            for item in contexts
            if item.get("association_id") in valid_assoc_ids
            and item.get("calculation_status") != STATUS_COMPLETE
        ]
        return {
            "name": "Geometry Resolved For Valid Associations",
            "status": "PASS" if not unresolved else "FAIL",
            "unresolved": unresolved[:10],
        }

    @staticmethod
    def _check_beam_dimensions_available(contexts: list) -> dict[str, Any]:
        missing = [
            item.get("context_id")
            for item in contexts
            if item.get("calculation_status") == STATUS_COMPLETE
            and (
                item.get("beam_width_mm") is None or item.get("beam_depth_mm") is None
            )
        ]
        return {
            "name": "Beam Dimensions Available",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing[:10],
        }

    @staticmethod
    def _check_spans_available(contexts: list) -> dict[str, Any]:
        missing = [
            item.get("context_id")
            for item in contexts
            if item.get("calculation_status") == STATUS_COMPLETE
            and (
                item.get("clear_span_mm") is None or item.get("effective_span_mm") is None
            )
        ]
        return {
            "name": "Spans Available",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing[:10],
        }

    @staticmethod
    def _check_concrete_grade_available(contexts: list) -> dict[str, Any]:
        missing = [item.get("context_id") for item in contexts if not item.get("concrete_grade")]
        return {
            "name": "Concrete Grade Available",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_steel_grade_available(contexts: list) -> dict[str, Any]:
        missing = [item.get("context_id") for item in contexts if not item.get("steel_grade")]
        return {
            "name": "Steel Grade Available",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_cover_resolved(contexts: list) -> dict[str, Any]:
        missing = [
            item.get("context_id")
            for item in contexts
            if item.get("cover_top_mm") is None
            or item.get("cover_bottom_mm") is None
            or item.get("cover_side_mm") is None
        ]
        return {
            "name": "Cover Resolved",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_estimator_rules_loaded(contexts: list) -> dict[str, Any]:
        missing = [
            item.get("context_id")
            for item in contexts
            if not (item.get("estimator_rules") or {}).get("reference_id")
        ]
        return {
            "name": "Estimator Rules Loaded",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_general_notes_referenced(contexts: list) -> dict[str, Any]:
        missing = [
            item.get("context_id")
            for item in contexts
            if not (item.get("development_length_table") or {}).get("reference_id", "").startswith(
                RULE_PROJECT
            )
        ]
        return {
            "name": "General Notes Referenced",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_references_preserved(contexts: list, associations: list) -> dict[str, Any]:
        assoc_by_spec = {item.get("specification_id"): item for item in associations}
        invalid: List[str] = []
        for context in contexts:
            assoc = assoc_by_spec.get(context.get("specification_id"), {})
            for field in REFERENCE_FIELDS:
                assoc_value = assoc.get(field.replace("geometry_association_id", "association_id"))
                if field == "geometry_association_id":
                    assoc_value = assoc.get("association_id")
                context_value = context.get(field)
                if assoc_value and context_value and assoc_value != context_value:
                    invalid.append(context.get("context_id"))
                    break
        return {
            "name": "References Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_deterministic_ids(contexts: list) -> dict[str, Any]:
        invalid = [
            item.get("context_id")
            for item in contexts
            if not str(item.get("context_id", "")).startswith("CALC_CTX::")
        ]
        return {
            "name": "Deterministic IDs",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_registry_lookup_integrity(
        contexts: list,
        registry: dict[str, Any],
    ) -> dict[str, Any]:
        lookup_registry = CalculationContextRegistry()
        for context in contexts:
            lookup_registry.register(context)

        ok = True
        for context in contexts:
            spec_id = str(context.get("specification_id", ""))
            if lookup_registry.context_by_specification(spec_id) != context:
                ok = False
                break

        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if contexts and ok else "FAIL",
            "context_count": len(contexts),
        }

    @staticmethod
    def _check_no_duplicated_geometry_objects(contexts: list) -> dict[str, Any]:
        forbidden_keys = {"beams", "beam_section", "length_model", "geometry", "dimensions"}
        invalid = [
            item.get("context_id")
            for item in contexts
            if forbidden_keys.intersection(item.keys())
        ]
        return {
            "name": "No Duplicated Geometry Objects",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_no_duplicated_rule_tables(contexts: list) -> dict[str, Any]:
        invalid: List[str] = []
        for context in contexts:
            dev_table = context.get("development_length_table", {})
            if isinstance(dev_table, dict) and any(
                key in dev_table for key in ("tables", "development_tables", "Fe550", "Fe500")
            ):
                invalid.append(context.get("context_id"))
        return {
            "name": "No Duplicated Rule Tables",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_traceability_preserved(contexts: list) -> dict[str, Any]:
        missing = [
            item.get("context_id")
            for item in contexts
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if contexts and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_export_consistency(model: dict[str, Any], contexts: list) -> dict[str, Any]:
        registry = model.get("calculation_context_registry", {})
        ok = (
            len(contexts) == registry.get("context_count")
            and set(registry.get("context_ids", [])) == {item.get("context_id") for item in contexts}
        )
        return {
            "name": "Export Consistency",
            "status": "PASS" if contexts and ok else "FAIL",
            "context_count": len(contexts),
        }

    @staticmethod
    def _check_immutable_structure(contexts: list) -> dict[str, Any]:
        invalid: List[str] = []
        for context in contexts:
            status = context.get("calculation_status")
            if status not in VALID_CALCULATION_STATUSES:
                invalid.append(context.get("context_id"))
                continue
            for field in SCALAR_GEOMETRY_FIELDS | MATERIAL_FIELDS:
                value = context.get(field)
                if isinstance(value, (dict, list)):
                    invalid.append(context.get("context_id"))
                    break
        schema_ok = True
        return {
            "name": "Immutable Context Structure",
            "status": "PASS" if contexts and not invalid else "FAIL",
            "invalid": invalid[:10],
            "schema_ok": schema_ok,
        }
