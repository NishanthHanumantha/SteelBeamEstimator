"""Validate bar identity determinations — Phase I.8."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.bar_identity.bar_identity_determiner import (
    BarIdentityDeterminer,
    bar_identity_applied,
)
from src.engineering_calculations.bar_identity.bar_identity_registry import BarIdentityRegistry
from src.engineering_calculations.bar_identity.bar_identity_types import (
    CALCULATION_TYPE,
    ENGINE_NAME,
    NAMESPACE_BAR_IDENTITY,
    PREFIX_ENGINEERING_BAR,
    RULE_SOURCE_GENERAL_NOTES,
    BarIdentityState,
)
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.formula_engine.bar_identity_classifier import (
    BarIdentityClassificationInput,
    BarIdentityClassifier,
)
from src.engineering_calculations.rule_resolution.bar_identity_rule_resolver import (
    BarIdentityRuleResolver,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBarIdentityRule
from src.reinforcement_calculation.calculation_state import CalculationState


class BarIdentityValidator:
    """Verify bar identity determination integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not bar_identity_applied(model) and not model.get("bar_identity_results"):
            return {
                "phase": "Phase I.8",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "bar identity determination not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        identity_records = model.get("bar_identity_results", [])
        registry = model.get("bar_identity_registry", {})
        contexts = model.get("calculation_contexts", [])
        dependency_graph = model.get("calculation_dependency_graph", {})
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }

        identity_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]
        results_by_id = {
            str(item.get("result_id", "")): item
            for item in results
            if item.get("result_id")
        }
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_identity_result_has_record(identity_results, identity_records))
        checks.append(self._check_every_bar_has_identity_result(bars, identity_results))
        checks.append(self._check_every_ready_result_evaluated(identity_results))
        checks.append(self._check_deferred_results_unchanged(identity_results, bars))
        checks.append(self._check_blocked_results_unchanged(identity_results, bars))
        checks.append(self._check_dependency_graph_exists(dependency_graph))
        checks.append(self._check_dependency_graph_consulted(identity_records))
        checks.append(self._check_prerequisite(identity_records, bars, results_by_id, "CUT_LENGTH", "Cut Length Prerequisite"))
        checks.append(self._check_prerequisite(identity_records, bars, results_by_id, "HOOK_LENGTH", "Hook Length Prerequisite"))
        checks.append(self._check_prerequisite(identity_records, bars, results_by_id, "DEVELOPMENT_LENGTH", "Development Length Prerequisite"))
        checks.append(self._check_prerequisite(identity_records, bars, results_by_id, "LAP_LENGTH", "Lap Length Prerequisite"))
        checks.append(self._check_shape_code_prerequisite(identity_records, bars, results))
        checks.append(self._check_engineering_bar_id_populated(identity_records))
        checks.append(self._check_bar_mark_populated(identity_records))
        checks.append(self._check_engineering_group_populated(identity_records))
        checks.append(self._check_general_notes_rules_only(identity_records))
        checks.append(self._check_no_estimator_rule_usage(identity_records))
        checks.append(self._check_classification_inputs_populated(identity_results))
        checks.append(self._check_calculated_result_value_populated(identity_results))
        checks.append(self._check_calculated_result_unit_identity(identity_results))
        checks.append(self._check_calculated_trace_exists(identity_results))
        checks.append(self._check_identity_metadata_present(identity_results))
        checks.append(self._check_metadata_matches_result_value(identity_results))
        checks.append(self._check_provenance_attached(identity_results))
        checks.append(self._check_provenance_source_ids_valid(identity_results, results_by_id))
        checks.append(self._check_provenance_three_sources(identity_results))
        checks.append(self._check_deferred_blocked_no_metadata(identity_results))
        checks.append(self._check_registry_integrity(registry, identity_records))
        checks.append(self._check_deterministic_bar_identity_ids(identity_records))
        checks.append(self._check_unique_bar_identity_ids(identity_records))
        checks.append(self._check_unique_engineering_bar_ids(identity_records))
        checks.append(self._check_traceability_preserved(identity_records))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, identity_records))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, identity_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, identity_results))
        checks.append(self._check_shape_code_results_preserved(results))
        checks.append(self._check_cut_length_results_preserved(results))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_bbs_generation(results))
        checks.append(self._check_no_quantity_generation(results))
        checks.append(self._check_no_weight_calculation(results))
        checks.append(self._check_export_integrity(registry, identity_records))
        checks.append(self._check_registry_lookup_integrity(identity_records))
        checks.append(self._check_engine_name_for_calculated(identity_results))
        checks.append(self._check_calculation_reproducibility(identity_results, bars, context_by_spec, results_by_id))
        checks.append(self._check_statistics_integrity(registry, identity_records))
        checks.append(self._check_classifier_isolated())
        checks.append(self._check_rule_resolver_no_identity_generation())
        checks.append(self._check_dependency_satisfied_for_calculated(bars, graph, results_by_id, results))
        checks.append(self._check_group_consistency(identity_records))
        checks.append(self._check_group_reproducibility(bars, context_by_spec, results_by_id))
        checks.append(self._check_stable_identity_ordering(identity_records))
        checks.append(self._check_duplicate_detection_enabled(identity_records))
        checks.append(self._check_no_fabrication_numbering(identity_results))
        checks.append(self._check_no_bbs_fields(identity_results))
        checks.append(self._check_identity_metadata_has_rule_reference(identity_results))
        checks.append(self._check_identity_metadata_has_rule_source(identity_results))
        checks.append(self._check_engine_separation())

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.8",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "identity_result_count": len(identity_results),
                "determination_count": len(identity_records),
            },
        }

    @staticmethod
    def _check_every_identity_result_has_record(identity_results: list, identity_records: list) -> dict[str, Any]:
        result_ids = {item.get("result_id") for item in identity_results}
        covered = {item.get("result_id") for item in identity_records}
        missing = sorted(result_ids - covered)
        return {
            "name": "Every Identity Result Has Record",
            "status": "PASS" if identity_results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_bar_has_identity_result(bars: list, identity_results: list) -> dict[str, Any]:
        bar_ids = {bar.get("bar_id") for bar in bars}
        covered = {item.get("input_bar_id") for item in identity_results}
        missing = sorted(bar_ids - covered)
        return {
            "name": "Every Bar Has Identity Result",
            "status": "PASS" if bars and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_ready_result_evaluated(identity_results: list) -> dict[str, Any]:
        ready = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.READY.value
        ]
        return {
            "name": "Every READY Result Evaluated",
            "status": "PASS" if not ready else "FAIL",
            "ready_count": len(ready),
        }

    @staticmethod
    def _check_deferred_results_unchanged(identity_results: list, bars: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        changed = [
            item.get("result_id")
            for item in identity_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") != CalculationResultState.DEFERRED.value
        ]
        return {
            "name": "Deferred Results Unchanged",
            "status": "PASS" if not changed else "FAIL",
            "changed_count": len(changed),
        }

    @staticmethod
    def _check_blocked_results_unchanged(identity_results: list, bars: list) -> dict[str, Any]:
        blocked_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.BLOCKED.value
        }
        changed = [
            item.get("result_id")
            for item in identity_results
            if item.get("input_bar_id") in blocked_bar_ids
            and item.get("calculation_state") != CalculationResultState.BLOCKED.value
        ]
        return {
            "name": "Blocked Results Unchanged",
            "status": "PASS" if not changed else "FAIL",
            "changed_count": len(changed),
        }

    @staticmethod
    def _check_dependency_graph_exists(dependency_graph: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Dependency Graph Exists",
            "status": "PASS" if dependency_graph.get("nodes") else "FAIL",
        }

    @staticmethod
    def _check_dependency_graph_consulted(identity_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_identity_id")
            for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
            and not item.get("dependency_graph_consulted")
        ]
        return {
            "name": "Dependency Graph Consulted",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_prerequisite(
        identity_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
        category: str,
        check_name: str,
    ) -> dict[str, Any]:
        bar_by_id = {bar.get("bar_id"): bar for bar in bars}
        invalid = []
        for record in identity_records:
            if record.get("determination_state") != BarIdentityState.CALCULATED.value:
                continue
            bar = bar_by_id.get(record.get("bar_id"), {})
            references = (bar.get("calculation_index") or {}).get("references") or {}
            result_id = references.get(category)
            result = results_by_id.get(str(result_id))
            if not result or result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                invalid.append(record.get("bar_identity_id"))
        return {
            "name": check_name,
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_shape_code_prerequisite(identity_records: list, bars: list, results: list) -> dict[str, Any]:
        bar_by_id = {bar.get("bar_id"): bar for bar in bars}
        invalid = []
        for record in identity_records:
            if record.get("determination_state") != BarIdentityState.CALCULATED.value:
                continue
            bar = bar_by_id.get(record.get("bar_id"), {})
            shape = next(
                (
                    item
                    for item in results
                    if item.get("input_bar_id") == bar.get("bar_id")
                    and item.get("calculation_type") == CalculationType.SHAPE_CODE.value
                    and item.get("calculation_state") == CalculationResultState.CALCULATED.value
                ),
                None,
            )
            if not shape:
                invalid.append(record.get("bar_identity_id"))
        return {
            "name": "Shape Code Prerequisite",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engineering_bar_id_populated(identity_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_identity_id")
            for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
            and not str(item.get("engineering_bar_id", "")).startswith(f"{PREFIX_ENGINEERING_BAR}::")
        ]
        return {"name": "Engineering Bar Id Populated", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_bar_mark_populated(identity_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_identity_id")
            for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
            and not str(item.get("engineering_bar_mark", "")).startswith("BM")
        ]
        return {"name": "Bar Mark Populated", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_engineering_group_populated(identity_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_identity_id")
            for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
            and not item.get("engineering_group_id")
        ]
        return {"name": "Engineering Group Id Populated", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_general_notes_rules_only(identity_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_identity_id")
            for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
            and item.get("identity_rule_source") not in {RULE_SOURCE_GENERAL_NOTES, "STRUCTURAL_CODE"}
        ]
        return {"name": "General Notes Or Structural Code Rules Only", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_no_estimator_rule_usage(identity_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_identity_id")
            for item in identity_records
            if "ESTIMATOR" in str(item.get("identity_rule_source", "")).upper()
        ]
        return {"name": "No Estimator Rules", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_classification_inputs_populated(identity_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("classification_inputs")
        ]
        return {"name": "Classification Inputs Populated", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_calculated_result_value_populated(identity_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("result_value")
        ]
        return {"name": "Result Value Populated", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_calculated_result_unit_identity(identity_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "IDENTITY"
        ]
        return {"name": "Result Unit Is IDENTITY", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_calculated_trace_exists(identity_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {"name": "Calculation Trace Exists", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_identity_metadata_present(identity_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("identity_metadata")
        ]
        return {"name": "Identity Metadata Present", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_metadata_matches_result_value(identity_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("identity_metadata") or {}).get("engineering_bar_id") != item.get("result_value")
        ]
        return {"name": "Metadata Matches Result Value", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_provenance_attached(identity_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_provenance")
        ]
        return {"name": "Provenance Attached", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_provenance_source_ids_valid(identity_results: list, results_by_id: dict) -> dict[str, Any]:
        invalid = []
        for item in identity_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            for source in (item.get("calculation_provenance") or {}).get("sources", []):
                if str(source.get("calculation_type", "")) == "BEAM_GEOMETRY":
                    continue
                if str(source.get("result_id", "")) not in results_by_id:
                    invalid.append(item.get("result_id"))
        return {"name": "Provenance Source IDs Valid", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_provenance_three_sources(identity_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and len((item.get("calculation_provenance") or {}).get("sources", [])) != 3
        ]
        return {"name": "Provenance Three Sources", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_deferred_blocked_no_metadata(identity_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in identity_results
            if item.get("calculation_state") in {CalculationResultState.DEFERRED.value, CalculationResultState.BLOCKED.value}
            and item.get("identity_metadata")
        ]
        return {"name": "Deferred Blocked No Metadata", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_registry_integrity(registry: dict, identity_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_BAR_IDENTITY
            and registry.get("determination_count") == len(identity_records)
            and set(registry.get("determination_ids", [])) == {item.get("bar_identity_id") for item in identity_records}
        )
        return {"name": "Registry Integrity", "status": "PASS" if identity_records and ok else "FAIL", "determination_count": len(identity_records)}

    @staticmethod
    def _check_deterministic_bar_identity_ids(identity_records: list) -> dict[str, Any]:
        ids = [item.get("bar_identity_id") for item in identity_records]
        expected = [f"BAR_IDENTITY::{index:06d}" for index in range(1, len(identity_records) + 1)]
        return {"name": "Deterministic Bar Identity IDs", "status": "PASS" if ids == expected else "FAIL", "record_count": len(identity_records)}

    @staticmethod
    def _check_unique_bar_identity_ids(identity_records: list) -> dict[str, Any]:
        ids = [item.get("bar_identity_id") for item in identity_records]
        return {"name": "Unique Bar Identity IDs", "status": "PASS" if len(ids) == len(set(ids)) else "FAIL", "record_count": len(ids)}

    @staticmethod
    def _check_unique_engineering_bar_ids(identity_records: list) -> dict[str, Any]:
        calculated = [
            item.get("engineering_bar_id")
            for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
        ]
        return {"name": "Unique Engineering Bar Ids", "status": "PASS" if len(calculated) == len(set(calculated)) else "FAIL", "record_count": len(calculated)}

    @staticmethod
    def _check_traceability_preserved(identity_records: list) -> dict[str, Any]:
        missing = [item.get("bar_identity_id") for item in identity_records if not (item.get("traceability") or {}).get("lineage")]
        return {"name": "Traceability Preserved", "status": "PASS" if identity_records and not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, identity_records: list) -> dict[str, Any]:
        ready_bars = sum(1 for bar in bars if (bar.get("calculation_readiness") or {}).get("calculation_state") == CalculationState.READY.value)
        calculated = sum(1 for item in identity_records if item.get("determination_state") == BarIdentityState.CALCULATED.value)
        return {"name": "Calculated Count Matches Ready Bars", "status": "PASS" if calculated == ready_bars else "FAIL", "expected": ready_bars, "actual": calculated}

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, identity_records: list) -> dict[str, Any]:
        deferred_bars = sum(1 for bar in bars if (bar.get("calculation_readiness") or {}).get("calculation_state") == CalculationState.DEFERRED.value)
        deferred = sum(1 for item in identity_records if item.get("determination_state") == BarIdentityState.DEFERRED.value)
        return {"name": "Deferred Count Matches Deferred Bars", "status": "PASS" if deferred == deferred_bars else "FAIL", "expected": deferred_bars, "actual": deferred}

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, identity_results: list) -> dict[str, Any]:
        deferred_bar_ids = {bar.get("bar_id") for bar in bars if (bar.get("calculation_readiness") or {}).get("calculation_state") == CalculationState.DEFERRED.value}
        invalid = [item.get("result_id") for item in identity_results if item.get("input_bar_id") in deferred_bar_ids and item.get("calculation_state") == CalculationResultState.CALCULATED.value]
        return {"name": "No Calculated For Deferred Readiness", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_shape_code_results_preserved(results: list) -> dict[str, Any]:
        calculated = sum(1 for item in results if item.get("calculation_type") == CalculationType.SHAPE_CODE.value and item.get("calculation_state") == CalculationResultState.CALCULATED.value)
        return {"name": "Shape Code Results Preserved", "status": "PASS" if calculated > 0 else "FAIL", "calculated_count": calculated}

    @staticmethod
    def _check_cut_length_results_preserved(results: list) -> dict[str, Any]:
        calculated = sum(1 for item in results if item.get("calculation_type") == CalculationType.CUT_LENGTH.value and item.get("calculation_state") == CalculationResultState.CALCULATED.value)
        return {"name": "Cut Length Results Preserved", "status": "PASS" if calculated > 0 else "FAIL", "calculated_count": calculated}

    @staticmethod
    def _check_no_geometry_modified(model: dict[str, Any], contexts: list) -> dict[str, Any]:
        geometry_keys = {"geometry", "beam_geometry", "length_mm", "cover_mm"}
        violations = [context.get("context_id") for context in contexts for key in geometry_keys if key in (context.get("modified_fields") or [])]
        return {"name": "No Geometry Modified", "status": "PASS" if not violations else "FAIL", "violation_count": len(violations)}

    @staticmethod
    def _check_no_bbs_generation(results: list) -> dict[str, Any]:
        invalid = [item.get("result_id") for item in results if item.get("calculation_type") == CalculationType.BAR_SCHEDULE.value and item.get("calculation_state") == CalculationResultState.CALCULATED.value and item.get("result_value") is not None]
        return {"name": "No BBS Generation", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_no_quantity_generation(results: list) -> dict[str, Any]:
        invalid = [item.get("result_id") for item in results if item.get("calculation_type") == CalculationType.BOQ.value and item.get("calculation_state") == CalculationResultState.CALCULATED.value and item.get("result_value") is not None]
        return {"name": "No Quantity Generation", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_no_weight_calculation(results: list) -> dict[str, Any]:
        invalid = [item.get("result_id") for item in results if item.get("calculation_type") == CalculationType.STEEL_WEIGHT.value and item.get("calculation_state") == CalculationResultState.CALCULATED.value and item.get("result_value") is not None]
        return {"name": "No Weight Calculation", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_export_integrity(registry: dict, identity_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(identity_records)
        return {"name": "Export Integrity", "status": "PASS" if identity_records and ok else "FAIL", "determination_count": len(identity_records)}

    @staticmethod
    def _check_registry_lookup_integrity(identity_records: list) -> dict[str, Any]:
        lookup_registry = BarIdentityRegistry()
        for record in identity_records:
            lookup_registry.register(dict(record))
        calculated = sum(1 for item in identity_records if item.get("determination_state") == BarIdentityState.CALCULATED.value)
        ok = len(lookup_registry.records_by_state(BarIdentityState.CALCULATED.value)) == calculated
        return {"name": "Registry Lookup Integrity", "status": "PASS" if identity_records and ok else "FAIL", "calculated_count": calculated}

    @staticmethod
    def _check_engine_name_for_calculated(identity_results: list) -> dict[str, Any]:
        invalid = [item.get("result_id") for item in identity_results if item.get("calculation_state") == CalculationResultState.CALCULATED.value and item.get("engine_name") != ENGINE_NAME]
        return {"name": "Engine Name For Calculated", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_calculation_reproducibility(identity_results: list, bars: list, context_by_spec: dict, results_by_id: dict) -> dict[str, Any]:
        bar_by_id = {bar.get("bar_id"): bar for bar in bars}
        invalid = []
        for item in identity_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            inputs = item.get("classification_inputs") or {}
            metadata = item.get("identity_metadata") or {}
            rule = ResolvedBarIdentityRule(
                grouping_strategy=str(inputs.get("grouping_strategy", "")),
                equivalence_attributes=tuple(inputs.get("equivalence_attributes", [])),
                include_support_configuration=bool(inputs.get("include_support_configuration", False)),
                include_geometry_signature=bool(inputs.get("include_geometry_signature", False)),
                rule_source=str(metadata.get("rule_source", "")),
                rule_name=str(metadata.get("rule_name", "")),
                rule_reference=str(metadata.get("rule_reference", "")),
                rule_priority=1,
                structural_code_reference="",
                general_notes_reference="",
                lookup_path=tuple(metadata.get("lookup_path", [])),
                reinforcement_role=str(inputs.get("reinforcement_role", "")),
                rule_description="",
            )
            bar = bar_by_id.get(item.get("input_bar_id"), {})
            context = context_by_spec.get(str(bar.get("specification_id", "")), {})
            signature = BarIdentityDeterminer.build_equivalence_signature(bar, context, results_by_id)
            expected = BarIdentityClassifier.classify(
                BarIdentityClassificationInput(
                    bar_id=str(bar.get("bar_id", "")),
                    equivalence_signature=signature,
                    identity_sequence=int(str(item.get("result_value", "")).split("::")[-1]),
                    group_sequence=int(str((item.get("identity_metadata") or {}).get("engineering_group_id", "GROUP::0")).split("::")[-1]),
                    instance_index_in_group=int(inputs.get("instance_index_in_group") or metadata.get("instance_index_in_group") or 0),
                    group_member_count=int(inputs.get("group_member_count") or metadata.get("group_member_count") or 0),
                    resolved_rule=rule,
                )
            )
            if expected.engineering_bar_id != item.get("result_value"):
                invalid.append(item.get("result_id"))
        return {"name": "Calculation Reproducibility", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_statistics_integrity(registry: dict, identity_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(identity_records)
        return {"name": "Statistics Integrity", "status": "PASS" if identity_records and ok else "FAIL", "determination_count": len(identity_records)}

    @staticmethod
    def _check_classifier_isolated() -> dict[str, Any]:
        import inspect
        source = inspect.getsource(BarIdentityClassifier)
        forbidden = ("EngineeringRuleCache", "BarIdentityRuleResolver", "dependency_graph", "RuleResolver")
        violations = [token for token in forbidden if token in source]
        return {"name": "Classifier Isolated", "status": "PASS" if not violations else "FAIL", "violations": violations}

    @staticmethod
    def _check_rule_resolver_no_identity_generation() -> dict[str, Any]:
        import inspect
        source = inspect.getsource(BarIdentityRuleResolver)
        forbidden = ("BarIdentityClassifier", "classify(", "format_engineering_bar_id", "format_bar_mark", "BM")
        violations = [token for token in forbidden if token in source]
        return {"name": "Rule Resolver No Identity Generation", "status": "PASS" if not violations else "FAIL", "violations": violations}

    @staticmethod
    def _check_dependency_satisfied_for_calculated(bars: list, graph: CalculationDependencyGraph, results_by_id: dict, results: list) -> dict[str, Any]:
        invalid = []
        for bar in bars:
            if (bar.get("calculation_readiness") or {}).get("calculation_state") != CalculationState.READY.value:
                continue
            references = (bar.get("calculation_index") or {}).get("references") or {}
            for dependency in graph.depends_on("BAR_IDENTITY"):
                if dependency == "SHAPE_CODE":
                    shape = next((item for item in results if item.get("input_bar_id") == bar.get("bar_id") and item.get("calculation_type") == CalculationType.SHAPE_CODE.value), None)
                    if not shape or shape.get("calculation_state") != CalculationResultState.CALCULATED.value:
                        invalid.append(bar.get("bar_id"))
                    continue
                result = results_by_id.get(str(references.get(dependency)))
                if not result or result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                    invalid.append(bar.get("bar_id"))
        return {"name": "Dependency Satisfied For Calculated", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_group_consistency(identity_records: list) -> dict[str, Any]:
        invalid = []
        groups: dict[str, set[str]] = {}
        for record in identity_records:
            if record.get("determination_state") != BarIdentityState.CALCULATED.value:
                continue
            group_id = str(record.get("engineering_group_id", ""))
            signature = str(record.get("equivalence_signature", ""))
            groups.setdefault(group_id, set()).add(signature)
            if len(groups[group_id]) > 1:
                invalid.append(group_id)
        return {"name": "Group Consistency", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_group_reproducibility(bars: list, context_by_spec: dict, results_by_id: dict) -> dict[str, Any]:
        from src.engineering_calculations.bar_identity.bar_identity_engine import BarIdentityEngine
        engine = BarIdentityEngine()
        plan = engine._build_assignment_plan(bars, context_by_spec, results_by_id)
        invalid = [bar_id for bar_id, assignment in plan.items() if not assignment.get("group_sequence")]
        return {"name": "Group Reproducibility", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_stable_identity_ordering(identity_records: list) -> dict[str, Any]:
        calculated = [item for item in identity_records if item.get("determination_state") == BarIdentityState.CALCULATED.value]
        ids = [int(str(item.get("engineering_bar_id", "BAR::0")).split("::")[-1]) for item in calculated]
        expected = list(range(1, len(ids) + 1))
        return {"name": "Stable Identity Ordering", "status": "PASS" if sorted(ids) == expected else "FAIL", "record_count": len(ids)}

    @staticmethod
    def _check_duplicate_detection_enabled(identity_records: list) -> dict[str, Any]:
        calculated = [item for item in identity_records if item.get("determination_state") == BarIdentityState.CALCULATED.value]
        has_group = any(int(item.get("group_member_count") or 0) > 1 for item in calculated)
        has_flag = any(item.get("is_duplicate") is not None for item in calculated)
        return {"name": "Duplicate Detection Enabled", "status": "PASS" if calculated and has_flag else "FAIL", "grouped_present": has_group}

    @staticmethod
    def _check_no_fabrication_numbering(identity_results: list) -> dict[str, Any]:
        invalid = [item.get("result_id") for item in identity_results if item.get("fabrication_number") is not None]
        return {"name": "No Fabrication Numbering", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_no_bbs_fields(identity_results: list) -> dict[str, Any]:
        invalid = [item.get("result_id") for item in identity_results if item.get("bar_schedule") or item.get("bbs_entry")]
        return {"name": "No BBS Fields", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_identity_metadata_has_rule_reference(identity_results: list) -> dict[str, Any]:
        missing = [item.get("result_id") for item in identity_results if item.get("calculation_state") == CalculationResultState.CALCULATED.value and not (item.get("identity_metadata") or {}).get("rule_reference")]
        return {"name": "Identity Metadata Rule Reference", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_identity_metadata_has_rule_source(identity_results: list) -> dict[str, Any]:
        missing = [item.get("result_id") for item in identity_results if item.get("calculation_state") == CalculationResultState.CALCULATED.value and not (item.get("identity_metadata") or {}).get("rule_source")]
        return {"name": "Identity Metadata Rule Source", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_engine_separation() -> dict[str, Any]:
        import inspect
        from src.engineering_calculations.bar_identity.bar_identity_determiner import (
            BarIdentityDeterminer,
        )
        from src.engineering_calculations.bar_identity.bar_identity_engine import BarIdentityEngine

        engine_source = inspect.getsource(BarIdentityEngine)
        determiner_source = inspect.getsource(BarIdentityDeterminer)
        engine_ok = "BarIdentityDeterminer" in engine_source and "BarIdentityClassifier" not in engine_source
        determiner_ok = (
            "BarIdentityClassifier" in determiner_source
            and "BarIdentityRuleResolver" in determiner_source
        )
        ok = engine_ok and determiner_ok
        return {"name": "Engine Separation", "status": "PASS" if ok else "FAIL"}
