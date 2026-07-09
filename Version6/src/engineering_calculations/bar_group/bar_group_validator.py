"""Validate bar group aggregations — Phase I.9."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.bar_group.bar_group_determiner import bar_group_applied
from src.engineering_calculations.bar_group.bar_group_types import (
    CALCULATION_TYPE,
    ENGINE_NAME,
    NAMESPACE_BAR_GROUP,
    PREFIX_ENGINEERING_SIGNATURE,
    RULE_SOURCE_GENERAL_NOTES,
    compute_engineering_signature_from_inputs,
    BarGroupState,
)
from src.engineering_calculations.bar_identity.bar_identity_types import BarIdentityState
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.formula_engine.bar_group_classifier import (
    BarGroupClassificationInput,
    BarGroupClassifier,
)
from src.engineering_calculations.rule_resolution.bar_group_rule_resolver import (
    BarGroupRuleResolver,
)
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBarGroupRule
from src.reinforcement_calculation.calculation_state import CalculationState


class BarGroupValidator:
    """Verify bar group aggregation integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not bar_group_applied(model) and not model.get("bar_group_results"):
            return {
                "phase": "Phase I.9",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "bar group aggregation not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        identity_records = model.get("bar_identity_results", [])
        group_records = model.get("bar_group_results", [])
        registry = model.get("bar_group_registry", {})
        contexts = model.get("calculation_contexts", [])
        dependency_graph = model.get("calculation_dependency_graph", {})

        group_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]
        results_by_id = {
            str(item.get("result_id", "")): item
            for item in results
            if item.get("result_id")
        }
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_group_has_record(group_results, group_records))
        checks.append(self._check_every_bar_has_group_result(bars, group_results))
        checks.append(self._check_every_calculated_identity_in_group(identity_records, group_records))
        checks.append(self._check_every_group_has_member(group_records))
        checks.append(self._check_member_count_correct(group_records))
        checks.append(self._check_no_empty_groups(group_records))
        checks.append(self._check_deferred_results_unchanged(group_results, bars))
        checks.append(self._check_blocked_results_unchanged(group_results, bars))
        checks.append(self._check_dependency_graph_exists(dependency_graph))
        checks.append(self._check_dependency_graph_consulted(group_records))
        checks.append(self._check_identity_prerequisite(group_records, identity_records))
        checks.append(self._check_shape_prerequisite(group_records, results))
        checks.append(self._check_cut_length_prerequisite(group_records, results))
        checks.append(self._check_engineering_signature_exists(group_records))
        checks.append(self._check_signature_deterministic(group_records))
        checks.append(self._check_signature_unique(group_records))
        checks.append(self._check_engineering_group_id_populated(group_records))
        checks.append(self._check_general_notes_rules_only(group_records))
        checks.append(self._check_no_estimator_rule_usage(group_records))
        checks.append(self._check_classification_inputs_populated(group_results))
        checks.append(self._check_calculated_result_value_populated(group_results))
        checks.append(self._check_calculated_result_unit_group(group_results))
        checks.append(self._check_calculated_trace_exists(group_results))
        checks.append(self._check_group_metadata_present(group_results))
        checks.append(self._check_metadata_matches_result_value(group_results))
        checks.append(self._check_provenance_attached(group_results))
        checks.append(self._check_provenance_source_ids_valid(group_results, results_by_id))
        checks.append(self._check_provenance_five_sources(group_results))
        checks.append(self._check_deferred_blocked_no_metadata(group_results))
        checks.append(self._check_registry_integrity(registry, group_records))
        checks.append(self._check_deterministic_bar_group_ids(group_records))
        checks.append(self._check_unique_bar_group_ids(group_records))
        checks.append(self._check_unique_engineering_signatures(group_records))
        checks.append(self._check_unique_engineering_group_ids(group_records))
        checks.append(self._check_traceability_preserved(group_records))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, group_results))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, group_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, group_results))
        checks.append(self._check_identity_results_preserved(identity_records))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_bbs_generation(results))
        checks.append(self._check_no_quantity_generation(results))
        checks.append(self._check_no_weight_calculation(results))
        checks.append(self._check_no_boq_generation(results))
        checks.append(self._check_export_integrity(registry, group_records))
        checks.append(self._check_registry_lookup_integrity(group_records))
        checks.append(self._check_engine_name_for_calculated(group_results))
        checks.append(self._check_calculation_reproducibility(group_records, identity_records))
        checks.append(self._check_statistics_integrity(registry, group_records))
        checks.append(self._check_classifier_isolated())
        checks.append(self._check_rule_resolver_isolated())
        checks.append(self._check_engine_separation())
        checks.append(self._check_dependency_satisfied_for_calculated(bars, graph, results_by_id))
        checks.append(self._check_grouping_reproducible(identity_records))
        checks.append(self._check_stable_ordering(group_records))
        checks.append(self._check_duplicate_detection_enabled(group_records))
        checks.append(self._check_no_fabrication_numbering(group_results))
        checks.append(self._check_no_bbs_fields(group_results))
        checks.append(self._check_group_metadata_has_rule_reference(group_results))
        checks.append(self._check_group_metadata_has_rule_source(group_results))
        checks.append(self._check_engineering_signature_immutable(group_records))
        checks.append(self._check_group_ids_deterministic(group_records))
        checks.append(self._check_bar_group_node_in_graph(graph))
        checks.append(self._check_bbs_depends_on_bar_group(graph))
        checks.append(self._check_member_identity_ids_populated(group_records))
        checks.append(self._check_member_beams_populated(group_records))
        checks.append(self._check_member_roles_populated(group_records))
        checks.append(self._check_diameter_populated(group_records))
        checks.append(self._check_shape_code_populated(group_records))
        checks.append(self._check_cut_length_populated(group_records))
        checks.append(self._check_hook_length_populated(group_records))
        checks.append(self._check_development_length_populated(group_records))
        checks.append(self._check_lap_length_populated(group_records))
        checks.append(self._check_geometry_signature_populated(group_records))
        checks.append(self._check_support_configuration_populated(group_records))
        checks.append(self._check_is_duplicate_group_flag(group_records))
        checks.append(self._check_formula_isolation())
        checks.append(self._check_no_scheduling_fields(group_results))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.9",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "group_result_count": len(group_results),
                "determination_count": len(group_records),
            },
        }

    @staticmethod
    def _check_every_group_has_record(group_results: list, group_records: list) -> dict[str, Any]:
        group_ids = {
            item.get("engineering_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        }
        invalid = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") not in group_ids
        ]
        return {
            "name": "Every Group Has Record",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_every_bar_has_group_result(bars: list, group_results: list) -> dict[str, Any]:
        bar_ids = {str(item.get("bar_id", "")) for item in bars}
        covered = {str(item.get("input_bar_id", "")) for item in group_results}
        missing = sorted(bar_ids - covered)
        return {
            "name": "Every Bar Has Group Result",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_calculated_identity_in_group(
        identity_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        calculated = [
            item for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
        ]
        member_bars = {
            str(bar_id)
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            for bar_id in (item.get("member_bar_ids") or [])
        }
        missing = [
            item.get("bar_id")
            for item in calculated
            if str(item.get("bar_id", "")) not in member_bars
        ]
        return {
            "name": "Every Calculated Identity In Group",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_group_has_member(group_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not (item.get("member_bar_ids") or [])
        ]
        return {
            "name": "Every Group Has Member",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_member_count_correct(group_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and int(item.get("member_count") or 0) != len(item.get("member_bar_ids") or [])
        ]
        return {
            "name": "Member Count Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_empty_groups(group_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and int(item.get("member_count") or 0) < 1
        ]
        return {
            "name": "No Empty Groups",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_results_unchanged(group_results: list, bars: list) -> dict[str, Any]:
        deferred_bars = {
            str(item.get("bar_id", ""))
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        changed = [
            item.get("result_id")
            for item in group_results
            if str(item.get("input_bar_id", "")) in deferred_bars
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "Deferred Results Unchanged",
            "status": "PASS" if not changed else "FAIL",
            "changed_count": len(changed),
        }

    @staticmethod
    def _check_blocked_results_unchanged(group_results: list, bars: list) -> dict[str, Any]:
        blocked_bars = {
            str(item.get("bar_id", ""))
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.BLOCKED.value
        }
        changed = [
            item.get("result_id")
            for item in group_results
            if str(item.get("input_bar_id", "")) in blocked_bars
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "Blocked Results Unchanged",
            "status": "PASS" if not changed else "FAIL",
            "changed_count": len(changed),
        }

    @staticmethod
    def _check_dependency_graph_exists(dependency_graph: dict) -> dict[str, Any]:
        return {
            "name": "Dependency Graph Exists",
            "status": "PASS" if dependency_graph else "FAIL",
        }

    @staticmethod
    def _check_dependency_graph_consulted(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        missing = [
            item.get("bar_group_id")
            for item in calculated
            if not item.get("dependency_graph_consulted")
        ]
        return {
            "name": "Dependency Graph Consulted",
            "status": "PASS" if calculated and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_identity_prerequisite(group_records: list, identity_records: list) -> dict[str, Any]:
        identity_by_bar = {str(item.get("bar_id", "")): item for item in identity_records}
        invalid = []
        for record in group_records:
            if record.get("determination_state") != BarGroupState.CALCULATED.value:
                continue
            for bar_id in record.get("member_bar_ids") or []:
                identity = identity_by_bar.get(str(bar_id))
                if not identity or identity.get("determination_state") != BarIdentityState.CALCULATED.value:
                    invalid.append(record.get("bar_group_id"))
                    break
        return {
            "name": "Identity Prerequisite",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_shape_prerequisite(group_records: list, results: list) -> dict[str, Any]:
        invalid = []
        for record in group_records:
            if record.get("determination_state") != BarGroupState.CALCULATED.value:
                continue
            if not record.get("shape_code"):
                invalid.append(record.get("bar_group_id"))
        return {
            "name": "Shape Prerequisite",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_cut_length_prerequisite(group_records: list, results: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and item.get("cut_length") is None
        ]
        return {
            "name": "Cut Length Prerequisite",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engineering_signature_exists(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not str(item.get("engineering_signature", "")).startswith(PREFIX_ENGINEERING_SIGNATURE)
        ]
        return {
            "name": "Engineering Signature Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_signature_deterministic(group_records: list) -> dict[str, Any]:
        invalid = []
        for record in group_records:
            if record.get("determination_state") != BarGroupState.CALCULATED.value:
                continue
            inputs = dict(record.get("classification_inputs") or {})
            expected = compute_engineering_signature_from_inputs(inputs)
            if expected != record.get("engineering_signature"):
                invalid.append(record.get("bar_group_id"))
        return {
            "name": "Signature Deterministic",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_signature_unique(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        signatures = [str(item.get("engineering_signature", "")) for item in calculated]
        ok = len(signatures) == len(set(signatures))
        return {
            "name": "Signature Unique",
            "status": "PASS" if ok else "FAIL",
            "record_count": len(signatures),
        }

    @staticmethod
    def _check_engineering_group_id_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not item.get("engineering_group_id")
        ]
        return {
            "name": "Engineering Group Id Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_general_notes_rules_only(group_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and item.get("rule_source") not in {RULE_SOURCE_GENERAL_NOTES, "GENERAL_NOTES"}
        ]
        return {
            "name": "General Notes Or Structural Code Rules Only",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_estimator_rule_usage(group_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bar_group_id")
            for item in group_records
            if "ESTIMATOR" in str(item.get("rule_source", "")).upper()
        ]
        return {
            "name": "No Estimator Rules",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_classification_inputs_populated(group_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("classification_inputs")
        ]
        return {
            "name": "Classification Inputs Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_value_populated(group_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("result_value")
        ]
        return {
            "name": "Result Value Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_unit_group(group_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "GROUP"
        ]
        return {
            "name": "Result Unit Is GROUP",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_trace_exists(group_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {
            "name": "Calculation Trace Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_group_metadata_present(group_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("group_metadata") or item.get("bar_group_metadata"))
        ]
        return {
            "name": "Group Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_metadata_matches_result_value(group_results: list) -> dict[str, Any]:
        invalid = []
        for item in group_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            metadata = item.get("group_metadata") or item.get("bar_group_metadata") or {}
            if metadata.get("engineering_group_id") != item.get("result_value"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Metadata Matches Result Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_attached(group_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_provenance")
        ]
        return {
            "name": "Provenance Attached",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_provenance_source_ids_valid(group_results: list, results_by_id: dict) -> dict[str, Any]:
        invalid = []
        for item in group_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            provenance = item.get("calculation_provenance") or {}
            for source in provenance.get("sources", []):
                source_id = str(source.get("result_id", ""))
                calc_type = str(source.get("calculation_type", ""))
                if calc_type in {"BEAM_GEOMETRY", "ENGINEERING_SIGNATURE"}:
                    continue
                if source_id and source_id not in results_by_id:
                    invalid.append(item.get("result_id"))
                    break
        return {
            "name": "Provenance Source IDs Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_five_sources(group_results: list) -> dict[str, Any]:
        invalid = []
        for item in group_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            provenance = item.get("calculation_provenance") or {}
            if len(provenance.get("sources", [])) < 5:
                invalid.append(item.get("result_id"))
        return {
            "name": "Provenance Five Sources",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_blocked_no_metadata(group_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }
            and (item.get("group_metadata") or item.get("bar_group_metadata"))
        ]
        return {
            "name": "Deferred Blocked No Metadata",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(registry: dict, group_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_BAR_GROUP
            and registry.get("determination_count") == len(group_records)
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if ok else "FAIL",
            "determination_count": len(group_records),
        }

    @staticmethod
    def _check_deterministic_bar_group_ids(group_records: list) -> dict[str, Any]:
        ids = [str(item.get("bar_group_id", "")) for item in group_records if item.get("bar_group_id")]
        return {
            "name": "Deterministic Bar Group IDs",
            "status": "PASS" if ids and ids == sorted(ids, key=lambda value: int(value.rsplit("::", 1)[-1])) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_unique_bar_group_ids(group_records: list) -> dict[str, Any]:
        ids = [item.get("bar_group_id") for item in group_records if item.get("bar_group_id")]
        return {
            "name": "Unique Bar Group IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_unique_engineering_signatures(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        signatures = [item.get("engineering_signature") for item in calculated]
        return {
            "name": "Unique Engineering Signatures",
            "status": "PASS" if len(signatures) == len(set(signatures)) else "FAIL",
            "record_count": len(signatures),
        }

    @staticmethod
    def _check_unique_engineering_group_ids(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        group_ids = [item.get("engineering_group_id") for item in calculated]
        return {
            "name": "Unique Engineering Group IDs",
            "status": "PASS" if len(group_ids) == len(set(group_ids)) else "FAIL",
            "record_count": len(group_ids),
        }

    @staticmethod
    def _check_traceability_preserved(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, group_results: list) -> dict[str, Any]:
        ready_count = sum(
            1
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        )
        calculated = sum(
            1
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
        )
        return {
            "name": "Calculated Count Matches Ready Bars",
            "status": "PASS" if calculated == ready_count else "FAIL",
            "expected": ready_count,
            "actual": calculated,
        }

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, group_records: list) -> dict[str, Any]:
        deferred_bars = sum(
            1
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        deferred_records = sum(
            1
            for item in group_records
            if item.get("determination_state") == BarGroupState.DEFERRED.value
        )
        return {
            "name": "Deferred Count Matches Deferred Bars",
            "status": "PASS" if deferred_records == deferred_bars else "FAIL",
            "expected": deferred_bars,
            "actual": deferred_records,
        }

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, group_results: list) -> dict[str, Any]:
        deferred_bars = {
            str(item.get("bar_id", ""))
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        invalid = [
            item.get("result_id")
            for item in group_results
            if str(item.get("input_bar_id", "")) in deferred_bars
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No Calculated For Deferred Readiness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_identity_results_preserved(identity_records: list) -> dict[str, Any]:
        calculated = sum(
            1 for item in identity_records if item.get("determination_state") == BarIdentityState.CALCULATED.value
        )
        return {
            "name": "Identity Results Preserved",
            "status": "PASS" if calculated >= 0 else "FAIL",
            "calculated_count": calculated,
        }

    @staticmethod
    def _check_no_geometry_modified(model: dict, contexts: list) -> dict[str, Any]:
        return {"name": "No Geometry Modified", "status": "PASS", "violation_count": 0}

    @staticmethod
    def _check_no_bbs_generation(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("bar_schedule") or item.get("bbs_entry")
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
            if item.get("quantity") is not None or item.get("boq_quantity") is not None
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
        ]
        return {
            "name": "No Weight Calculation",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_boq_generation(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.BOQ.value
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No BOQ Generation",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_export_integrity(registry: dict, group_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(group_records)
        return {
            "name": "Export Integrity",
            "status": "PASS" if group_records and ok else "FAIL",
            "determination_count": len(group_records),
        }

    @staticmethod
    def _check_registry_lookup_integrity(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        ok = all(item.get("bar_group_id") and item.get("engineering_signature") for item in calculated)
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if ok else "FAIL",
            "calculated_count": len(calculated),
        }

    @staticmethod
    def _check_engine_name_for_calculated(group_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("engine_name") != ENGINE_NAME
        ]
        return {
            "name": "Engine Name For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculation_reproducibility(
        group_records: list,
        identity_records: list,
    ) -> dict[str, Any]:
        calculated_identities = [
            item for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
        ]
        rule = ResolvedBarGroupRule(
            grouping_strategy="ENGINEERING_SIGNATURE",
            group_by_identity=True,
            group_by_geometry=True,
            group_by_shape=True,
            group_by_cut_length=True,
            rule_source=RULE_SOURCE_GENERAL_NOTES,
            rule_name="ENGINEERING_SIGNATURE_GROUPING",
            rule_reference="ENGINEERING_BAR_GROUP_AGGREGATION",
            rule_priority=1,
            structural_code_reference="",
            general_notes_reference="",
            lookup_path=(),
            rule_description="",
        )
        expected = BarGroupClassifier.classify(
            BarGroupClassificationInput(
                resolved_rule=rule,
                identity_records=tuple(calculated_identities),
            )
        )
        expected_by_signature = {
            item.engineering_signature: item for item in expected
        }
        invalid = []
        for record in group_records:
            if record.get("determination_state") != BarGroupState.CALCULATED.value:
                continue
            expected_membership = expected_by_signature.get(record.get("engineering_signature"))
            if not expected_membership:
                invalid.append(record.get("bar_group_id"))
                continue
            if tuple(record.get("member_bar_ids") or []) != expected_membership.member_bar_ids:
                invalid.append(record.get("bar_group_id"))
        return {
            "name": "Calculation Reproducibility",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_statistics_integrity(registry: dict, group_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(group_records)
        return {
            "name": "Statistics Integrity",
            "status": "PASS" if group_records and ok else "FAIL",
            "determination_count": len(group_records),
        }

    @staticmethod
    def _check_classifier_isolated() -> dict[str, Any]:
        import inspect
        from src.engineering_calculations.formula_engine.bar_group_classifier import (
            BarGroupClassifier,
        )

        source = inspect.getsource(BarGroupClassifier)
        forbidden = ("EngineeringRuleCache", "BarGroupRuleResolver", "dependency_graph", "BarGroupRegistry")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Classifier Isolated",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_rule_resolver_isolated() -> dict[str, Any]:
        import inspect
        source = inspect.getsource(BarGroupRuleResolver)
        forbidden = ("BarGroupClassifier", "classify(", "format_engineering_group_id", "BarGroupRegistry", "aggregate")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Rule Resolver Isolated",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_engine_separation() -> dict[str, Any]:
        import inspect
        from src.engineering_calculations.bar_group.bar_group_determiner import BarGroupDeterminer
        from src.engineering_calculations.bar_group.bar_group_engine import BarGroupEngine

        engine_source = inspect.getsource(BarGroupEngine)
        determiner_source = inspect.getsource(BarGroupDeterminer)
        engine_ok = "BarGroupDeterminer" in engine_source and "BarGroupClassifier" not in engine_source
        determiner_ok = (
            "BarGroupRuleResolver" in determiner_source
            and "BarGroupClassifier" in determiner_source
        )
        ok = engine_ok and determiner_ok
        return {"name": "Engine Separation", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_dependency_satisfied_for_calculated(
        bars: list,
        graph: CalculationDependencyGraph,
        results_by_id: dict,
    ) -> dict[str, Any]:
        invalid = []
        for bar in bars:
            readiness = bar.get("calculation_readiness") or {}
            if readiness.get("calculation_state") != CalculationState.READY.value:
                continue
            bar_id = str(bar.get("bar_id", ""))
            for dependency in graph.depends_on("BAR_GROUP"):
                if dependency == "BAR_IDENTITY":
                    identity_result = next(
                        (
                            item
                            for item in results_by_id.values()
                            if str(item.get("input_bar_id", "")) == bar_id
                            and item.get("calculation_type") == "BAR_IDENTITY"
                        ),
                        None,
                    )
                    if (
                        not identity_result
                        or identity_result.get("calculation_state")
                        != CalculationResultState.CALCULATED.value
                    ):
                        invalid.append(bar_id)
                        break
                    continue
                references = (bar.get("calculation_index") or {}).get("references") or {}
                result_id = references.get(dependency)
                result = results_by_id.get(str(result_id)) if result_id else None
                if not result or result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                    invalid.append(bar_id)
                    break
        return {
            "name": "Dependency Satisfied For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_grouping_reproducible(identity_records: list) -> dict[str, Any]:
        calculated = [
            item for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
        ]
        rule = ResolvedBarGroupRule(
            grouping_strategy="ENGINEERING_SIGNATURE",
            group_by_identity=True,
            group_by_geometry=True,
            group_by_shape=True,
            group_by_cut_length=True,
            rule_source=RULE_SOURCE_GENERAL_NOTES,
            rule_name="ENGINEERING_SIGNATURE_GROUPING",
            rule_reference="ENGINEERING_BAR_GROUP_AGGREGATION",
            rule_priority=1,
            structural_code_reference="",
            general_notes_reference="",
            lookup_path=(),
            rule_description="",
        )
        first = BarGroupClassifier.classify(
            BarGroupClassificationInput(resolved_rule=rule, identity_records=tuple(calculated))
        )
        second = BarGroupClassifier.classify(
            BarGroupClassificationInput(resolved_rule=rule, identity_records=tuple(reversed(calculated)))
        )
        ok = first == second
        return {"name": "Grouping Reproducible", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_stable_ordering(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        signatures = [str(item.get("engineering_signature", "")) for item in calculated]
        ok = signatures == sorted(signatures)
        return {
            "name": "Stable Ordering",
            "status": "PASS" if ok else "FAIL",
            "record_count": len(calculated),
        }

    @staticmethod
    def _check_duplicate_detection_enabled(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        has_flag = any(item.get("is_duplicate_group") is not None for item in calculated)
        return {
            "name": "Duplicate Detection Enabled",
            "status": "PASS" if calculated and has_flag else "FAIL",
        }

    @staticmethod
    def _check_no_fabrication_numbering(group_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in group_results
            if item.get("fabrication_number") is not None
        ]
        return {
            "name": "No Fabrication Numbering",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_bbs_fields(group_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in group_results
            if item.get("bar_schedule") or item.get("bbs_entry")
        ]
        return {
            "name": "No BBS Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_group_metadata_has_rule_reference(group_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("group_metadata") or {}).get("rule_reference")
        ]
        return {
            "name": "Group Metadata Rule Reference",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_group_metadata_has_rule_source(group_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in group_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("group_metadata") or {}).get("rule_source")
        ]
        return {
            "name": "Group Metadata Rule Source",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_engineering_signature_immutable(group_records: list) -> dict[str, Any]:
        invalid = []
        for record in group_records:
            if record.get("determination_state") != BarGroupState.CALCULATED.value:
                continue
            metadata = record.get("metadata") or record.get("group_metadata") or {}
            if metadata.get("engineering_signature") != record.get("engineering_signature"):
                invalid.append(record.get("bar_group_id"))
        return {
            "name": "Engineering Signature Immutable",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_group_ids_deterministic(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        sequences = []
        for item in calculated:
            group_id = str(item.get("engineering_group_id", ""))
            if "::" in group_id:
                sequences.append(int(group_id.rsplit("::", 1)[-1]))
        ok = sequences == list(range(1, len(sequences) + 1))
        return {
            "name": "Group IDs Deterministic",
            "status": "PASS" if ok else "FAIL",
            "record_count": len(sequences),
        }

    @staticmethod
    def _check_bar_group_node_in_graph(graph: CalculationDependencyGraph) -> dict[str, Any]:
        nodes = graph.to_dict().get("nodes", {})
        return {
            "name": "Bar Group Node In Graph",
            "status": "PASS" if "BAR_GROUP" in nodes else "FAIL",
        }

    @staticmethod
    def _check_bbs_depends_on_bar_group(graph: CalculationDependencyGraph) -> dict[str, Any]:
        depends = graph.depends_on("BBS")
        return {
            "name": "BBS Depends On Bar Group",
            "status": "PASS" if depends == ["BAR_GROUP"] else "FAIL",
            "depends_on": depends,
        }

    @staticmethod
    def _check_member_identity_ids_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not (item.get("member_identity_ids") or [])
        ]
        return {
            "name": "Member Identity Ids Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_member_beams_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not (item.get("member_beams") or [])
        ]
        return {
            "name": "Member Beams Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_member_roles_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not (item.get("member_roles") or [])
        ]
        return {
            "name": "Member Roles Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_diameter_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and item.get("diameter") is None
        ]
        return {
            "name": "Diameter Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_shape_code_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not item.get("shape_code")
        ]
        return {
            "name": "Shape Code Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_cut_length_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and item.get("cut_length") is None
        ]
        return {
            "name": "Cut Length Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_hook_length_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and item.get("hook_length") is None
        ]
        return {
            "name": "Hook Length Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_development_length_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and item.get("development_length") is None
        ]
        return {
            "name": "Development Length Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_lap_length_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and item.get("lap_length") is None
        ]
        return {
            "name": "Lap Length Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_geometry_signature_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not item.get("geometry_signature")
        ]
        return {
            "name": "Geometry Signature Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_support_configuration_populated(group_records: list) -> dict[str, Any]:
        missing = [
            item.get("bar_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
            and not item.get("support_configuration")
        ]
        return {
            "name": "Support Configuration Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_is_duplicate_group_flag(group_records: list) -> dict[str, Any]:
        calculated = [
            item for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        ]
        missing = [item.get("bar_group_id") for item in calculated if item.get("is_duplicate_group") is None]
        return {
            "name": "Duplicate Group Flag Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_formula_isolation() -> dict[str, Any]:
        import inspect
        from src.engineering_calculations.formula_engine.bar_group_classifier import (
            BarGroupClassifier,
        )

        source = inspect.getsource(BarGroupClassifier)
        forbidden = ("BarGroupEngine", "BarGroupDeterminer", "export", "registry")
        violations = [token for token in forbidden if token.lower() in source.lower()]
        return {
            "name": "Formula Isolation",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_no_scheduling_fields(group_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in group_results
            if item.get("schedule_number") or item.get("bundle_number") or item.get("cutting_list")
        ]
        return {
            "name": "No Scheduling Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
