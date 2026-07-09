"""Validate lap length determinations — Phase I.5."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.lap_length_determiner import lap_length_applied
from src.engineering_calculations.lap_length_registry import LapLengthRegistry
from src.engineering_calculations.lap_length_types import (
    CALCULATION_TYPE,
    ENGINE_NAME,
    NAMESPACE_LAP_LENGTH,
    RESULT_STATUS_SUCCESS,
    RULE_SOURCE_GENERAL_NOTES,
    LapLengthState,
)
from src.reinforcement_calculation.calculation_state import CalculationState


class LapLengthValidator:
    """Verify lap length determination integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not lap_length_applied(model) and not model.get("lap_length_results"):
            return {
                "phase": "Phase I.5",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "lap length determination not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        lap_records = model.get("lap_length_results", [])
        registry = model.get("lap_length_registry", {})
        contexts = model.get("calculation_contexts", [])
        dependency_graph = model.get("calculation_dependency_graph", {})

        lap_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]
        results_by_id = {
            str(item.get("result_id", "")): item
            for item in results
            if item.get("result_id")
        }
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_lap_result_has_record(lap_results, lap_records))
        checks.append(self._check_every_ready_result_evaluated(lap_results))
        checks.append(self._check_deferred_results_unchanged(lap_results, bars))
        checks.append(self._check_blocked_results_unchanged(lap_results, bars))
        checks.append(self._check_dependency_graph_exists(dependency_graph))
        checks.append(self._check_dependency_graph_consulted(lap_records))
        checks.append(self._check_development_length_exists_before_lap(lap_records, bars, results_by_id))
        checks.append(self._check_lap_length_resolved(lap_records))
        checks.append(self._check_general_notes_rules_only(lap_records))
        checks.append(self._check_no_estimator_rule_usage(lap_records))
        checks.append(self._check_calculated_inputs_populated(lap_results))
        checks.append(self._check_calculated_result_value_populated(lap_results))
        checks.append(self._check_calculated_result_unit_mm(lap_results))
        checks.append(self._check_calculated_trace_exists(lap_results))
        checks.append(self._check_calculated_metadata_present(lap_results))
        checks.append(self._check_metadata_matches_result_value(lap_results))
        checks.append(self._check_metadata_lap_factor_consistency(lap_results))
        checks.append(self._check_deferred_blocked_no_metadata(lap_results))
        checks.append(self._check_registry_integrity(registry, lap_records))
        checks.append(self._check_deterministic_lap_length_ids(lap_records))
        checks.append(self._check_unique_lap_length_ids(lap_records))
        checks.append(self._check_traceability_preserved(lap_records))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, lap_records))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, lap_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, lap_results))
        checks.append(self._check_non_lap_results_unchanged(results))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_cut_length_calculations(results))
        checks.append(self._check_no_weight_calculations(results))
        checks.append(self._check_no_bbs_calculations(results))
        checks.append(self._check_export_consistency(model, lap_records))
        checks.append(self._check_registry_lookup_integrity(lap_records))
        checks.append(self._check_engine_name_for_calculated(lap_results))
        checks.append(self._check_calculation_reproducibility(lap_results))
        checks.append(self._check_statistics_integrity(model))
        checks.append(self._check_dependency_can_execute_for_calculated(bars, graph, results_by_id))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.5",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "lap_result_count": len(lap_results),
                "determination_count": len(lap_records),
            },
        }

    @staticmethod
    def _check_every_lap_result_has_record(lap_results: list, lap_records: list) -> dict[str, Any]:
        result_ids = {item.get("result_id") for item in lap_results}
        covered = {item.get("result_id") for item in lap_records}
        missing = sorted(result_ids - covered)
        return {
            "name": "Every Lap Result Has Record",
            "status": "PASS" if lap_results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_ready_result_evaluated(lap_results: list) -> dict[str, Any]:
        ready = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state") == CalculationResultState.READY.value
        ]
        return {
            "name": "Every READY Result Evaluated",
            "status": "PASS" if not ready else "FAIL",
            "ready_count": len(ready),
        }

    @staticmethod
    def _check_deferred_results_unchanged(lap_results: list, bars: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        changed = [
            item.get("result_id")
            for item in lap_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") != CalculationResultState.DEFERRED.value
        ]
        return {
            "name": "Deferred Results Unchanged",
            "status": "PASS" if not changed else "FAIL",
            "changed_count": len(changed),
        }

    @staticmethod
    def _check_blocked_results_unchanged(lap_results: list, bars: list) -> dict[str, Any]:
        blocked_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.BLOCKED.value
        }
        changed = [
            item.get("result_id")
            for item in lap_results
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
    def _check_dependency_graph_consulted(lap_records: list) -> dict[str, Any]:
        calculated = [
            item.get("lap_length_id")
            for item in lap_records
            if item.get("determination_state") == LapLengthState.CALCULATED.value
            and not item.get("dependency_graph_consulted")
        ]
        return {
            "name": "Dependency Graph Consulted",
            "status": "PASS" if not calculated else "FAIL",
            "missing_count": len(calculated),
        }

    @staticmethod
    def _check_development_length_exists_before_lap(
        lap_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        bar_by_id = {bar.get("bar_id"): bar for bar in bars}
        invalid = []
        for record in lap_records:
            if record.get("determination_state") != LapLengthState.CALCULATED.value:
                continue
            bar = bar_by_id.get(record.get("bar_id"), {})
            references = (bar.get("calculation_index") or {}).get("references") or {}
            dev_id = references.get("DEVELOPMENT_LENGTH")
            dev_result = results_by_id.get(str(dev_id))
            if not dev_result or dev_result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                invalid.append(record.get("lap_length_id"))
        return {
            "name": "Development Length Exists Before Lap",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_lap_length_resolved(lap_records: list) -> dict[str, Any]:
        missing = [
            item.get("lap_length_id")
            for item in lap_records
            if item.get("determination_state") == LapLengthState.CALCULATED.value
            and item.get("lap_length_mm") is None
        ]
        return {
            "name": "Lap Length Resolved",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_general_notes_rules_only(lap_records: list) -> dict[str, Any]:
        invalid = [
            item.get("lap_length_id")
            for item in lap_records
            if item.get("determination_state") == LapLengthState.CALCULATED.value
            and item.get("lap_rule_source") not in {
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
    def _check_no_estimator_rule_usage(lap_records: list) -> dict[str, Any]:
        invalid = [
            item.get("lap_length_id")
            for item in lap_records
            if "ESTIMATOR" in str(item.get("lap_rule_source", "")).upper()
        ]
        return {
            "name": "Estimator Rules Never Used",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_inputs_populated(lap_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_inputs")
        ]
        return {
            "name": "Engineering Inputs Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_value_populated(lap_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") is None
        ]
        return {
            "name": "Result Value Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_unit_mm(lap_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "mm"
        ]
        return {
            "name": "Result Unit Is mm",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_trace_exists(lap_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {
            "name": "Calculation Trace Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_metadata_present(lap_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("lap_length_metadata")
        ]
        return {
            "name": "Lap Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_metadata_matches_result_value(lap_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("lap_length_metadata") or {}).get("value") != item.get("result_value")
        ]
        return {
            "name": "Metadata Matches Result Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_metadata_lap_factor_consistency(lap_results: list) -> dict[str, Any]:
        invalid = []
        for item in lap_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            meta = item.get("lap_length_metadata") or {}
            inputs = item.get("calculation_inputs") or {}
            development_length = int(meta.get("development_length", 0))
            lap_factor = float(meta.get("lap_factor", 0))
            minimum_lap = int(meta.get("minimum_lap_mm", 0))
            expected = max(int(round(development_length * lap_factor)), minimum_lap)
            if expected != item.get("result_value"):
                invalid.append(item.get("result_id"))
            elif lap_factor != inputs.get("lap_factor"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Metadata Lap Factor Consistency",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_blocked_no_metadata(lap_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state")
            in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }
            and item.get("lap_length_metadata")
        ]
        return {
            "name": "Deferred Blocked Results Have No Metadata",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(registry: dict, lap_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_LAP_LENGTH
            and registry.get("determination_count") == len(lap_records)
            and set(registry.get("determination_ids", [])) == {
                item.get("lap_length_id") for item in lap_records
            }
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if lap_records and ok else "FAIL",
            "determination_count": len(lap_records),
        }

    @staticmethod
    def _check_deterministic_lap_length_ids(lap_records: list) -> dict[str, Any]:
        ids = [item.get("lap_length_id") for item in lap_records]
        expected = [f"LAP_LENGTH::{index:06d}" for index in range(1, len(lap_records) + 1)]
        return {
            "name": "Deterministic Lap Length IDs",
            "status": "PASS" if ids == expected else "FAIL",
            "record_count": len(lap_records),
        }

    @staticmethod
    def _check_unique_lap_length_ids(lap_records: list) -> dict[str, Any]:
        ids = [item.get("lap_length_id") for item in lap_records]
        return {
            "name": "Unique Lap Length IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_traceability_preserved(lap_records: list) -> dict[str, Any]:
        missing = [
            item.get("lap_length_id")
            for item in lap_records
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if lap_records and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, lap_records: list) -> dict[str, Any]:
        ready_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        )
        calculated = sum(
            1
            for item in lap_records
            if item.get("determination_state") == LapLengthState.CALCULATED.value
        )
        return {
            "name": "CALCULATED Count Matches READY Bars",
            "status": "PASS" if calculated == ready_bars else "FAIL",
            "expected": ready_bars,
            "actual": calculated,
        }

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, lap_records: list) -> dict[str, Any]:
        deferred_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        deferred = sum(
            1
            for item in lap_records
            if item.get("determination_state") == LapLengthState.DEFERRED.value
        )
        return {
            "name": "Deferred Count Matches Deferred Bars",
            "status": "PASS" if deferred == deferred_bars else "FAIL",
            "expected": deferred_bars,
            "actual": deferred,
        }

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, lap_results: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        invalid = [
            item.get("result_id")
            for item in lap_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No Calculated For Deferred Readiness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_non_lap_results_unchanged(results: list) -> dict[str, Any]:
        return {
            "name": "Non Lap Results Present",
            "status": "PASS" if any(item.get("calculation_type") != CALCULATION_TYPE for item in results) else "FAIL",
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
            "name": "No Weight Calculations",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_bbs_calculations(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.BAR_SCHEDULE.value
            and item.get("result_value") is not None
        ]
        return {
            "name": "No BBS Calculations",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_export_consistency(model: dict[str, Any], lap_records: list) -> dict[str, Any]:
        registry = model.get("lap_length_registry", {})
        ok = registry.get("determination_count") == len(lap_records)
        return {
            "name": "Export Integrity",
            "status": "PASS" if lap_records and ok else "FAIL",
            "determination_count": len(lap_records),
        }

    @staticmethod
    def _check_registry_lookup_integrity(lap_records: list) -> dict[str, Any]:
        lookup_registry = LapLengthRegistry()
        for record in lap_records:
            lookup_registry.register(dict(record))

        calculated = sum(
            1
            for item in lap_records
            if item.get("determination_state") == LapLengthState.CALCULATED.value
        )
        ok = len(lookup_registry.records_by_state(LapLengthState.CALCULATED.value)) == calculated
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if lap_records and ok else "FAIL",
            "calculated_count": calculated,
        }

    @staticmethod
    def _check_engine_name_for_calculated(lap_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in lap_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("engine_name") != ENGINE_NAME
        ]
        return {
            "name": "Engine Name For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_reproducibility(lap_results: list) -> dict[str, Any]:
        invalid = []
        for item in lap_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            inputs = item.get("calculation_inputs") or {}
            development_length = int(inputs.get("development_length_mm", 0))
            lap_factor = float(inputs.get("lap_factor", 0))
            minimum_lap = int(inputs.get("minimum_lap_mm", 0))
            expected = max(int(round(development_length * lap_factor)), minimum_lap)
            if expected != item.get("result_value"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Calculation Reproducibility",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_statistics_integrity(model: dict[str, Any]) -> dict[str, Any]:
        registry = model.get("lap_length_registry", {})
        records = model.get("lap_length_results", [])
        ok = registry.get("determination_count") == len(records)
        return {
            "name": "Statistics Integrity",
            "status": "PASS" if records and ok else "FAIL",
            "determination_count": len(records),
        }

    @staticmethod
    def _check_dependency_can_execute_for_calculated(
        bars: list,
        graph: CalculationDependencyGraph,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        invalid = []
        for bar in bars:
            if (bar.get("calculation_readiness") or {}).get("calculation_state") != CalculationState.READY.value:
                continue
            if not graph.can_execute("LAP_LENGTH", bar, results_by_id):
                invalid.append(bar.get("bar_id"))
        return {
            "name": "Dependency Can Execute For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
