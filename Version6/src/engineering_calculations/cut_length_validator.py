"""Validate cut length determinations — Phase I.6."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.cut_length_determiner import cut_length_applied
from src.engineering_calculations.cut_length_registry import CutLengthRegistry
from src.engineering_calculations.cut_length_types import (
    CALCULATION_TYPE,
    ENGINE_NAME,
    NAMESPACE_CUT_LENGTH,
    RULE_SOURCE_GENERAL_NOTES,
    CutLengthState,
)
from src.engineering_calculations.formula_engine.cut_length_formula import (
    CutLengthFormulaEngine,
    CutLengthFormulaInput,
)
from src.engineering_calculations.rule_resolution.cut_length_rule_resolver import (
    CutLengthRuleResolver,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedCutLengthRule
from src.reinforcement_calculation.calculation_state import CalculationState


class CutLengthValidator:
    """Verify cut length determination integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not cut_length_applied(model) and not model.get("cut_length_results"):
            return {
                "phase": "Phase I.6",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "cut length determination not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        cut_records = model.get("cut_length_results", [])
        registry = model.get("cut_length_registry", {})
        contexts = model.get("calculation_contexts", [])
        dependency_graph = model.get("calculation_dependency_graph", {})

        cut_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]
        results_by_id = {
            str(item.get("result_id", "")): item
            for item in results
            if item.get("result_id")
        }
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_cut_result_has_record(cut_results, cut_records))
        checks.append(self._check_every_ready_result_evaluated(cut_results))
        checks.append(self._check_deferred_results_unchanged(cut_results, bars))
        checks.append(self._check_blocked_results_unchanged(cut_results, bars))
        checks.append(self._check_dependency_graph_exists(dependency_graph))
        checks.append(self._check_dependency_graph_consulted(cut_records))
        checks.append(self._check_development_length_available(cut_records, bars, results_by_id))
        checks.append(self._check_hook_length_available(cut_records, bars, results_by_id))
        checks.append(self._check_lap_length_available(cut_records, bars, results_by_id))
        checks.append(self._check_cut_length_resolved(cut_records))
        checks.append(self._check_general_notes_rules_only(cut_records))
        checks.append(self._check_no_estimator_rule_usage(cut_records))
        checks.append(self._check_calculated_inputs_populated(cut_results))
        checks.append(self._check_calculated_result_value_populated(cut_results))
        checks.append(self._check_calculated_result_unit_mm(cut_results))
        checks.append(self._check_calculated_trace_exists(cut_results))
        checks.append(self._check_calculated_metadata_present(cut_results))
        checks.append(self._check_metadata_matches_result_value(cut_results))
        checks.append(self._check_provenance_attached(cut_results))
        checks.append(self._check_provenance_source_ids_valid(cut_results, results_by_id))
        checks.append(self._check_provenance_three_sources(cut_results))
        checks.append(self._check_deferred_blocked_no_metadata(cut_results))
        checks.append(self._check_registry_integrity(registry, cut_records))
        checks.append(self._check_deterministic_cut_length_ids(cut_records))
        checks.append(self._check_unique_cut_length_ids(cut_records))
        checks.append(self._check_traceability_preserved(cut_records))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, cut_records))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, cut_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, cut_results))
        checks.append(self._check_non_cut_results_unchanged(results))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_bbs_generation(results))
        checks.append(self._check_no_quantity_generation(results))
        checks.append(self._check_no_weight_calculation(results))
        checks.append(self._check_export_integrity(registry, cut_records))
        checks.append(self._check_registry_lookup_integrity(cut_records))
        checks.append(self._check_engine_name_for_calculated(cut_results))
        checks.append(self._check_calculation_reproducibility(cut_results))
        checks.append(self._check_statistics_integrity(registry, cut_records))
        checks.append(self._check_formula_engine_isolated())
        checks.append(self._check_rule_resolver_no_mathematics())
        checks.append(self._check_dependency_can_execute_for_calculated(bars, graph, results_by_id))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.6",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "cut_result_count": len(cut_results),
                "determination_count": len(cut_records),
            },
        }

    @staticmethod
    def _check_every_cut_result_has_record(cut_results: list, cut_records: list) -> dict[str, Any]:
        result_ids = {item.get("result_id") for item in cut_results}
        covered = {item.get("result_id") for item in cut_records}
        missing = sorted(result_ids - covered)
        return {
            "name": "Every Cut Result Has Record",
            "status": "PASS" if cut_results and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_ready_result_evaluated(cut_results: list) -> dict[str, Any]:
        ready = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.READY.value
        ]
        return {
            "name": "Every READY Result Evaluated",
            "status": "PASS" if not ready else "FAIL",
            "ready_count": len(ready),
        }

    @staticmethod
    def _check_deferred_results_unchanged(cut_results: list, bars: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        changed = [
            item.get("result_id")
            for item in cut_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") != CalculationResultState.DEFERRED.value
        ]
        return {
            "name": "Deferred Results Unchanged",
            "status": "PASS" if not changed else "FAIL",
            "changed_count": len(changed),
        }

    @staticmethod
    def _check_blocked_results_unchanged(cut_results: list, bars: list) -> dict[str, Any]:
        blocked_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.BLOCKED.value
        }
        changed = [
            item.get("result_id")
            for item in cut_results
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
    def _check_dependency_graph_consulted(cut_records: list) -> dict[str, Any]:
        missing = [
            item.get("cut_length_id")
            for item in cut_records
            if item.get("determination_state") == CutLengthState.CALCULATED.value
            and not item.get("dependency_graph_consulted")
        ]
        return {
            "name": "Dependency Graph Consulted",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_prerequisite_available(
        cut_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
        category: str,
        check_name: str,
    ) -> dict[str, Any]:
        bar_by_id = {bar.get("bar_id"): bar for bar in bars}
        invalid = []
        for record in cut_records:
            if record.get("determination_state") != CutLengthState.CALCULATED.value:
                continue
            bar = bar_by_id.get(record.get("bar_id"), {})
            references = (bar.get("calculation_index") or {}).get("references") or {}
            result_id = references.get(category)
            result = results_by_id.get(str(result_id))
            if not result or result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                invalid.append(record.get("cut_length_id"))
        return {
            "name": check_name,
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    def _check_development_length_available(
        self,
        cut_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return self._check_prerequisite_available(
            cut_records,
            bars,
            results_by_id,
            "DEVELOPMENT_LENGTH",
            "Development Length Available",
        )

    def _check_hook_length_available(
        self,
        cut_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return self._check_prerequisite_available(
            cut_records,
            bars,
            results_by_id,
            "HOOK_LENGTH",
            "Hook Length Available",
        )

    def _check_lap_length_available(
        self,
        cut_records: list,
        bars: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return self._check_prerequisite_available(
            cut_records,
            bars,
            results_by_id,
            "LAP_LENGTH",
            "Lap Length Available",
        )

    @staticmethod
    def _check_cut_length_resolved(cut_records: list) -> dict[str, Any]:
        missing = [
            item.get("cut_length_id")
            for item in cut_records
            if item.get("determination_state") == CutLengthState.CALCULATED.value
            and item.get("cut_length_mm") is None
        ]
        return {
            "name": "Cut Length Resolved",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_general_notes_rules_only(cut_records: list) -> dict[str, Any]:
        invalid = [
            item.get("cut_length_id")
            for item in cut_records
            if item.get("determination_state") == CutLengthState.CALCULATED.value
            and item.get("cut_rule_source") not in {
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
    def _check_no_estimator_rule_usage(cut_records: list) -> dict[str, Any]:
        invalid = [
            item.get("cut_length_id")
            for item in cut_records
            if "ESTIMATOR" in str(item.get("cut_rule_source", "")).upper()
        ]
        return {
            "name": "Estimator Rules Never Used",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_inputs_populated(cut_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_inputs")
        ]
        return {
            "name": "Engineering Inputs Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_value_populated(cut_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") is None
        ]
        return {
            "name": "Result Value Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_unit_mm(cut_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "mm"
        ]
        return {
            "name": "Result Unit Is mm",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_trace_exists(cut_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {
            "name": "Calculation Trace Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_metadata_present(cut_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("cut_length_metadata")
        ]
        return {
            "name": "Cut Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_metadata_matches_result_value(cut_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and (item.get("cut_length_metadata") or {}).get("value") != item.get("result_value")
        ]
        return {
            "name": "Metadata Matches Result Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_attached(cut_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in cut_results
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
        cut_results: list,
        results_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        invalid = []
        for item in cut_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            for source in (item.get("calculation_provenance") or {}).get("sources", []):
                if str(source.get("result_id", "")) not in results_by_id:
                    invalid.append(item.get("result_id"))
        return {
            "name": "Provenance Source IDs Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_three_sources(cut_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and len((item.get("calculation_provenance") or {}).get("sources", [])) != 3
        ]
        return {
            "name": "Provenance References Three Sources",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_blocked_no_metadata(cut_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state")
            in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }
            and item.get("cut_length_metadata")
        ]
        return {
            "name": "Deferred Blocked Results Have No Metadata",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(registry: dict, cut_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_CUT_LENGTH
            and registry.get("determination_count") == len(cut_records)
            and set(registry.get("determination_ids", [])) == {
                item.get("cut_length_id") for item in cut_records
            }
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if cut_records and ok else "FAIL",
            "determination_count": len(cut_records),
        }

    @staticmethod
    def _check_deterministic_cut_length_ids(cut_records: list) -> dict[str, Any]:
        ids = [item.get("cut_length_id") for item in cut_records]
        expected = [f"CUT_LENGTH::{index:06d}" for index in range(1, len(cut_records) + 1)]
        return {
            "name": "Deterministic Cut Length IDs",
            "status": "PASS" if ids == expected else "FAIL",
            "record_count": len(cut_records),
        }

    @staticmethod
    def _check_unique_cut_length_ids(cut_records: list) -> dict[str, Any]:
        ids = [item.get("cut_length_id") for item in cut_records]
        return {
            "name": "Unique Cut Length IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_traceability_preserved(cut_records: list) -> dict[str, Any]:
        missing = [
            item.get("cut_length_id")
            for item in cut_records
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if cut_records and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, cut_records: list) -> dict[str, Any]:
        ready_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        )
        calculated = sum(
            1
            for item in cut_records
            if item.get("determination_state") == CutLengthState.CALCULATED.value
        )
        return {
            "name": "CALCULATED Count Matches READY Bars",
            "status": "PASS" if calculated == ready_bars else "FAIL",
            "expected": ready_bars,
            "actual": calculated,
        }

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, cut_records: list) -> dict[str, Any]:
        deferred_bars = sum(
            1
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        deferred = sum(
            1
            for item in cut_records
            if item.get("determination_state") == CutLengthState.DEFERRED.value
        )
        return {
            "name": "Deferred Count Matches Deferred Bars",
            "status": "PASS" if deferred == deferred_bars else "FAIL",
            "expected": deferred_bars,
            "actual": deferred,
        }

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, cut_results: list) -> dict[str, Any]:
        deferred_bar_ids = {
            bar.get("bar_id")
            for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        invalid = [
            item.get("result_id")
            for item in cut_results
            if item.get("input_bar_id") in deferred_bar_ids
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No Calculated For Deferred Readiness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_non_cut_results_unchanged(results: list) -> dict[str, Any]:
        return {
            "name": "Non Cut Results Present",
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
    def _check_export_integrity(registry: dict, cut_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(cut_records)
        return {
            "name": "Export Integrity",
            "status": "PASS" if cut_records and ok else "FAIL",
            "determination_count": len(cut_records),
        }

    @staticmethod
    def _check_registry_lookup_integrity(cut_records: list) -> dict[str, Any]:
        lookup_registry = CutLengthRegistry()
        for record in cut_records:
            lookup_registry.register(dict(record))
        calculated = sum(
            1
            for item in cut_records
            if item.get("determination_state") == CutLengthState.CALCULATED.value
        )
        ok = len(lookup_registry.records_by_state(CutLengthState.CALCULATED.value)) == calculated
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if cut_records and ok else "FAIL",
            "calculated_count": calculated,
        }

    @staticmethod
    def _check_engine_name_for_calculated(cut_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in cut_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("engine_name") != ENGINE_NAME
        ]
        return {
            "name": "Engine Name For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_reproducibility(cut_results: list) -> dict[str, Any]:
        invalid = []
        for item in cut_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            inputs = item.get("calculation_inputs") or {}
            metadata = item.get("cut_length_metadata") or {}
            rule = ResolvedCutLengthRule(
                span_basis=str(inputs.get("span_basis", "")),
                development_length_end_count=int(inputs.get("development_length_end_count", 0)),
                hook_length_end_count=int(inputs.get("hook_length_end_count", 0)),
                lap_length_adjustment_count=int(inputs.get("lap_length_adjustment_count", 0)),
                rule_source=str(metadata.get("rule_source", "")),
                rule_name=str(metadata.get("rule_name", "")),
                rule_reference=str(metadata.get("rule_reference", "")),
                rule_priority=1,
                structural_code_reference="",
                general_notes_reference="",
                lookup_path=tuple(metadata.get("lookup_path", [])),
                reinforcement_position=str(inputs.get("reinforcement_position", "")),
                reinforcement_role=str(inputs.get("reinforcement_role", "")),
                rule_description="",
                use_effective_span=bool(inputs.get("use_effective_span", False)),
            )
            expected = CutLengthFormulaEngine.evaluate(
                CutLengthFormulaInput(
                    clear_span_mm=int(inputs.get("clear_span_mm", 0)),
                    effective_span_mm=int(inputs.get("effective_span_mm", 0)),
                    development_length_mm=int(inputs.get("development_length_mm", 0)),
                    hook_length_mm=int(inputs.get("hook_length_mm", 0)),
                    lap_length_mm=int(inputs.get("lap_length_mm", 0)),
                    beam_width_mm=int(inputs.get("beam_width_mm", 0)),
                    beam_depth_mm=int(inputs.get("beam_depth_mm", 0)),
                    cover_side_mm=int(inputs.get("cover_side_mm", 0)),
                    resolved_rule=rule,
                )
            )
            if expected != item.get("result_value"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Calculation Reproducibility",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_statistics_integrity(registry: dict, cut_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(cut_records)
        return {
            "name": "Statistics Integrity",
            "status": "PASS" if cut_records and ok else "FAIL",
            "determination_count": len(cut_records),
        }

    @staticmethod
    def _check_formula_engine_isolated() -> dict[str, Any]:
        import inspect

        source = inspect.getsource(CutLengthFormulaEngine)
        forbidden = ("EngineeringRuleCache", "general_notes", "fabrication_rules", "anchorage_rules", "RuleResolver")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Formula Engine Isolated",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_rule_resolver_no_mathematics() -> dict[str, Any]:
        import inspect

        source = inspect.getsource(CutLengthRuleResolver)
        forbidden = ("round(", "max(", "min(", "development_length_mm *", "hook_length_mm *")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Rule Resolver Performs No Mathematics",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
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
            if not graph.can_execute("CUT_LENGTH", bar, results_by_id):
                invalid.append(bar.get("bar_id"))
        return {
            "name": "Dependency Can Execute For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
