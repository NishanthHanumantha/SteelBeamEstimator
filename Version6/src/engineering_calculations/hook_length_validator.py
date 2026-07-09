"""Validate hook length determinations — Phase I.4."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.hook_length_determiner import hook_length_applied
from src.engineering_calculations.hook_length_registry import HookLengthRegistry
from src.engineering_calculations.hook_length_types import (
    CALCULATION_TYPE,
    ENGINE_NAME,
    NAMESPACE_HOOK_LENGTH,
    RESULT_STATUS_SUCCESS,
    RULE_SOURCE_GENERAL_NOTES,
    HookLengthState,
)
from src.reinforcement_calculation.calculation_state import CalculationState


class HookLengthValidator:
    """Verify hook length determination integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not hook_length_applied(model) and not model.get("hook_length_results"):
            return {
                "phase": "Phase I.4",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "hook length determination not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        hook_records = model.get("hook_length_results", [])
        registry = model.get("hook_length_registry", {})
        contexts = model.get("calculation_contexts", [])

        hook_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_hook_result_has_record(hook_results, hook_records))
        checks.append(self._check_every_ready_result_evaluated(hook_results))
        checks.append(self._check_deferred_results_unchanged(hook_results, bars))
        checks.append(self._check_blocked_results_unchanged(hook_results, bars))
        checks.append(self._check_hook_length_resolved(hook_records))
        checks.append(self._check_general_notes_rules_only(hook_records))
        checks.append(self._check_no_estimator_rule_usage(hook_records))
        checks.append(self._check_calculated_inputs_populated(hook_results))
        checks.append(self._check_calculated_result_value_populated(hook_results))
        checks.append(self._check_calculated_result_unit_mm(hook_results))
        checks.append(self._check_calculated_trace_exists(hook_results))
        checks.append(self._check_calculated_metadata_present(hook_results))
        checks.append(self._check_metadata_matches_result_value(hook_results))
        checks.append(self._check_metadata_multiplier_consistency(hook_results))
        checks.append(self._check_deferred_blocked_no_metadata(hook_results))
        checks.append(self._check_registry_integrity(registry, hook_records))
        checks.append(self._check_deterministic_hook_length_ids(hook_records))
        checks.append(self._check_unique_hook_length_ids(hook_records))
        checks.append(self._check_traceability_preserved(hook_records))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, hook_records))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, hook_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, hook_results))
        checks.append(self._check_non_hook_results_unchanged(results))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_cut_length_calculations(results))
        checks.append(self._check_no_lap_calculations(results))
        checks.append(self._check_no_weight_calculations(results))
        checks.append(self._check_export_consistency(model, hook_records))
        checks.append(self._check_registry_lookup_integrity(hook_records))
        checks.append(self._check_engine_name_for_calculated(hook_results))
        checks.append(self._check_calculation_reproducibility(hook_results))
        checks.append(self._check_statistics_integrity(model))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.4",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "hook_result_count": len(hook_results),
                "determination_count": len(hook_records),
            },
        }

    @staticmethod
    def _check_every_hook_result_has_record(hook_results: list, hook_records: list) -> dict[str, Any]:
        result_ids = {item.get("result_id") for item in hook_results}
        covered = {item.get("result_id") for item in hook_records}
        missing = sorted(result_ids - covered)
        return {
            "name": "Every Hook Result Has Record",
            "status": "PASS" if hook_results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_ready_result_evaluated(hook_results: list) -> dict[str, Any]:
        pending = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state") == CalculationResultState.READY.value
        ]
        return {
            "name": "Every READY Result Evaluated",
            "status": "PASS" if not pending else "FAIL",
            "pending_count": len(pending),
        }

    @staticmethod
    def _check_deferred_results_unchanged(hook_results: list, bars: list) -> dict[str, Any]:
        bar_map = {item.get("bar_id"): item for item in bars}
        invalid = []
        for result in hook_results:
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
            "name": "DEFERRED Results Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_blocked_results_unchanged(hook_results: list, bars: list) -> dict[str, Any]:
        bar_map = {item.get("bar_id"): item for item in bars}
        invalid = [
            result.get("result_id")
            for result in hook_results
            if result.get("calculation_state") == CalculationResultState.BLOCKED.value
            and (result.get("result_value") is not None or result.get("hook_metadata"))
        ]
        return {
            "name": "BLOCKED Results Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_hook_length_resolved(hook_records: list) -> dict[str, Any]:
        missing = [
            item.get("hook_length_id")
            for item in hook_records
            if item.get("determination_state") == HookLengthState.CALCULATED.value
            and item.get("hook_length_mm") is None
        ]
        return {
            "name": "Hook Length Resolved",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_general_notes_rules_only(hook_records: list) -> dict[str, Any]:
        calculated = [
            item for item in hook_records
            if item.get("determination_state") == HookLengthState.CALCULATED.value
        ]
        invalid = [
            item.get("hook_length_id")
            for item in calculated
            if str(item.get("hook_rule_source", "")).upper() != RULE_SOURCE_GENERAL_NOTES
        ]
        return {
            "name": "General Notes Rules Only",
            "status": "PASS" if calculated and not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_estimator_rule_usage(hook_records: list) -> dict[str, Any]:
        invalid = [
            item.get("hook_length_id")
            for item in hook_records
            if "ESTIMATOR" in str(item.get("hook_rule_source", "")).upper()
        ]
        return {
            "name": "No Estimator Rule Usage",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_inputs_populated(hook_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_inputs")
        ]
        return {
            "name": "Engineering Inputs Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_value_populated(hook_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") is None
        ]
        return {
            "name": "Result Value Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_unit_mm(hook_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "mm"
        ]
        return {
            "name": "Result Unit Is mm",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_trace_exists(hook_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {
            "name": "Calculation Trace Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_metadata_present(hook_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("hook_metadata")
        ]
        return {
            "name": "Hook Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_metadata_matches_result_value(hook_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("hook_metadata") or {}).get("value") != item.get("result_value")
        ]
        return {
            "name": "Metadata Matches Result Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_metadata_multiplier_consistency(hook_results: list) -> dict[str, Any]:
        invalid = []
        for item in hook_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            meta = item.get("hook_metadata") or {}
            inputs = item.get("calculation_inputs") or {}
            multiplier = int(meta.get("multiplier", 0))
            diameter = int(meta.get("diameter_mm", 0))
            expected = multiplier * diameter
            if expected != item.get("result_value"):
                invalid.append(item.get("result_id"))
            elif multiplier != inputs.get("hook_multiplier"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Metadata Multiplier Consistency",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_blocked_no_metadata(hook_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state")
            in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }
            and item.get("hook_metadata")
        ]
        return {
            "name": "Deferred Blocked Results Have No Metadata",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(registry: dict, hook_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_HOOK_LENGTH
            and registry.get("determination_count") == len(hook_records)
            and set(registry.get("determination_ids", [])) == {
                item.get("hook_length_id") for item in hook_records
            }
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if hook_records and ok else "FAIL",
            "determination_count": len(hook_records),
        }

    @staticmethod
    def _check_deterministic_hook_length_ids(hook_records: list) -> dict[str, Any]:
        ids = [item.get("hook_length_id") for item in hook_records]
        expected = [f"HOOK_LENGTH::{index:06d}" for index in range(1, len(hook_records) + 1)]
        return {
            "name": "Deterministic Hook Length IDs",
            "status": "PASS" if ids == expected else "FAIL",
            "record_count": len(hook_records),
        }

    @staticmethod
    def _check_unique_hook_length_ids(hook_records: list) -> dict[str, Any]:
        ids = [item.get("hook_length_id") for item in hook_records]
        return {
            "name": "Unique Hook Length IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_traceability_preserved(hook_records: list) -> dict[str, Any]:
        missing = [
            item.get("hook_length_id")
            for item in hook_records
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if hook_records and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, hook_records: list) -> dict[str, Any]:
        ready_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        )
        calculated = sum(
            1
            for item in hook_records
            if item.get("determination_state") == HookLengthState.CALCULATED.value
        )
        return {
            "name": "CALCULATED Count Matches READY Bars",
            "status": "PASS" if calculated == ready_bars else "FAIL",
            "expected": ready_bars,
            "actual": calculated,
        }

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, hook_records: list) -> dict[str, Any]:
        deferred_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        deferred = sum(
            1
            for item in hook_records
            if item.get("determination_state") == HookLengthState.DEFERRED.value
        )
        return {
            "name": "DEFERRED Count Matches Deferred Bars",
            "status": "PASS" if deferred == deferred_bars else "FAIL",
            "expected": deferred_bars,
            "actual": deferred,
        }

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, hook_results: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        invalid = [
            item.get("result_id")
            for item in hook_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No CALCULATED For Deferred Readiness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_non_hook_results_unchanged(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") not in {CALCULATION_TYPE, CalculationType.DEVELOPMENT_LENGTH.value}
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "Non Hook Results Unchanged Except Development Length",
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
                CalculationType.BAR_SCHEDULE.value,
            }
            and item.get("result_value") is not None
        ]
        return {
            "name": "No Weight BBS Or Quantity Calculations",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_export_consistency(model: dict[str, Any], hook_records: list) -> dict[str, Any]:
        registry = model.get("hook_length_registry", {})
        ok = registry.get("determination_count") == len(hook_records)
        return {
            "name": "Export Integrity",
            "status": "PASS" if hook_records and ok else "FAIL",
            "determination_count": len(hook_records),
        }

    @staticmethod
    def _check_registry_lookup_integrity(hook_records: list) -> dict[str, Any]:
        lookup_registry = HookLengthRegistry()
        for record in hook_records:
            lookup_registry.register(dict(record))

        calculated = sum(
            1
            for item in hook_records
            if item.get("determination_state") == HookLengthState.CALCULATED.value
        )
        ok = len(lookup_registry.records_by_state(HookLengthState.CALCULATED.value)) == calculated
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if hook_records and ok else "FAIL",
            "calculated_count": calculated,
        }

    @staticmethod
    def _check_engine_name_for_calculated(hook_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in hook_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("engine_name") != ENGINE_NAME
        ]
        return {
            "name": "Engine Name For Calculated Results",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_reproducibility(hook_results: list) -> dict[str, Any]:
        invalid = []
        for item in hook_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            inputs = item.get("calculation_inputs") or {}
            multiplier = int(inputs.get("hook_multiplier", 0))
            diameter = int(inputs.get("bar_diameter_mm", 0))
            if multiplier * diameter != item.get("result_value"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Calculation Reproducibility",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_statistics_integrity(model: dict[str, Any]) -> dict[str, Any]:
        registry = model.get("hook_length_registry", {})
        records = model.get("hook_length_results", [])
        ok = registry.get("determination_count") == len(records)
        return {
            "name": "Statistics Integrity",
            "status": "PASS" if records and ok else "FAIL",
            "determination_count": len(records),
        }
