"""Validate shape code determinations — Phase I.7."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.formula_engine.shape_code_classifier import (
    ShapeCodeClassificationInput,
    ShapeCodeClassifier,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedShapeCodeRule
from src.engineering_calculations.rule_resolution.shape_code_rule_resolver import (
    ShapeCodeRuleResolver,
)
from src.engineering_calculations.shape_code_determiner import shape_code_applied
from src.engineering_calculations.shape_code_registry import ShapeCodeRegistry
from src.engineering_calculations.shape_code_types import (
    CALCULATION_TYPE,
    ENGINE_NAME,
    NAMESPACE_SHAPE_CODE,
    RULE_SOURCE_GENERAL_NOTES,
    ShapeCodeState,
)
from src.reinforcement_calculation.calculation_state import CalculationState


class ShapeCodeValidator:
    """Verify shape code determination integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not shape_code_applied(model) and not model.get("shape_code_results"):
            return {
                "phase": "Phase I.7",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "shape code determination not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        shape_records = model.get("shape_code_results", [])
        registry = model.get("shape_code_registry", {})
        contexts = model.get("calculation_contexts", [])
        dependency_graph = model.get("calculation_dependency_graph", {})

        shape_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]
        results_by_id = {
            str(item.get("result_id", "")): item
            for item in results
            if item.get("result_id")
        }
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_shape_result_has_record(shape_results, shape_records))
        checks.append(self._check_every_bar_has_shape_result(bars, shape_results))
        checks.append(self._check_every_ready_result_evaluated(shape_results))
        checks.append(self._check_deferred_results_unchanged(shape_results, bars))
        checks.append(self._check_blocked_results_unchanged(shape_results, bars))
        checks.append(self._check_dependency_graph_exists(dependency_graph))
        checks.append(self._check_dependency_graph_consulted(shape_records))
        checks.append(self._check_cut_length_prerequisite(shape_records, bars, results_by_id))
        checks.append(self._check_hook_length_prerequisite(shape_records, bars, results_by_id))
        checks.append(self._check_shape_code_resolved(shape_records))
        checks.append(self._check_shape_family_resolved(shape_records))
        checks.append(self._check_general_notes_rules_only(shape_records))
        checks.append(self._check_no_estimator_rule_usage(shape_records))
        checks.append(self._check_classification_inputs_populated(shape_results))
        checks.append(self._check_calculated_result_value_populated(shape_results))
        checks.append(self._check_calculated_result_unit_code(shape_results))
        checks.append(self._check_calculated_trace_exists(shape_results))
        checks.append(self._check_classification_metadata_present(shape_results))
        checks.append(self._check_metadata_matches_result_value(shape_results))
        checks.append(self._check_provenance_attached(shape_results))
        checks.append(self._check_provenance_source_ids_valid(shape_results, results_by_id))
        checks.append(self._check_provenance_three_sources(shape_results))
        checks.append(self._check_deferred_blocked_no_metadata(shape_results))
        checks.append(self._check_registry_integrity(registry, shape_records))
        checks.append(self._check_deterministic_shape_code_ids(shape_records))
        checks.append(self._check_unique_shape_code_ids(shape_records))
        checks.append(self._check_traceability_preserved(shape_records))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, shape_records))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, shape_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, shape_results))
        checks.append(self._check_cut_length_results_preserved(results))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_bbs_generation(results))
        checks.append(self._check_no_quantity_generation(results))
        checks.append(self._check_no_weight_calculation(results))
        checks.append(self._check_export_integrity(registry, shape_records))
        checks.append(self._check_registry_lookup_integrity(shape_records))
        checks.append(self._check_engine_name_for_calculated(shape_results))
        checks.append(self._check_calculation_reproducibility(shape_results))
        checks.append(self._check_statistics_integrity(registry, shape_records))
        checks.append(self._check_classifier_isolated())
        checks.append(self._check_rule_resolver_no_classification())
        checks.append(self._check_dependency_satisfied_for_calculated(bars, graph, results_by_id))
        checks.append(self._check_shape_code_internal_codes_only(shape_records))
        checks.append(self._check_no_fabrication_numbering(shape_results))
        checks.append(self._check_no_bar_marks(shape_results))
        checks.append(self._check_shape_metadata_has_rule_reference(shape_results))
        checks.append(self._check_shape_metadata_has_rule_source(shape_results))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.7",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "shape_result_count": len(shape_results),
                "determination_count": len(shape_records),
            },
        }

    @staticmethod
    def _check_every_shape_result_has_record(shape_results: list, shape_records: list) -> dict[str, Any]:
        result_ids = {item.get("result_id") for item in shape_results}
        covered = {item.get("result_id") for item in shape_records}
        missing = sorted(result_ids - covered)
        return {
            "name": "Every Shape Result Has Record",
            "status": "PASS" if shape_results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_bar_has_shape_result(bars: list, shape_results: list) -> dict[str, Any]:
        bar_ids = {bar.get("bar_id") for bar in bars}
        covered = {item.get("input_bar_id") for item in shape_results}
        missing = sorted(bar_ids - covered)
        return {
            "name": "Every Bar Has Shape Result",
            "status": "PASS" if bars and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_ready_result_evaluated(shape_results: list) -> dict[str, Any]:
        ready = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.READY.value
        ]
        return {
            "name": "Every READY Result Evaluated",
            "status": "PASS" if not ready else "FAIL",
            "ready_count": len(ready),
        }

    @staticmethod
    def _check_deferred_results_unchanged(shape_results: list, bars: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        changed = [
            item.get("result_id")
            for item in shape_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") != CalculationResultState.DEFERRED.value
        ]
        return {
            "name": "Deferred Results Unchanged",
            "status": "PASS" if not changed else "FAIL",
            "changed_count": len(changed),
        }

    @staticmethod
    def _check_blocked_results_unchanged(shape_results: list, bars: list) -> dict[str, Any]:
        blocked_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.BLOCKED.value
        }
        changed = [
            item.get("result_id")
            for item in shape_results
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
    def _check_dependency_graph_consulted(shape_records: list) -> dict[str, Any]:
        missing = [
            item.get("shape_code_id")
            for item in shape_records
            if item.get("determination_state") == ShapeCodeState.CALCULATED.value
            and not item.get("dependency_graph_consulted")
        ]
        return {
            "name": "Dependency Graph Consulted",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    def _check_prerequisite_available(
        self,
        shape_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
        category: str,
        check_name: str,
    ) -> dict[str, Any]:
        bar_by_id = {bar.get("bar_id"): bar for bar in bars}
        invalid = []
        for record in shape_records:
            if record.get("determination_state") != ShapeCodeState.CALCULATED.value:
                continue
            bar = bar_by_id.get(record.get("bar_id"), {})
            references = (bar.get("calculation_index") or {}).get("references") or {}
            result_id = references.get(category)
            result = results_by_id.get(str(result_id))
            if not result or result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                invalid.append(record.get("shape_code_id"))
        return {
            "name": check_name,
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    def _check_cut_length_prerequisite(
        self,
        shape_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return self._check_prerequisite_available(
            shape_records,
            bars,
            results_by_id,
            "CUT_LENGTH",
            "Cut Length Prerequisite Satisfied",
        )

    def _check_hook_length_prerequisite(
        self,
        shape_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return self._check_prerequisite_available(
            shape_records,
            bars,
            results_by_id,
            "HOOK_LENGTH",
            "Hook Length Prerequisite Satisfied",
        )

    @staticmethod
    def _check_shape_code_resolved(shape_records: list) -> dict[str, Any]:
        missing = [
            item.get("shape_code_id")
            for item in shape_records
            if item.get("determination_state") == ShapeCodeState.CALCULATED.value
            and not item.get("shape_code")
        ]
        return {
            "name": "Shape Code Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_shape_family_resolved(shape_records: list) -> dict[str, Any]:
        missing = [
            item.get("shape_code_id")
            for item in shape_records
            if item.get("determination_state") == ShapeCodeState.CALCULATED.value
            and not item.get("shape_family")
        ]
        return {
            "name": "Shape Family Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_general_notes_rules_only(shape_records: list) -> dict[str, Any]:
        invalid = [
            item.get("shape_code_id")
            for item in shape_records
            if item.get("determination_state") == ShapeCodeState.CALCULATED.value
            and item.get("shape_rule_source") not in {
                RULE_SOURCE_GENERAL_NOTES,
                "STRUCTURAL_CODE",
            }
        ]
        return {
            "name": "General Notes Or Structural Code Rules Only",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_estimator_rule_usage(shape_records: list) -> dict[str, Any]:
        invalid = [
            item.get("shape_code_id")
            for item in shape_records
            if "ESTIMATOR" in str(item.get("shape_rule_source", "")).upper()
        ]
        return {
            "name": "Estimator Rules Never Used",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_classification_inputs_populated(shape_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("classification_inputs")
        ]
        return {
            "name": "Classification Inputs Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_value_populated(shape_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("result_value")
        ]
        return {
            "name": "Result Value Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_unit_code(shape_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "CODE"
        ]
        return {
            "name": "Result Unit Is CODE",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_trace_exists(shape_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {
            "name": "Calculation Trace Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_classification_metadata_present(shape_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("classification_metadata")
        ]
        return {
            "name": "Classification Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_metadata_matches_result_value(shape_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("classification_metadata") or {}).get("shape_code")
            != item.get("result_value")
        ]
        return {
            "name": "Metadata Matches Result Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_attached(shape_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_provenance")
        ]
        return {
            "name": "Provenance Attached",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_provenance_source_ids_valid(
        shape_results: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        invalid = []
        for item in shape_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            for source in (item.get("calculation_provenance") or {}).get("sources", []):
                calc_type = str(source.get("calculation_type", ""))
                if calc_type == "BEAM_GEOMETRY":
                    continue
                if str(source.get("result_id", "")) not in results_by_id:
                    invalid.append(item.get("result_id"))
        return {
            "name": "Provenance Source IDs Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_three_sources(shape_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and len((item.get("calculation_provenance") or {}).get("sources", [])) != 3
        ]
        return {
            "name": "Provenance References Three Sources",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_blocked_no_metadata(shape_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state")
            in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }
            and item.get("classification_metadata")
        ]
        return {
            "name": "Deferred Blocked Results Have No Metadata",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(registry: dict, shape_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_SHAPE_CODE
            and registry.get("determination_count") == len(shape_records)
            and set(registry.get("determination_ids", [])) == {
                item.get("shape_code_id") for item in shape_records
            }
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if shape_records and ok else "FAIL",
            "determination_count": len(shape_records),
        }

    @staticmethod
    def _check_deterministic_shape_code_ids(shape_records: list) -> dict[str, Any]:
        ids = [item.get("shape_code_id") for item in shape_records]
        expected = [f"SHAPE_CODE::{index:06d}" for index in range(1, len(shape_records) + 1)]
        return {
            "name": "Deterministic Shape Code IDs",
            "status": "PASS" if ids == expected else "FAIL",
            "record_count": len(shape_records),
        }

    @staticmethod
    def _check_unique_shape_code_ids(shape_records: list) -> dict[str, Any]:
        ids = [item.get("shape_code_id") for item in shape_records]
        return {
            "name": "Unique Shape Code IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_traceability_preserved(shape_records: list) -> dict[str, Any]:
        missing = [
            item.get("shape_code_id")
            for item in shape_records
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if shape_records and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, shape_records: list) -> dict[str, Any]:
        ready_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        )
        calculated = sum(
            1
            for item in shape_records
            if item.get("determination_state") == ShapeCodeState.CALCULATED.value
        )
        return {
            "name": "CALCULATED Count Matches READY Bars",
            "status": "PASS" if calculated == ready_bars else "FAIL",
            "expected": ready_bars,
            "actual": calculated,
        }

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, shape_records: list) -> dict[str, Any]:
        deferred_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        deferred = sum(
            1
            for item in shape_records
            if item.get("determination_state") == ShapeCodeState.DEFERRED.value
        )
        return {
            "name": "Deferred Count Matches Deferred Bars",
            "status": "PASS" if deferred == deferred_bars else "FAIL",
            "expected": deferred_bars,
            "actual": deferred,
        }

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, shape_results: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        invalid = [
            item.get("result_id")
            for item in shape_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No Calculated For Deferred Readiness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_cut_length_results_preserved(results: list) -> dict[str, Any]:
        cut_calculated = sum(
            1
            for item in results
            if item.get("calculation_type") == CalculationType.CUT_LENGTH.value
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        )
        return {
            "name": "Cut Length Results Preserved",
            "status": "PASS" if cut_calculated > 0 else "FAIL",
            "calculated_count": cut_calculated,
        }

    @staticmethod
    def _check_no_geometry_modified(model: dict[str, Any], contexts: list) -> dict[str, Any]:
        geometry_keys = {"geometry", "beam_geometry", "length_mm", "cover_mm"}
        violations = []
        for context in contexts:
            for key in geometry_keys:
                if key in (context.get("modified_fields") or []):
                    violations.append(context.get("context_id"))
        return {
            "name": "No Geometry Modified",
            "status": "PASS" if not violations else "FAIL",
            "violation_count": len(violations),
        }

    @staticmethod
    def _check_no_bbs_generation(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.BAR_SCHEDULE.value
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") is not None
        ]
        return {
            "name": "No BBS Generation",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_quantity_generation(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.BOQ.value
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") is not None
        ]
        return {
            "name": "No Quantity Generation",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_weight_calculation(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.STEEL_WEIGHT.value
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") is not None
        ]
        return {
            "name": "No Weight Calculation",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_export_integrity(registry: dict, shape_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(shape_records)
        return {
            "name": "Export Integrity",
            "status": "PASS" if shape_records and ok else "FAIL",
            "determination_count": len(shape_records),
        }

    @staticmethod
    def _check_registry_lookup_integrity(shape_records: list) -> dict[str, Any]:
        lookup_registry = ShapeCodeRegistry()
        for record in shape_records:
            lookup_registry.register(dict(record))
        calculated = sum(
            1
            for item in shape_records
            if item.get("determination_state") == ShapeCodeState.CALCULATED.value
        )
        ok = len(lookup_registry.records_by_state(ShapeCodeState.CALCULATED.value)) == calculated
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if shape_records and ok else "FAIL",
            "calculated_count": calculated,
        }

    @staticmethod
    def _check_engine_name_for_calculated(shape_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("engine_name") != ENGINE_NAME
        ]
        return {
            "name": "Engine Name For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_reproducibility(shape_results: list) -> dict[str, Any]:
        invalid = []
        for item in shape_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            inputs = item.get("classification_inputs") or {}
            metadata = item.get("classification_metadata") or {}
            rule = ResolvedShapeCodeRule(
                shape_code=str(inputs.get("shape_code", "")),
                shape_family=str(inputs.get("shape_family", "")),
                bend_count=int(inputs.get("bend_count", 0)),
                hook_count=int(inputs.get("hook_count", 0)),
                closed_loop=bool(inputs.get("closed_loop", False)),
                open_loop=bool(inputs.get("open_loop", False)),
                anchorage_configuration=str(inputs.get("anchorage_configuration", "")),
                stirrup_classification=str(inputs.get("stirrup_classification", "")),
                link_classification=str(inputs.get("link_classification", "")),
                main_bar_classification=str(inputs.get("main_bar_classification", "")),
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
            expected = ShapeCodeClassifier.classify(
                ShapeCodeClassificationInput(
                    reinforcement_role=str(inputs.get("reinforcement_role", "")),
                    bar_type=str(inputs.get("bar_type", "")),
                    hook_count=int(inputs.get("hook_count", 0)),
                    bend_count=int(inputs.get("bend_count", 0)),
                    closed_loop=bool(inputs.get("closed_loop", False)),
                    open_loop=bool(inputs.get("open_loop", False)),
                    hook_angle=int(inputs.get("hook_angle", 90)),
                    cut_length_mm=int(inputs.get("cut_length_mm", 0)),
                    clear_span_mm=int(inputs.get("clear_span_mm", 0)),
                    resolved_rule=rule,
                )
            )
            if expected.shape_code != item.get("result_value"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Calculation Reproducibility",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_statistics_integrity(registry: dict, shape_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(shape_records)
        return {
            "name": "Statistics Integrity",
            "status": "PASS" if shape_records and ok else "FAIL",
            "determination_count": len(shape_records),
        }

    @staticmethod
    def _check_classifier_isolated() -> dict[str, Any]:
        import inspect

        source = inspect.getsource(ShapeCodeClassifier)
        forbidden = (
            "EngineeringRuleCache",
            "general_notes",
            "ShapeCodeRuleResolver",
            "RuleResolver",
            "dependency_graph",
        )
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Classifier Isolated",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_rule_resolver_no_classification() -> dict[str, Any]:
        import inspect

        source = inspect.getsource(ShapeCodeRuleResolver)
        forbidden = ("ShapeCodeClassifier", "classify(", "SC_STRAIGHT", "SC_STIRRUP", "SC_LINK")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Rule Resolver Performs No Classification",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_dependency_satisfied_for_calculated(
        bars: list,
        graph: CalculationDependencyGraph,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        invalid = []
        for bar in bars:
            if (bar.get("calculation_readiness") or {}).get("calculation_state") != CalculationState.READY.value:
                continue
            references = (bar.get("calculation_index") or {}).get("references") or {}
            for dependency in graph.depends_on("SHAPE_CODE"):
                result_id = references.get(dependency)
                result = results_by_id.get(str(result_id)) if result_id else None
                if (
                    not result
                    or result.get("calculation_state") != CalculationResultState.CALCULATED.value
                ):
                    invalid.append(bar.get("bar_id"))
                    break
        return {
            "name": "Dependency Satisfied For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_shape_code_internal_codes_only(shape_records: list) -> dict[str, Any]:
        invalid = [
            item.get("shape_code_id")
            for item in shape_records
            if item.get("determination_state") == ShapeCodeState.CALCULATED.value
            and not str(item.get("shape_code", "")).startswith("SC_")
        ]
        return {
            "name": "Internal Shape Codes Only",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_fabrication_numbering(shape_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("fabrication_number") is not None
        ]
        return {
            "name": "No Fabrication Numbering",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_bar_marks(shape_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("bar_mark") is not None
        ]
        return {
            "name": "No Bar Marks",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_shape_metadata_has_rule_reference(shape_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("classification_metadata") or {}).get("rule_reference")
        ]
        return {
            "name": "Metadata Has Rule Reference",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_shape_metadata_has_rule_source(shape_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in shape_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("classification_metadata") or {}).get("rule_source")
        ]
        return {
            "name": "Metadata Has Rule Source",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }
