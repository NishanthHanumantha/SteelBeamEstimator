"""Validate development length determinations — Phase I.3."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.development_length_determiner import development_length_applied
from src.engineering_calculations.development_length_registry import DevelopmentLengthRegistry
from src.engineering_calculations.development_length_types import (
    CALCULATION_TYPE,
    ENGINE_NAME,
    NAMESPACE_DEV_LENGTH,
    RESULT_STATUS_SUCCESS,
    DevelopmentLengthState,
)
from src.general_notes.ld_table_selector import steel_table_key
from src.reinforcement_calculation.calculation_state import CalculationState


class DevelopmentLengthValidator:
    """Verify development length determination integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not development_length_applied(model) and not model.get("development_length_results"):
            return {
                "phase": "Phase I.3",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "development length determination not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        dev_records = model.get("development_length_results", [])
        registry = model.get("development_length_registry", {})
        contexts = model.get("calculation_contexts", [])

        dev_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_dev_length_result_has_record(dev_results, dev_records))
        checks.append(self._check_every_ready_result_evaluated(dev_results))
        checks.append(self._check_deferred_results_unchanged(dev_results, bars))
        checks.append(self._check_development_length_resolved(dev_records))
        checks.append(self._check_engineering_rule_cache_referenced(dev_records))
        checks.append(self._check_calculated_inputs_populated(dev_results))
        checks.append(self._check_calculated_result_value_populated(dev_results))
        checks.append(self._check_calculated_result_unit_mm(dev_results))
        checks.append(self._check_calculated_trace_exists(dev_results))
        checks.append(self._check_registry_integrity(registry, dev_records))
        checks.append(self._check_deterministic_dev_length_ids(dev_records))
        checks.append(self._check_traceability_preserved(dev_records))
        checks.append(self._check_unique_dev_length_ids(dev_records))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, dev_records))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, dev_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, dev_results))
        checks.append(self._check_non_dev_length_results_unchanged(results))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_hook_calculations(results))
        checks.append(self._check_no_cut_length_calculations(results))
        checks.append(self._check_no_lap_calculations(results))
        checks.append(self._check_no_weight_calculations(results))
        checks.append(self._check_export_consistency(model, dev_records))
        checks.append(self._check_registry_lookup_integrity(dev_records))
        checks.append(self._check_engine_name_for_calculated(dev_results))
        checks.append(self._check_result_status_success_for_calculated(dev_results))
        checks.append(self._check_diameter_in_inputs(dev_results))
        checks.append(self._check_steel_grade_in_inputs(dev_results))
        checks.append(self._check_concrete_grade_in_inputs(dev_results))
        checks.append(self._check_calculated_metadata_present(dev_results))
        checks.append(self._check_metadata_matches_result_value(dev_results))
        checks.append(self._check_metadata_lookup_path_consistency(dev_results))
        checks.append(self._check_metadata_normalized_grade_correct(dev_results))
        checks.append(self._check_metadata_source_table_consistency(dev_results))
        checks.append(self._check_deferred_blocked_no_metadata(dev_results))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.3",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "dev_length_result_count": len(dev_results),
                "determination_count": len(dev_records),
            },
        }

    @staticmethod
    def _check_every_dev_length_result_has_record(dev_results: list, dev_records: list) -> dict[str, Any]:
        result_ids = {item.get("result_id") for item in dev_results}
        covered = {item.get("result_id") for item in dev_records}
        missing = sorted(result_ids - covered)
        return {
            "name": "Every Development Length Result Has Record",
            "status": "PASS" if dev_results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_ready_result_evaluated(dev_results: list) -> dict[str, Any]:
        pending = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.READY.value
        ]
        return {
            "name": "Every READY Result Evaluated",
            "status": "PASS" if not pending else "FAIL",
            "pending_count": len(pending),
        }

    @staticmethod
    def _check_deferred_results_unchanged(dev_results: list, bars: list) -> dict[str, Any]:
        bar_map = {item.get("bar_id"): item for item in bars}
        invalid = []
        for result in dev_results:
            if result.get("calculation_state") != CalculationResultState.DEFERRED.value:
                continue
            bar = bar_map.get(result.get("input_bar_id"), {})
            readiness = bar.get("calculation_readiness") or {}
            if readiness.get("calculation_state") != CalculationState.DEFERRED.value:
                invalid.append(result.get("result_id"))
            elif result.get("result_value") is not None:
                invalid.append(result.get("result_id"))
            elif result.get("calculation_inputs"):
                invalid.append(result.get("result_id"))
        return {
            "name": "DEFERRED Results Unchanged",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_development_length_resolved(dev_records: list) -> dict[str, Any]:
        missing = [
            item.get("dev_length_id")
            for item in dev_records
            if item.get("determination_state") == DevelopmentLengthState.CALCULATED.value
            and item.get("development_length_mm") is None
        ]
        return {
            "name": "Development Length Resolved",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_engineering_rule_cache_referenced(dev_records: list) -> dict[str, Any]:
        calculated = [
            item for item in dev_records
            if item.get("determination_state") == DevelopmentLengthState.CALCULATED.value
        ]
        with_table = [
            item for item in calculated if item.get("development_length_table")
        ]
        ok = not calculated or len(with_table) == len(calculated)
        return {
            "name": "Engineering Rule Cache Used",
            "status": "PASS" if ok else "FAIL",
            "calculated_count": len(calculated),
            "with_table_count": len(with_table),
        }

    @staticmethod
    def _check_calculated_inputs_populated(dev_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_inputs")
        ]
        return {
            "name": "Engineering Inputs Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_value_populated(dev_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") is None
        ]
        return {
            "name": "Result Value Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_unit_mm(dev_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "mm"
        ]
        return {
            "name": "Result Unit Is mm",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_trace_exists(dev_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {
            "name": "Calculation Trace Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_registry_integrity(registry: dict, dev_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_DEV_LENGTH
            and registry.get("determination_count") == len(dev_records)
            and set(registry.get("determination_ids", [])) == {
                item.get("dev_length_id") for item in dev_records
            }
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if dev_records and ok else "FAIL",
            "determination_count": len(dev_records),
        }

    @staticmethod
    def _check_deterministic_dev_length_ids(dev_records: list) -> dict[str, Any]:
        ids = [item.get("dev_length_id") for item in dev_records]
        expected = [f"DEV_LENGTH::{index:06d}" for index in range(1, len(dev_records) + 1)]
        return {
            "name": "Deterministic Development Length IDs",
            "status": "PASS" if ids == expected else "FAIL",
            "record_count": len(dev_records),
        }

    @staticmethod
    def _check_traceability_preserved(dev_records: list) -> dict[str, Any]:
        missing = [
            item.get("dev_length_id")
            for item in dev_records
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if dev_records and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_unique_dev_length_ids(dev_records: list) -> dict[str, Any]:
        ids = [item.get("dev_length_id") for item in dev_records]
        return {
            "name": "Unique Development Length IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, dev_records: list) -> dict[str, Any]:
        ready_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        )
        calculated = sum(
            1
            for item in dev_records
            if item.get("determination_state") == DevelopmentLengthState.CALCULATED.value
        )
        return {
            "name": "CALCULATED Count Matches READY Bars",
            "status": "PASS" if calculated == ready_bars else "FAIL",
            "expected": ready_bars,
            "actual": calculated,
        }

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, dev_records: list) -> dict[str, Any]:
        deferred_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        deferred = sum(
            1
            for item in dev_records
            if item.get("determination_state") == DevelopmentLengthState.DEFERRED.value
        )
        return {
            "name": "DEFERRED Count Matches Deferred Bars",
            "status": "PASS" if deferred == deferred_bars else "FAIL",
            "expected": deferred_bars,
            "actual": deferred,
        }

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, dev_results: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        invalid = [
            item.get("result_id")
            for item in dev_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No CALCULATED For Deferred Readiness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_non_dev_length_results_unchanged(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") != CALCULATION_TYPE
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "Non Development Length Results Unchanged",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_geometry_modified(model: dict[str, Any], contexts: list) -> dict[str, Any]:
        forbidden = {"development_length_mm", "cut_length_mm", "hook_length_mm", "lap_length_mm"}
        invalid = []
        for context in contexts:
            if forbidden.intersection(context.keys()):
                invalid.append(context.get("context_id"))
        for bar in model.get("reinforcement_bars", []):
            if forbidden.intersection(bar.keys()):
                invalid.append(bar.get("bar_id"))
        return {
            "name": "No Geometry Modified",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_hook_calculations(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.HOOK.value
            and item.get("result_value") is not None
        ]
        return {
            "name": "No Hook Calculations",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_cut_length_calculations(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.CUT_LENGTH.value
            and item.get("result_value") is not None
        ]
        return {
            "name": "No Cut Length Calculations",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_lap_calculations(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.LAP_LENGTH.value
            and item.get("result_value") is not None
        ]
        return {
            "name": "No Lap Calculations",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_weight_calculations(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") in {
                CalculationType.STEEL_WEIGHT.value,
                CalculationType.BOQ.value,
            }
            and item.get("result_value") is not None
        ]
        return {
            "name": "No Weight Or BOQ Calculations",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_export_consistency(model: dict[str, Any], dev_records: list) -> dict[str, Any]:
        registry = model.get("development_length_registry", {})
        ok = registry.get("determination_count") == len(dev_records)
        return {
            "name": "Export Consistency",
            "status": "PASS" if dev_records and ok else "FAIL",
            "determination_count": len(dev_records),
        }

    @staticmethod
    def _check_registry_lookup_integrity(dev_records: list) -> dict[str, Any]:
        lookup_registry = DevelopmentLengthRegistry()
        for record in dev_records:
            lookup_registry.register(dict(record))

        calculated = sum(
            1
            for item in dev_records
            if item.get("determination_state") == DevelopmentLengthState.CALCULATED.value
        )
        ok = len(lookup_registry.records_by_state(DevelopmentLengthState.CALCULATED.value)) == calculated
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if dev_records and ok else "FAIL",
            "calculated_count": calculated,
        }

    @staticmethod
    def _check_engine_name_for_calculated(dev_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("engine_name") != ENGINE_NAME
        ]
        return {
            "name": "Engine Name For Calculated Results",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_result_status_success_for_calculated(dev_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_status") != RESULT_STATUS_SUCCESS
        ]
        return {
            "name": "Result Status SUCCESS For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_diameter_in_inputs(dev_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("calculation_inputs") or {}).get("bar_diameter_mm")
        ]
        return {
            "name": "Diameter In Calculation Inputs",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_steel_grade_in_inputs(dev_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("calculation_inputs") or {}).get("steel_grade")
        ]
        return {
            "name": "Steel Grade In Calculation Inputs",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_concrete_grade_in_inputs(dev_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("calculation_inputs") or {}).get("concrete_grade")
        ]
        return {
            "name": "Concrete Grade In Calculation Inputs",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_metadata_present(dev_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("development_length_metadata")
        ]
        return {
            "name": "Calculated Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_metadata_matches_result_value(dev_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("development_length_metadata") or {}).get("value")
            != item.get("result_value")
        ]
        return {
            "name": "Metadata Matches Result Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_metadata_lookup_path_consistency(dev_results: list) -> dict[str, Any]:
        invalid = []
        for item in dev_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            meta = item.get("development_length_metadata") or {}
            inputs = item.get("calculation_inputs") or {}
            path = meta.get("lookup_path") or []
            if len(path) != 4 or path[0] != "development_tables":
                invalid.append(item.get("result_id"))
                continue
            steel = str(inputs.get("steel_grade", ""))
            if path[1] != steel_table_key(steel):
                invalid.append(item.get("result_id"))
            elif path[2] != str(inputs.get("concrete_grade", "")):
                invalid.append(item.get("result_id"))
            elif path[3] != str(int(inputs.get("bar_diameter_mm", 0))):
                invalid.append(item.get("result_id"))
        return {
            "name": "Metadata Lookup Path Consistency",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_metadata_normalized_grade_correct(dev_results: list) -> dict[str, Any]:
        invalid = []
        for item in dev_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            meta = item.get("development_length_metadata") or {}
            steel = str(meta.get("steel_grade", ""))
            normalized = str(meta.get("normalized_steel_grade", ""))
            if normalized != steel_table_key(steel):
                invalid.append(item.get("result_id"))
        return {
            "name": "Metadata Normalized Grade Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_metadata_source_table_consistency(dev_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("development_length_metadata") or {}).get("source_table")
            != (item.get("calculation_inputs") or {}).get("development_length_table")
        ]
        return {
            "name": "Metadata Source Table Consistency",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_blocked_no_metadata(dev_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in dev_results
            if item.get("calculation_state")
            in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }
            and item.get("development_length_metadata")
        ]
        return {
            "name": "Deferred Blocked Results Have No Metadata",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
