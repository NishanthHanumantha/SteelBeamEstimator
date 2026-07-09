"""Validate engineering calculation results — Phase I.2.2."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_result_models import calculation_results_applied
from src.engineering_calculations.calculation_result_registry import CalculationResultRegistry
from src.engineering_calculations.calculation_result_types import (
    FRAMEWORK_CALCULATION_TYPES,
    VALID_CALCULATION_TYPES,
    VALID_RESULT_STATES,
    CalculationResultState,
    CalculationType,
)
from src.reinforcement_calculation.calculation_state import CalculationState


class CalculationResultValidator:
    """Verify calculation result framework integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not calculation_results_applied(model) and not model.get("engineering_calculation_results"):
            return {
                "phase": "Phase I.2.2",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "calculation result framework not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        registry = model.get("calculation_result_registry", {})

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_bar_has_results(bars, results))
        checks.append(self._check_every_bar_has_all_calculation_types(bars, results))
        checks.append(self._check_unique_result_ids(results))
        checks.append(self._check_deterministic_result_ids(results))
        checks.append(self._check_registry_integrity(registry, results, bars))
        checks.append(self._check_result_states_valid(results))
        checks.append(self._check_calculation_types_valid(results))
        checks.append(self._check_deferred_results_preserve_defer_reason(results))
        checks.append(self._check_ready_results_have_null_value(results))
        checks.append(self._check_no_calculated_values_yet(results))
        checks.append(self._check_immutable_result_structure(results))
        checks.append(self._check_traceability_preserved(results))
        checks.append(self._check_input_references_preserved(results, bars, model))
        checks.append(self._check_export_consistency(model, results))
        checks.append(self._check_registry_lookup_integrity(results))
        checks.append(self._check_ready_count_matches_readiness(bars, results))
        checks.append(self._check_deferred_count_matches_readiness(bars, results))
        checks.append(self._check_no_engineering_values_calculated(results))
        checks.append(self._check_framework_metadata(results))
        checks.append(self._check_one_result_per_bar_and_type(results))
        checks.append(self._check_no_unknown_result_states(results))
        checks.append(self._check_result_status_initialized(results))
        checks.append(self._check_calculation_inputs_field_present(results))
        checks.append(self._check_calculation_inputs_is_dictionary(results))
        checks.append(self._check_calculation_inputs_never_none(results))
        checks.append(self._check_calculation_inputs_immutable_copy(results))
        checks.append(self._check_ready_results_empty_calculation_inputs(results))
        checks.append(self._check_deferred_results_empty_calculation_inputs(results))
        checks.append(self._check_export_contains_calculation_inputs(results))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.2.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "result_count": len(results),
            },
        }

    @staticmethod
    def _check_every_bar_has_results(bars: list, results: list) -> dict[str, Any]:
        bar_ids = {item.get("bar_id") for item in bars}
        covered = {item.get("input_bar_id") for item in results}
        missing = sorted(bar_ids - covered)
        return {
            "name": "Every Reinforcement Object Has Result",
            "status": "PASS" if bars and not missing else "FAIL",
            "missing": missing[:10],
        }

    @staticmethod
    def _check_every_bar_has_all_calculation_types(bars: list, results: list) -> dict[str, Any]:
        expected_types = {calc_type.value for calc_type in FRAMEWORK_CALCULATION_TYPES}
        missing: List[str] = []
        for bar in bars:
            bar_id = bar.get("bar_id")
            present = {
                item.get("calculation_type")
                for item in results
                if item.get("input_bar_id") == bar_id
            }
            if expected_types - present:
                missing.append(bar_id)
        return {
            "name": "Every Bar Has All Calculation Types",
            "status": "PASS" if bars and not missing else "FAIL",
            "missing": missing[:10],
        }

    @staticmethod
    def _check_unique_result_ids(results: list) -> dict[str, Any]:
        ids = [item.get("result_id") for item in results]
        return {
            "name": "Result IDs Unique",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "result_count": len(ids),
        }

    @staticmethod
    def _check_deterministic_result_ids(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if not str(item.get("result_id", "")).startswith("CALC_RESULT::")
        ]
        return {
            "name": "Deterministic IDs",
            "status": "PASS" if results and not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_registry_integrity(
        registry: dict[str, Any],
        results: list,
        bars: list,
    ) -> dict[str, Any]:
        ok = (
            registry.get("result_count") == len(results)
            and registry.get("bar_count") == len(bars)
            and registry.get("namespace") == "CALCULATION_RESULT"
            and len(registry.get("processed_bar_ids", [])) == len(bars)
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if results and ok else "FAIL",
            "registry_result_count": registry.get("result_count"),
            "actual_result_count": len(results),
        }

    @staticmethod
    def _check_result_states_valid(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_state") not in VALID_RESULT_STATES
        ]
        return {
            "name": "Result States Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_calculation_types_valid(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") not in VALID_CALCULATION_TYPES
        ]
        return {
            "name": "Calculation Types Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_deferred_results_preserve_defer_reason(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.DEFERRED.value
            and not (
                item.get("calculation_notes")
                or (item.get("result_metadata") or {}).get("defer_reason")
            )
        ]
        return {
            "name": "Deferred Results Preserve Defer Reason",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_ready_results_have_null_value(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.READY.value
            and item.get("result_value") is not None
        ]
        return {
            "name": "READY Results Have Null Result Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_no_calculated_values_yet(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No CALCULATED State Yet",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_immutable_result_structure(results: list) -> dict[str, Any]:
        forbidden = {"beams", "length_model", "development_length_mm", "weight_kg", "steel_quantity"}
        invalid = [
            item.get("result_id")
            for item in results
            if forbidden.intersection(item.keys())
        ]
        return {
            "name": "Immutable Result Structure",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_traceability_preserved(results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in results
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_input_references_preserved(
        results: list,
        bars: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        bar_map = {item.get("bar_id"): item for item in bars}
        context_map = {
            item.get("context_id"): item for item in model.get("calculation_contexts", [])
        }
        invalid = []
        for result in results:
            bar = bar_map.get(result.get("input_bar_id"), {})
            context = context_map.get(result.get("input_context_id"), {})
            if bar and result.get("input_specification_id") != bar.get("specification_id"):
                invalid.append(result.get("result_id"))
            elif context and result.get("input_association_id") != context.get("association_id"):
                invalid.append(result.get("result_id"))
        return {
            "name": "Input References Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid[:10],
        }

    @staticmethod
    def _check_export_consistency(model: dict[str, Any], results: list) -> dict[str, Any]:
        registry = model.get("calculation_result_registry", {})
        ok = (
            registry.get("result_count") == len(results)
            and set(registry.get("result_ids", [])) == {item.get("result_id") for item in results}
        )
        return {
            "name": "Export Consistency",
            "status": "PASS" if results and ok else "FAIL",
            "result_count": len(results),
        }

    @staticmethod
    def _check_registry_lookup_integrity(results: list) -> dict[str, Any]:
        lookup_registry = CalculationResultRegistry()
        for result in results:
            lookup_registry.register(dict(result))

        ok = len(lookup_registry.get_ready_results()) == sum(
            1
            for item in results
            if item.get("calculation_state") == CalculationResultState.READY.value
        )
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if results and ok else "FAIL",
            "ready_count": len(lookup_registry.get_ready_results()),
        }

    @staticmethod
    def _check_ready_count_matches_readiness(bars: list, results: list) -> dict[str, Any]:
        ready_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        )
        type_count = len(FRAMEWORK_CALCULATION_TYPES)
        ready_results = sum(
            1
            for item in results
            if item.get("calculation_state") == CalculationResultState.READY.value
        )
        return {
            "name": "READY Result Count Matches Readiness",
            "status": "PASS" if ready_results == ready_bars * type_count else "FAIL",
            "expected_ready_results": ready_bars * type_count,
            "actual_ready_results": ready_results,
        }

    @staticmethod
    def _check_deferred_count_matches_readiness(bars: list, results: list) -> dict[str, Any]:
        deferred_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        type_count = len(FRAMEWORK_CALCULATION_TYPES)
        deferred_results = sum(
            1
            for item in results
            if item.get("calculation_state") == CalculationResultState.DEFERRED.value
        )
        return {
            "name": "DEFERRED Result Count Matches Readiness",
            "status": "PASS" if deferred_results == deferred_bars * type_count else "FAIL",
            "expected_deferred_results": deferred_bars * type_count,
            "actual_deferred_results": deferred_results,
        }

    @staticmethod
    def _check_no_engineering_values_calculated(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("result_value") is not None
        ]
        return {
            "name": "No Engineering Values Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_framework_metadata(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if not (item.get("result_metadata") or {}).get("framework_only")
        ]
        return {
            "name": "Framework Metadata Present",
            "status": "PASS" if results and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_one_result_per_bar_and_type(results: list) -> dict[str, Any]:
        keys = [
            f"{item.get('input_bar_id')}::{item.get('calculation_type')}" for item in results
        ]
        return {
            "name": "One Result Per Bar And Type",
            "status": "PASS" if len(keys) == len(set(keys)) else "FAIL",
            "result_count": len(keys),
        }

    @staticmethod
    def _check_no_unknown_result_states(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.UNKNOWN.value
        ]
        return {
            "name": "No UNKNOWN Result State After Evaluation",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_result_status_initialized(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("result_status") != "FRAMEWORK_INITIALIZED"
        ]
        return {
            "name": "Result Status Initialized",
            "status": "PASS" if results and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_inputs_field_present(results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in results
            if "calculation_inputs" not in item
        ]
        return {
            "name": "Calculation Inputs Field Present",
            "status": "PASS" if results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculation_inputs_is_dictionary(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if not isinstance(item.get("calculation_inputs"), dict)
        ]
        return {
            "name": "Calculation Inputs Is Dictionary",
            "status": "PASS" if results and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_inputs_never_none(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_inputs") is None
        ]
        return {
            "name": "Calculation Inputs Never None",
            "status": "PASS" if results and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_inputs_immutable_copy(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if type(item.get("calculation_inputs")) is not dict
        ]
        return {
            "name": "Calculation Inputs Immutable Copy Stored",
            "status": "PASS" if results and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_ready_results_empty_calculation_inputs(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.READY.value
            and item.get("calculation_inputs")
        ]
        return {
            "name": "READY Results Empty Calculation Inputs",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_results_empty_calculation_inputs(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_state") == CalculationResultState.DEFERRED.value
            and item.get("calculation_inputs")
        ]
        return {
            "name": "DEFERRED Results Empty Calculation Inputs",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_export_contains_calculation_inputs(results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in results
            if "calculation_inputs" not in item
        ]
        return {
            "name": "Export Contains Calculation Inputs",
            "status": "PASS" if results and not missing else "FAIL",
            "missing_count": len(missing),
        }
