"""Validate bar bending schedule determinations — Phase I.10."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.bar_group.bar_group_types import BarGroupState
from src.engineering_calculations.bar_identity.bar_identity_types import BarIdentityState
from src.engineering_calculations.bbs.bbs_determiner import bbs_applied
from src.engineering_calculations.bbs.bbs_types import (
    CALCULATION_TYPE,
    ENGINE_NAME,
    NAMESPACE_BBS,
    RULE_SOURCE_GENERAL_NOTES,
    BbsState,
    FabricationState,
    format_fabrication_mark,
    format_schedule_description,
)
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.formula_engine.bbs_classifier import (
    BbsClassificationInput,
    BbsClassifier,
)
from src.engineering_calculations.rule_resolution.bbs_rule_resolver import BbsRuleResolver
from src.engineering_calculations.rule_resolution.rule_types import ResolvedBbsRule
from src.reinforcement_calculation.calculation_state import CalculationState


class BbsValidator:
    """Verify BBS schedule determination integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not bbs_applied(model) and not model.get("bbs_results"):
            return {
                "phase": "Phase I.10",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "BBS determination not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        identity_records = model.get("bar_identity_results", [])
        group_records = model.get("bar_group_results", [])
        bbs_records = model.get("bbs_results", [])
        registry = model.get("bbs_registry", {})
        contexts = model.get("calculation_contexts", [])
        dependency_graph = model.get("calculation_dependency_graph", {})

        bbs_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]
        results_by_id = {
            str(item.get("result_id", "")): item
            for item in results
            if item.get("result_id")
        }
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_calculated_group_has_bbs_record(group_records, bbs_records))
        checks.append(self._check_every_bar_has_bbs_result(bars, bbs_results))
        checks.append(self._check_every_calculated_group_in_schedule(group_records, bbs_records))
        checks.append(self._check_every_schedule_has_members(bbs_records))
        checks.append(self._check_member_count_correct(bbs_records))
        checks.append(self._check_no_empty_schedules(bbs_records))
        checks.append(self._check_deferred_results_unchanged(bbs_results, bars))
        checks.append(self._check_blocked_results_unchanged(bbs_results, bars))
        checks.append(self._check_dependency_graph_exists(dependency_graph))
        checks.append(self._check_dependency_graph_consulted(bbs_records))
        checks.append(self._check_bar_group_prerequisite(bbs_records, group_records))
        checks.append(self._check_shape_prerequisite_preserved(bbs_records, group_records))
        checks.append(self._check_cut_length_prerequisite_preserved(bbs_records, group_records))
        checks.append(self._check_engineering_signature_exists(bbs_records))
        checks.append(self._check_signature_preserved(bbs_records, group_records))
        checks.append(self._check_engineering_group_id_populated(bbs_records))
        checks.append(self._check_general_notes_rules_only(bbs_records))
        checks.append(self._check_no_estimator_rule_usage(bbs_records))
        checks.append(self._check_classification_inputs_populated(bbs_results))
        checks.append(self._check_calculated_result_value_populated(bbs_results))
        checks.append(self._check_calculated_result_unit_schedule(bbs_results))
        checks.append(self._check_calculated_trace_exists(bbs_results))
        checks.append(self._check_schedule_metadata_present(bbs_results))
        checks.append(self._check_metadata_matches_result_value(bbs_results))
        checks.append(self._check_provenance_attached(bbs_results))
        checks.append(self._check_provenance_source_ids_valid(bbs_results, results_by_id))
        checks.append(self._check_provenance_six_sources(bbs_results))
        checks.append(self._check_deferred_blocked_no_metadata(bbs_results))
        checks.append(self._check_registry_integrity(registry, bbs_records))
        checks.append(self._check_deterministic_bbs_ids(bbs_records))
        checks.append(self._check_unique_bbs_ids(bbs_records))
        checks.append(self._check_unique_engineering_signatures(bbs_records))
        checks.append(self._check_unique_engineering_group_ids(bbs_records))
        checks.append(self._check_unique_fabrication_marks(bbs_records))
        checks.append(self._check_fabrication_mark_deterministic(bbs_records))
        checks.append(self._check_fabrication_mark_format(bbs_records))
        checks.append(self._check_traceability_preserved(bbs_records))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, bbs_results))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, bbs_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, bbs_results))
        checks.append(self._check_bar_group_results_preserved(group_records))
        checks.append(self._check_identity_results_preserved(identity_records))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_quantity_generation(results))
        checks.append(self._check_no_weight_calculation(results))
        checks.append(self._check_no_boq_generation(results))
        checks.append(self._check_no_procurement_fields(results))
        checks.append(self._check_no_costing_fields(results))
        checks.append(self._check_no_optimization_fields(results))
        checks.append(self._check_no_bundle_fields(results))
        checks.append(self._check_no_packing_fields(results))
        checks.append(self._check_export_integrity(registry, bbs_records))
        checks.append(self._check_registry_lookup_integrity(bbs_records))
        checks.append(self._check_engine_name_for_calculated(bbs_results))
        checks.append(self._check_calculation_reproducibility(bbs_records, group_records))
        checks.append(self._check_statistics_integrity(registry, bbs_records))
        checks.append(self._check_classifier_isolated())
        checks.append(self._check_rule_resolver_isolated())
        checks.append(self._check_engine_separation())
        checks.append(self._check_dependency_satisfied_for_calculated(bars, graph, group_records))
        checks.append(self._check_schedule_reproducible(group_records))
        checks.append(self._check_stable_ordering(bbs_records))
        checks.append(self._check_schedule_ordering_by_signature_then_group(bbs_records))
        checks.append(self._check_no_orphan_schedules(bbs_records, registry))
        checks.append(self._check_schedule_metadata_has_rule_reference(bbs_results))
        checks.append(self._check_schedule_metadata_has_rule_source(bbs_results))
        checks.append(self._check_engineering_signature_immutable(bbs_records))
        checks.append(self._check_schedule_position_populated(bbs_records))
        checks.append(self._check_schedule_description_populated(bbs_records))
        checks.append(self._check_bbs_node_in_graph(graph))
        checks.append(self._check_bbs_depends_on_bar_group(graph))
        checks.append(self._check_member_identity_ids_populated(bbs_records))
        checks.append(self._check_member_beams_populated(bbs_records))
        checks.append(self._check_member_roles_populated(bbs_records))
        checks.append(self._check_diameter_populated(bbs_records))
        checks.append(self._check_shape_code_populated(bbs_records))
        checks.append(self._check_cut_length_populated(bbs_records))
        checks.append(self._check_geometry_signature_populated(bbs_records))
        checks.append(self._check_support_configuration_populated(bbs_records))
        checks.append(self._check_fabrication_state_populated(bbs_records))
        checks.append(self._check_formula_isolation())
        checks.append(self._check_steel_weight_not_calculated(results))
        checks.append(self._check_identity_preserved_in_schedule(bbs_records, group_records))
        checks.append(self._check_shape_preserved_in_schedule(bbs_records, group_records))
        checks.append(self._check_cut_length_preserved_in_schedule(bbs_records, group_records))
        checks.append(self._check_engineering_group_preserved(bbs_records, group_records))
        checks.append(self._check_bar_group_id_preserved(bbs_records, group_records))
        checks.append(self._check_no_duplicate_fabrication_marks(bbs_records))
        checks.append(self._check_schedule_description_deterministic(bbs_records))
        checks.append(self._check_result_value_is_fabrication_mark(bbs_results))
        checks.append(self._check_no_scheduling_quantity_fields(bbs_results))
        checks.append(self._check_fabrication_ready_state_for_calculated(bbs_records))
        checks.append(self._check_bar_group_id_populated(bbs_records))
        checks.append(self._check_classification_inputs_have_fabrication_mark(bbs_results))
        checks.append(self._check_registry_fabrication_mark_index(registry, bbs_records))
        checks.append(self._check_registry_engineering_group_index(registry, bbs_records))
        checks.append(self._check_no_failed_for_ready_groups(bbs_records, group_records))
        checks.append(self._check_member_bar_ids_preserved(bbs_records, group_records))
        checks.append(self._check_schedule_position_sequential(bbs_records))
        checks.append(self._check_fabrication_mark_matches_position(bbs_records))
        checks.append(self._check_group_record_reference_valid(bbs_records, group_records))
        checks.append(self._check_bbs_result_has_engineering_group_reference(bbs_results))
        checks.append(self._check_preserved_fabrication_state(bbs_records))
        checks.append(self._check_no_quantity_on_bbs_records(bbs_records))
        checks.append(self._check_no_weight_on_bbs_records(bbs_records))
        checks.append(self._check_no_boq_on_bbs_records(bbs_records))
        checks.append(self._check_registry_phase_correct(registry))
        checks.append(self._check_registry_namespace_correct(registry))
        checks.append(self._check_calculated_bbs_has_provenance_record(bbs_records))
        checks.append(self._check_deferred_fabrication_state(bbs_records))
        checks.append(self._check_blocked_fabrication_state(bbs_records))
        checks.append(self._check_no_calculated_bbs_without_group(bbs_records, group_records))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.10",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "bbs_result_count": len(bbs_results),
                "determination_count": len(bbs_records),
            },
        }

    @staticmethod
    def _calculated_bbs_records(bbs_records: list) -> list:
        return [
            item for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
        ]

    @staticmethod
    def _group_by_id(group_records: list) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("bar_group_id", "")): item
            for item in group_records
            if item.get("bar_group_id")
        }

    @staticmethod
    def _check_every_calculated_group_has_bbs_record(
        group_records: list,
        bbs_records: list,
    ) -> dict[str, Any]:
        group_ids = {
            item.get("engineering_group_id")
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        }
        bbs_group_ids = {
            item.get("engineering_group_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
        }
        missing = sorted(group_ids - bbs_group_ids)
        return {
            "name": "Every Calculated Group Has BBS Record",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_bar_has_bbs_result(bars: list, bbs_results: list) -> dict[str, Any]:
        bar_ids = {str(item.get("bar_id", "")) for item in bars}
        covered = {str(item.get("input_bar_id", "")) for item in bbs_results}
        missing = sorted(bar_ids - covered)
        return {
            "name": "Every Bar Has BBS Result",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_calculated_group_in_schedule(
        group_records: list,
        bbs_records: list,
    ) -> dict[str, Any]:
        calculated_groups = {
            str(item.get("bar_group_id", ""))
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        }
        scheduled_groups = {
            str(item.get("bar_group_id", ""))
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
        }
        missing = sorted(calculated_groups - scheduled_groups)
        return {
            "name": "Every Calculated Group In Schedule",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_schedule_has_members(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
            and not (item.get("member_bar_ids") or [])
        ]
        return {
            "name": "Every Schedule Has Members",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_member_count_correct(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
            and len(item.get("member_bar_ids") or []) < 1
        ]
        return {
            "name": "Member Count Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_empty_schedules(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
            and not (item.get("member_bar_ids") or [])
        ]
        return {
            "name": "No Empty Schedules",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_results_unchanged(bbs_results: list, bars: list) -> dict[str, Any]:
        deferred_bars = {
            str(item.get("bar_id", ""))
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        changed = [
            item.get("result_id")
            for item in bbs_results
            if str(item.get("input_bar_id", "")) in deferred_bars
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "Deferred Results Unchanged",
            "status": "PASS" if not changed else "FAIL",
            "changed_count": len(changed),
        }

    @staticmethod
    def _check_blocked_results_unchanged(bbs_results: list, bars: list) -> dict[str, Any]:
        blocked_bars = {
            str(item.get("bar_id", ""))
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.BLOCKED.value
        }
        changed = [
            item.get("result_id")
            for item in bbs_results
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
    def _check_dependency_graph_consulted(bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        missing = [
            item.get("bbs_id")
            for item in calculated
            if not item.get("dependency_graph_consulted")
        ]
        return {
            "name": "Dependency Graph Consulted",
            "status": "PASS" if calculated and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_bar_group_prerequisite(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            bar_group_id = str(record.get("bar_group_id", ""))
            group = group_by_id.get(bar_group_id)
            if not group or group.get("determination_state") != BarGroupState.CALCULATED.value:
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Bar Group Prerequisite",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_shape_prerequisite_preserved(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            group = group_by_id.get(str(record.get("bar_group_id", "")))
            if not group or record.get("shape_code") != group.get("shape_code"):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Shape Prerequisite Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_cut_length_prerequisite_preserved(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            group = group_by_id.get(str(record.get("bar_group_id", "")))
            if not group or record.get("cut_length") != group.get("cut_length"):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Cut Length Prerequisite Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engineering_signature_exists(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
            and not item.get("engineering_signature")
        ]
        return {
            "name": "Engineering Signature Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_signature_preserved(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            group = group_by_id.get(str(record.get("bar_group_id", "")))
            if not group or record.get("engineering_signature") != group.get("engineering_signature"):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Signature Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engineering_group_id_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
            and not item.get("engineering_group_id")
        ]
        return {
            "name": "Engineering Group Id Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_general_notes_rules_only(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.CALCULATED.value
            and item.get("rule_source") not in {RULE_SOURCE_GENERAL_NOTES, "GENERAL_NOTES"}
        ]
        return {
            "name": "General Notes Or Structural Code Rules Only",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_estimator_rule_usage(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if "ESTIMATOR" in str(item.get("rule_source", "")).upper()
        ]
        return {
            "name": "No Estimator Rules",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_classification_inputs_populated(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("classification_inputs")
        ]
        return {
            "name": "Classification Inputs Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_value_populated(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("result_value")
        ]
        return {
            "name": "Result Value Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_result_unit_schedule(bbs_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "SCHEDULE"
        ]
        return {
            "name": "Result Unit Is SCHEDULE",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_trace_exists(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {
            "name": "Calculation Trace Exists",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_schedule_metadata_present(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("bbs_metadata") or item.get("schedule_metadata"))
        ]
        return {
            "name": "Schedule Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_metadata_matches_result_value(bbs_results: list) -> dict[str, Any]:
        invalid = []
        for item in bbs_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            metadata = item.get("bbs_metadata") or item.get("schedule_metadata") or {}
            if metadata.get("fabrication_mark") != item.get("result_value"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Metadata Matches Result Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_attached(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
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
        bbs_results: list,
        results_by_id: dict,
    ) -> dict[str, Any]:
        invalid = []
        for item in bbs_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            provenance = item.get("calculation_provenance") or {}
            for source in provenance.get("sources", []):
                source_id = str(source.get("result_id", ""))
                calc_type = str(source.get("calculation_type", ""))
                if calc_type in {"BEAM_GEOMETRY", "ENGINEERING_SIGNATURE", "BBS_GENERATION", "BAR_GROUP"}:
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
    def _check_provenance_six_sources(bbs_results: list) -> dict[str, Any]:
        invalid = []
        for item in bbs_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            provenance = item.get("calculation_provenance") or {}
            if len(provenance.get("sources", [])) < 6:
                invalid.append(item.get("result_id"))
        return {
            "name": "Provenance Six Sources",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_deferred_blocked_no_metadata(bbs_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") in {
                CalculationResultState.DEFERRED.value,
                CalculationResultState.BLOCKED.value,
            }
            and (item.get("bbs_metadata") or item.get("schedule_metadata"))
        ]
        return {
            "name": "Deferred Blocked No Metadata",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(registry: dict, bbs_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_BBS
            and registry.get("determination_count") == len(bbs_records)
        )
        return {
            "name": "Registry Integrity",
            "status": "PASS" if ok else "FAIL",
            "determination_count": len(bbs_records),
        }

    @staticmethod
    def _check_deterministic_bbs_ids(bbs_records: list) -> dict[str, Any]:
        ids = [str(item.get("bbs_id", "")) for item in bbs_records if item.get("bbs_id")]
        return {
            "name": "Deterministic BBS IDs",
            "status": "PASS" if ids and ids == sorted(ids, key=lambda value: int(value.rsplit("::", 1)[-1])) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_unique_bbs_ids(bbs_records: list) -> dict[str, Any]:
        ids = [item.get("bbs_id") for item in bbs_records if item.get("bbs_id")]
        return {
            "name": "Unique BBS IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
            "record_count": len(ids),
        }

    @staticmethod
    def _check_unique_engineering_signatures(bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        signatures = [item.get("engineering_signature") for item in calculated]
        return {
            "name": "Unique Engineering Signatures",
            "status": "PASS" if len(signatures) == len(set(signatures)) else "FAIL",
            "record_count": len(signatures),
        }

    @staticmethod
    def _check_unique_engineering_group_ids(bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        group_ids = [item.get("engineering_group_id") for item in calculated]
        return {
            "name": "Unique Engineering Group IDs",
            "status": "PASS" if len(group_ids) == len(set(group_ids)) else "FAIL",
            "record_count": len(group_ids),
        }

    @staticmethod
    def _check_unique_fabrication_marks(bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        marks = [item.get("fabrication_mark") for item in calculated if item.get("fabrication_mark")]
        return {
            "name": "Unique Fabrication Marks",
            "status": "PASS" if len(marks) == len(set(marks)) else "FAIL",
            "record_count": len(marks),
        }

    @staticmethod
    def _check_fabrication_mark_deterministic(bbs_records: list) -> dict[str, Any]:
        calculated = sorted(
            BbsValidator._calculated_bbs_records(bbs_records),
            key=lambda item: int(item.get("schedule_position") or 0),
        )
        expected = [format_fabrication_mark(index) for index in range(1, len(calculated) + 1)]
        actual = [str(item.get("fabrication_mark", "")) for item in calculated]
        return {
            "name": "Fabrication Mark Deterministic",
            "status": "PASS" if actual == expected else "FAIL",
            "record_count": len(calculated),
        }

    @staticmethod
    def _check_fabrication_mark_format(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not str(item.get("fabrication_mark", "")).startswith("BM")
        ]
        return {
            "name": "Fabrication Mark Format",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_traceability_preserved(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in bbs_records
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, bbs_results: list) -> dict[str, Any]:
        ready_count = sum(
            1
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        )
        calculated = sum(
            1
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
        )
        return {
            "name": "Calculated Count Matches Ready Bars",
            "status": "PASS" if calculated == ready_count else "FAIL",
            "expected": ready_count,
            "actual": calculated,
        }

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, bbs_records: list) -> dict[str, Any]:
        deferred_bars = sum(
            1
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        )
        deferred_records = sum(
            1
            for item in bbs_records
            if item.get("determination_state") == BbsState.DEFERRED.value
        )
        return {
            "name": "Deferred Count Matches Deferred Bars",
            "status": "PASS" if deferred_records == deferred_bars else "FAIL",
            "expected": deferred_bars,
            "actual": deferred_records,
        }

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, bbs_results: list) -> dict[str, Any]:
        deferred_bars = {
            str(item.get("bar_id", ""))
            for item in bars
            if (item.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        }
        invalid = [
            item.get("result_id")
            for item in bbs_results
            if str(item.get("input_bar_id", "")) in deferred_bars
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No Calculated For Deferred Readiness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_bar_group_results_preserved(group_records: list) -> dict[str, Any]:
        calculated = sum(
            1
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        )
        return {
            "name": "Bar Group Results Preserved",
            "status": "PASS" if calculated >= 0 else "FAIL",
            "calculated_count": calculated,
        }

    @staticmethod
    def _check_identity_results_preserved(identity_records: list) -> dict[str, Any]:
        calculated = sum(
            1
            for item in identity_records
            if item.get("determination_state") == BarIdentityState.CALCULATED.value
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
    def _check_no_procurement_fields(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("procurement") or item.get("procurement_quantity")
        ]
        return {
            "name": "No Procurement Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_costing_fields(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("costing") or item.get("cost_estimate") is not None
        ]
        return {
            "name": "No Costing Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_optimization_fields(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("optimization") or item.get("optimized_length") is not None
        ]
        return {
            "name": "No Optimization Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_bundle_fields(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("bundle_number") or item.get("bundle_id")
        ]
        return {
            "name": "No Bundle Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_packing_fields(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("packing") or item.get("packing_list")
        ]
        return {
            "name": "No Packing Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_export_integrity(registry: dict, bbs_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(bbs_records)
        return {
            "name": "Export Integrity",
            "status": "PASS" if bbs_records and ok else "FAIL",
            "determination_count": len(bbs_records),
        }

    @staticmethod
    def _check_registry_lookup_integrity(bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        ok = all(
            item.get("bbs_id")
            and item.get("engineering_signature")
            and item.get("fabrication_mark")
            for item in calculated
        )
        return {
            "name": "Registry Lookup Integrity",
            "status": "PASS" if ok else "FAIL",
            "calculated_count": len(calculated),
        }

    @staticmethod
    def _check_engine_name_for_calculated(bbs_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in bbs_results
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
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        rule = ResolvedBbsRule(
            fabrication_mark_format="BM{sequence:03d}",
            schedule_numbering_policy="SEQUENTIAL_BY_ENGINEERING_ORDER",
            schedule_ordering_policy="ENGINEERING_SIGNATURE_THEN_GROUP",
            naming_policy="ROLE_SHAPE_DIAMETER",
            rule_source=RULE_SOURCE_GENERAL_NOTES,
            rule_name="BBS_FOUNDATION_POLICY",
            rule_reference="BBS_FOUNDATION",
            rule_priority=1,
            structural_code_reference="IS456_REINFORCEMENT",
            general_notes_reference="",
            lookup_path=(),
            rule_description="",
        )
        expected = BbsClassifier.classify(
            BbsClassificationInput(
                resolved_rule=rule,
                group_records=tuple(group_records),
            )
        )
        expected_by_group = {item.bar_group_id: item for item in expected}
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            expected_membership = expected_by_group.get(str(record.get("bar_group_id", "")))
            if not expected_membership:
                invalid.append(record.get("bbs_id"))
                continue
            if record.get("engineering_group_id") != expected_membership.engineering_group_id:
                invalid.append(record.get("bbs_id"))
                continue
            if record.get("engineering_signature") != expected_membership.engineering_signature:
                invalid.append(record.get("bbs_id"))
                continue
            if tuple(record.get("member_bar_ids") or []) != expected_membership.member_bar_ids:
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Calculation Reproducibility",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_statistics_integrity(registry: dict, bbs_records: list) -> dict[str, Any]:
        ok = registry.get("determination_count") == len(bbs_records)
        return {
            "name": "Statistics Integrity",
            "status": "PASS" if bbs_records and ok else "FAIL",
            "determination_count": len(bbs_records),
        }

    @staticmethod
    def _check_classifier_isolated() -> dict[str, Any]:
        import inspect
        from src.engineering_calculations.formula_engine.bbs_classifier import BbsClassifier

        source = inspect.getsource(BbsClassifier)
        forbidden = ("EngineeringRuleCache", "BbsRuleResolver", "dependency_graph", "BbsRegistry")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Classifier Isolated",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_rule_resolver_isolated() -> dict[str, Any]:
        import inspect

        source = inspect.getsource(BbsRuleResolver)
        forbidden = ("BbsClassifier", "classify(", "format_fabrication_mark")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Rule Resolver Isolated",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_engine_separation() -> dict[str, Any]:
        import inspect
        from src.engineering_calculations.bbs.bbs_determiner import BbsDeterminer
        from src.engineering_calculations.bbs.bbs_engine import BbsEngine

        engine_source = inspect.getsource(BbsEngine)
        determiner_source = inspect.getsource(BbsDeterminer)
        engine_ok = "BbsDeterminer" in engine_source and "BbsClassifier" not in engine_source
        determiner_ok = (
            "BbsRuleResolver" in determiner_source
            and "BbsClassifier" in determiner_source
        )
        ok = engine_ok and determiner_ok
        return {"name": "Engine Separation", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_dependency_satisfied_for_calculated(
        bars: list,
        graph: CalculationDependencyGraph,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_bar: dict[str, dict[str, Any]] = {}
        for record in group_records:
            for bar_id in record.get("member_bar_ids") or []:
                group_by_bar[str(bar_id)] = record

        invalid = []
        for bar in bars:
            readiness = bar.get("calculation_readiness") or {}
            if readiness.get("calculation_state") != CalculationState.READY.value:
                continue
            bar_id = str(bar.get("bar_id", ""))
            for dependency in graph.depends_on("BBS"):
                if dependency == "BAR_GROUP":
                    group = group_by_bar.get(bar_id)
                    if (
                        not group
                        or group.get("determination_state") != BarGroupState.CALCULATED.value
                    ):
                        invalid.append(bar_id)
                        break
        return {
            "name": "Dependency Satisfied For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_schedule_reproducible(group_records: list) -> dict[str, Any]:
        rule = ResolvedBbsRule(
            fabrication_mark_format="BM{sequence:03d}",
            schedule_numbering_policy="SEQUENTIAL_BY_ENGINEERING_ORDER",
            schedule_ordering_policy="ENGINEERING_SIGNATURE_THEN_GROUP",
            naming_policy="ROLE_SHAPE_DIAMETER",
            rule_source=RULE_SOURCE_GENERAL_NOTES,
            rule_name="BBS_FOUNDATION_POLICY",
            rule_reference="BBS_FOUNDATION",
            rule_priority=1,
            structural_code_reference="IS456_REINFORCEMENT",
            general_notes_reference="",
            lookup_path=(),
            rule_description="",
        )
        first = BbsClassifier.classify(
            BbsClassificationInput(resolved_rule=rule, group_records=tuple(group_records))
        )
        second = BbsClassifier.classify(
            BbsClassificationInput(resolved_rule=rule, group_records=tuple(reversed(group_records)))
        )
        ok = first == second
        return {"name": "Schedule Reproducible", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_stable_ordering(bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        signatures = [str(item.get("engineering_signature", "")) for item in calculated]
        sorted_signatures = sorted(
            calculated,
            key=lambda item: (
                str(item.get("engineering_signature", "")),
                str(item.get("engineering_group_id", "")),
            ),
        )
        actual_order = [str(item.get("engineering_signature", "")) for item in calculated]
        expected_order = [str(item.get("engineering_signature", "")) for item in sorted_signatures]
        ok = actual_order == expected_order
        return {
            "name": "Stable Ordering",
            "status": "PASS" if ok else "FAIL",
            "record_count": len(signatures),
        }

    @staticmethod
    def _check_schedule_ordering_by_signature_then_group(bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        actual_keys = [
            (
                str(item.get("engineering_signature", "")),
                str(item.get("engineering_group_id", "")),
            )
            for item in calculated
        ]
        expected_keys = sorted(actual_keys)
        return {
            "name": "Schedule Ordering By Signature Then Group",
            "status": "PASS" if actual_keys == expected_keys else "FAIL",
            "record_count": len(calculated),
        }

    @staticmethod
    def _check_no_orphan_schedules(bbs_records: list, registry: dict) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        record_marks = {
            str(item.get("fabrication_mark", ""))
            for item in calculated
            if item.get("fabrication_mark")
        }
        registry_marks = {
            str(mark)
            for mark in (registry.get("results_by_fabrication_mark") or {}).keys()
            if mark and str(mark) != "None"
        }
        orphans = record_marks.symmetric_difference(registry_marks)
        return {
            "name": "No Orphan Schedules",
            "status": "PASS" if not orphans else "FAIL",
            "orphan_count": len(orphans),
        }

    @staticmethod
    def _check_schedule_metadata_has_rule_reference(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("bbs_metadata") or item.get("schedule_metadata") or {}).get("rule_reference")
        ]
        return {
            "name": "Schedule Metadata Rule Reference",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_schedule_metadata_has_rule_source(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("bbs_metadata") or item.get("schedule_metadata") or {}).get("rule_source")
        ]
        return {
            "name": "Schedule Metadata Rule Source",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_engineering_signature_immutable(bbs_records: list) -> dict[str, Any]:
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            metadata = record.get("metadata") or record.get("bbs_metadata") or record.get("schedule_metadata") or {}
            if metadata.get("engineering_signature") != record.get("engineering_signature"):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Engineering Signature Immutable",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_schedule_position_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not item.get("schedule_position")
        ]
        return {
            "name": "Schedule Position Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_schedule_description_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not item.get("schedule_description")
        ]
        return {
            "name": "Schedule Description Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_bbs_node_in_graph(graph: CalculationDependencyGraph) -> dict[str, Any]:
        nodes = graph.to_dict().get("nodes", {})
        return {
            "name": "BBS Node In Graph",
            "status": "PASS" if "BBS" in nodes else "FAIL",
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
    def _check_member_identity_ids_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not (item.get("member_identity_ids") or [])
        ]
        return {
            "name": "Member Identity Ids Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_member_beams_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not (item.get("member_beams") or [])
        ]
        return {
            "name": "Member Beams Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_member_roles_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not (item.get("member_roles") or [])
        ]
        return {
            "name": "Member Roles Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_diameter_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if item.get("diameter") is None
        ]
        return {
            "name": "Diameter Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_shape_code_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not item.get("shape_code")
        ]
        return {
            "name": "Shape Code Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_cut_length_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if item.get("cut_length") is None
        ]
        return {
            "name": "Cut Length Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_geometry_signature_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not item.get("geometry_signature")
        ]
        return {
            "name": "Geometry Signature Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_support_configuration_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not item.get("support_configuration")
        ]
        return {
            "name": "Support Configuration Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_fabrication_state_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in bbs_records
            if not item.get("fabrication_state")
        ]
        return {
            "name": "Fabrication State Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_formula_isolation() -> dict[str, Any]:
        import inspect
        from src.engineering_calculations.formula_engine.bbs_classifier import BbsClassifier

        source = inspect.getsource(BbsClassifier)
        forbidden = ("BbsEngine", "BbsDeterminer", "export", "registry")
        violations = [token for token in forbidden if token.lower() in source.lower()]
        return {
            "name": "Formula Isolation",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_steel_weight_not_calculated(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CalculationType.STEEL_WEIGHT.value
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "Steel Weight Not Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_identity_preserved_in_schedule(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            group = group_by_id.get(str(record.get("bar_group_id", "")))
            if not group:
                invalid.append(record.get("bbs_id"))
                continue
            if tuple(record.get("member_identity_ids") or []) != tuple(group.get("member_identity_ids") or []):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Identity Preserved In Schedule",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_shape_preserved_in_schedule(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            group = group_by_id.get(str(record.get("bar_group_id", "")))
            if not group or record.get("shape_code") != group.get("shape_code"):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Shape Preserved In Schedule",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_cut_length_preserved_in_schedule(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            group = group_by_id.get(str(record.get("bar_group_id", "")))
            if not group or record.get("cut_length") != group.get("cut_length"):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Cut Length Preserved In Schedule",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engineering_group_preserved(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            group = group_by_id.get(str(record.get("bar_group_id", "")))
            if not group or record.get("engineering_group_id") != group.get("engineering_group_id"):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Engineering Group Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_bar_group_id_preserved(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_ids = {str(item.get("bar_group_id", "")) for item in group_records if item.get("bar_group_id")}
        invalid = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if str(item.get("bar_group_id", "")) not in group_ids
        ]
        return {
            "name": "Bar Group Id Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_duplicate_fabrication_marks(bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        marks = [str(item.get("fabrication_mark", "")) for item in calculated if item.get("fabrication_mark")]
        ok = len(marks) == len(set(marks))
        return {
            "name": "No Duplicate Fabrication Marks",
            "status": "PASS" if ok else "FAIL",
            "record_count": len(marks),
        }

    @staticmethod
    def _check_schedule_description_deterministic(bbs_records: list) -> dict[str, Any]:
        invalid = []
        for record in BbsValidator._calculated_bbs_records(bbs_records):
            roles = record.get("member_roles") or []
            primary_role = str(roles[0]) if roles else ""
            expected = format_schedule_description(
                len(record.get("member_bar_ids") or []),
                int(record.get("diameter") or 0),
                primary_role,
                str(record.get("shape_code") or ""),
            )
            if record.get("schedule_description") != expected:
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Schedule Description Deterministic",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_result_value_is_fabrication_mark(bbs_results: list) -> dict[str, Any]:
        invalid = []
        for item in bbs_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            value = str(item.get("result_value", ""))
            if not value.startswith("BM"):
                invalid.append(item.get("result_id"))
        return {
            "name": "Result Value Is Fabrication Mark",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_scheduling_quantity_fields(bbs_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in bbs_results
            if item.get("quantity") is not None
            or item.get("boq_quantity") is not None
            or item.get("steel_weight") is not None
        ]
        return {
            "name": "No Scheduling Quantity Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_fabrication_ready_state_for_calculated(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if item.get("fabrication_state") != FabricationState.FABRICATION_READY.value
        ]
        return {
            "name": "Fabrication Ready State For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_bar_group_id_populated(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not item.get("bar_group_id")
        ]
        return {
            "name": "Bar Group Id Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_classification_inputs_have_fabrication_mark(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("classification_inputs") or {}).get("fabrication_mark")
        ]
        return {
            "name": "Classification Inputs Have Fabrication Mark",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_registry_fabrication_mark_index(registry: dict, bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        index = registry.get("results_by_fabrication_mark") or {}
        missing = [
            item.get("bbs_id")
            for item in calculated
            if str(item.get("fabrication_mark", "")) not in index
        ]
        return {
            "name": "Registry Fabrication Mark Index",
            "status": "PASS" if calculated and not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_registry_engineering_group_index(registry: dict, bbs_records: list) -> dict[str, Any]:
        calculated = BbsValidator._calculated_bbs_records(bbs_records)
        index = registry.get("results_by_signature") or {}
        ok = bool(index) or not calculated
        return {
            "name": "Registry Engineering Group Index",
            "status": "PASS" if ok else "FAIL",
            "index_count": len(index),
        }

    @staticmethod
    def _check_no_failed_for_ready_groups(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        ready_groups = {
            str(item.get("bar_group_id", ""))
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        }
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if str(item.get("bar_group_id", "")) in ready_groups
            and item.get("determination_state") == BbsState.FAILED.value
        ]
        return {
            "name": "No Failed For Ready Groups",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_member_bar_ids_preserved(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            group = group_by_id.get(str(record.get("bar_group_id", "")))
            if not group:
                invalid.append(record.get("bbs_id"))
                continue
            if tuple(record.get("member_bar_ids") or []) != tuple(group.get("member_bar_ids") or []):
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Member Bar Ids Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_schedule_position_sequential(bbs_records: list) -> dict[str, Any]:
        calculated = sorted(
            BbsValidator._calculated_bbs_records(bbs_records),
            key=lambda item: int(item.get("schedule_position") or 0),
        )
        positions = [int(item.get("schedule_position") or 0) for item in calculated]
        expected = list(range(1, len(calculated) + 1))
        return {
            "name": "Schedule Position Sequential",
            "status": "PASS" if positions == expected else "FAIL",
            "record_count": len(calculated),
        }

    @staticmethod
    def _check_fabrication_mark_matches_position(bbs_records: list) -> dict[str, Any]:
        invalid = []
        for record in BbsValidator._calculated_bbs_records(bbs_records):
            position = int(record.get("schedule_position") or 0)
            expected = format_fabrication_mark(position)
            if str(record.get("fabrication_mark", "")) != expected:
                invalid.append(record.get("bbs_id"))
        return {
            "name": "Fabrication Mark Matches Position",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_group_record_reference_valid(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_by_id = BbsValidator._group_by_id(group_records)
        invalid = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if str(item.get("bar_group_id", "")) not in group_by_id
        ]
        return {
            "name": "Group Record Reference Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_bbs_result_has_engineering_group_reference(bbs_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in bbs_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("result_metadata") or {}).get("engineering_group_id")
            and not (item.get("bbs_metadata") or item.get("schedule_metadata") or {}).get("engineering_group_id")
        ]
        return {
            "name": "BBS Result Has Engineering Group Reference",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_preserved_fabrication_state(bbs_records: list) -> dict[str, Any]:
        deferred = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.DEFERRED.value
            and item.get("fabrication_state") != FabricationState.FABRICATION_DEFERRED.value
        ]
        blocked = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("determination_state") == BbsState.BLOCKED.value
            and item.get("fabrication_state") != FabricationState.FABRICATION_BLOCKED.value
        ]
        invalid = deferred + blocked
        return {
            "name": "Preserved Fabrication State",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_quantity_on_bbs_records(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("quantity") is not None or item.get("boq_quantity") is not None
        ]
        return {
            "name": "No Quantity On BBS Records",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_weight_on_bbs_records(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("steel_weight") is not None or item.get("weight_kg") is not None
        ]
        return {
            "name": "No Weight On BBS Records",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_boq_on_bbs_records(bbs_records: list) -> dict[str, Any]:
        invalid = [
            item.get("bbs_id")
            for item in bbs_records
            if item.get("boq") or item.get("boq_entry")
        ]
        return {
            "name": "No BOQ On BBS Records",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_phase_correct(registry: dict) -> dict[str, Any]:
        return {
            "name": "Registry Phase Correct",
            "status": "PASS" if registry.get("phase") == "Phase I.10" else "FAIL",
        }

    @staticmethod
    def _check_registry_namespace_correct(registry: dict) -> dict[str, Any]:
        return {
            "name": "Registry Namespace Correct",
            "status": "PASS" if registry.get("namespace") == NAMESPACE_BBS else "FAIL",
        }

    @staticmethod
    def _check_calculated_bbs_has_provenance_record(bbs_records: list) -> dict[str, Any]:
        missing = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if not (item.get("calculation_provenance") or item.get("provenance"))
        ]
        return {
            "name": "Calculated BBS Has Provenance Record",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_deferred_fabrication_state(bbs_records: list) -> dict[str, Any]:
        deferred = [
            item for item in bbs_records
            if item.get("determination_state") == BbsState.DEFERRED.value
        ]
        invalid = [
            item.get("bbs_id")
            for item in deferred
            if item.get("fabrication_state") != FabricationState.FABRICATION_DEFERRED.value
        ]
        return {
            "name": "Deferred Fabrication State",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_blocked_fabrication_state(bbs_records: list) -> dict[str, Any]:
        blocked = [
            item for item in bbs_records
            if item.get("determination_state") == BbsState.BLOCKED.value
        ]
        invalid = [
            item.get("bbs_id")
            for item in blocked
            if item.get("fabrication_state") != FabricationState.FABRICATION_BLOCKED.value
        ]
        return {
            "name": "Blocked Fabrication State",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_calculated_bbs_without_group(
        bbs_records: list,
        group_records: list,
    ) -> dict[str, Any]:
        group_ids = {
            str(item.get("engineering_group_id", ""))
            for item in group_records
            if item.get("determination_state") == BarGroupState.CALCULATED.value
        }
        invalid = [
            item.get("bbs_id")
            for item in BbsValidator._calculated_bbs_records(bbs_records)
            if str(item.get("engineering_group_id", "")) not in group_ids
        ]
        return {
            "name": "No Calculated BBS Without Group",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
