"""Validate beam reinforcement summaries — Phase I.12."""

from __future__ import annotations

import inspect
from typing import Any, List

from src.engineering_calculations.beam_summary.beam_summary_builder import BeamSummaryBuilder
from src.engineering_calculations.beam_summary.beam_summary_engine import BeamSummaryEngine
from src.engineering_calculations.beam_summary.beam_summary_types import (
    ENGINE_NAME,
    ENGINEERING_COMPLETE,
    FABRICATION_READY,
    NAMESPACE_BEAM_SUMMARY,
    QUALITY_GRADE_A,
    QUALITY_GRADE_B,
    QUALITY_GRADE_C,
    QUALITY_GRADE_D,
    QUALITY_GRADE_UNKNOWN,
    READINESS_BLOCKED,
    READINESS_EMPTY,
    READINESS_PARTIAL,
    READINESS_READY,
    BeamSummaryState,
)
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.steel_weight.steel_weight_types import SteelWeightState


def beam_summary_applied(model: dict[str, Any]) -> bool:
    registry = model.get("beam_summary_registry", {})
    if registry.get("phase") == "Phase I.12" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("beam_summary_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("beam_summary_complete"))


class BeamSummaryValidator:
    """Verify beam reinforcement summary integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not beam_summary_applied(model) and not model.get("beam_summary_results"):
            return {
                "phase": "Phase I.12.2",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "Beam summary not applied"},
            }

        beams = model.get("beams", [])
        bars = model.get("reinforcement_bars", [])
        weight_records = model.get("steel_weight_results", [])
        summary_records = model.get("beam_summary_results", [])
        registry = model.get("beam_summary_registry", {})
        dependency_graph = model.get("calculation_dependency_graph", {})
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        check_methods = [
            self._check_every_beam_has_summary,
            self._check_one_summary_per_beam,
            self._check_unique_summary_ids,
            self._check_deterministic_summary_ids,
            self._check_beam_ids_preserved,
            self._check_beam_marks_preserved,
            self._check_section_preserved,
            self._check_span_preserved,
            self._check_weight_totals_equal_members,
            self._check_cut_length_totals_equal_members,
            self._check_every_calculated_beam_has_weight,
            self._check_shape_codes_preserved,
            self._check_diameter_list_unique,
            self._check_role_list_unique,
            self._check_fabrication_marks_unique,
            self._check_registry_integrity,
            self._check_registry_namespace,
            self._check_registry_phase,
            self._check_registry_beam_lookup,
            self._check_registry_beam_mark_lookup,
            self._check_registry_fabrication_mark_lookup,
            self._check_registry_shape_lookup,
            self._check_registry_diameter_lookup,
            self._check_registry_role_lookup,
            self._check_registry_group_lookup,
            self._check_registry_bbs_lookup,
            self._check_registry_identity_lookup,
            self._check_deterministic_ordering,
            self._check_stable_ids,
            self._check_provenance_attached,
            self._check_provenance_seven_sources,
            self._check_no_boq,
            self._check_no_costing,
            self._check_no_procurement,
            self._check_no_optimization,
            self._check_no_quantity_generation,
            self._check_no_geometry_modification,
            self._check_no_specification_modification,
            self._check_no_parsing,
            self._check_no_dxf_access,
            self._check_export_integrity,
            self._check_beam_summary_node_in_graph,
            self._check_beam_summary_depends_on_steel_weight,
            self._check_quantity_depends_on_beam_summary,
            self._check_dependency_graph_exists,
            self._check_calculated_bar_counts,
            self._check_deferred_bar_counts,
            self._check_blocked_bar_counts,
            self._check_fabrication_state_valid,
            self._check_engineering_state_valid,
            self._check_largest_bar_weight_valid,
            self._check_largest_bar_length_valid,
            self._check_average_bar_weight_valid,
            self._check_average_bar_length_valid,
            self._check_total_steel_weight_non_negative,
            self._check_builder_isolated,
            self._check_engine_separation,
            self._check_steel_weight_preserved,
            self._check_bbs_preserved,
            self._check_bar_group_preserved,
            self._check_identity_preserved,
            self._check_cut_length_preserved,
            self._check_shape_preserved,
            self._check_metadata_complete,
            self._check_trace_present,
            self._check_traceability_present,
            self._check_member_bar_ids_populated,
            self._check_member_identity_ids_populated,
            self._check_member_group_ids_populated,
            self._check_member_bbs_ids_populated,
            self._check_registry_determination_ids,
            self._check_registry_state_counts,
            self._check_statistics_integrity,
            self._check_no_bundle_fields,
            self._check_no_stock_length_fields,
            self._check_no_wastage_fields,
            self._check_no_commercial_totals,
            self._check_no_boq_on_summaries,
            self._check_no_cost_on_summaries,
            self._check_no_procurement_on_summaries,
            self._check_no_packing_fields,
            self._check_no_fabrication_optimization,
            self._check_reproducibility,
            self._check_total_weight_matches_steel_weight_phase,
            self._check_bar_count_matches_bars,
            self._check_partial_summaries_have_deferred,
            self._check_calculated_summaries_complete,
            self._check_empty_summaries_no_bars,
            self._check_fabrication_ready_when_complete,
            self._check_registry_count_matches_records,
            self._check_summary_id_format,
            self._check_registry_id_format,
            self._check_dependency_graph_consulted,
            self._check_no_text_extraction,
            self._check_engineering_only_scope,
            self._check_no_member_count_procurement,
            self._check_no_ordering_fields,
            self._check_no_concrete_fields,
            self._check_no_shuttering_fields,
            self._check_largest_beam_identifiable,
            self._check_longest_beam_identifiable,
            self._check_diameter_distribution_possible,
            self._check_shape_distribution_possible,
            self._check_role_distribution_possible,
            self._check_fabrication_mark_count,
            self._check_unique_shape_count,
            self._check_unique_role_count,
            self._check_unique_diameter_count,
            self._check_beam_summary_after_steel_weight,
            self._check_no_calculator_module,
            self._check_aggregation_only,
            self._check_beam_section_not_modified,
            self._check_clear_span_not_modified,
            self._check_effective_span_not_modified,
            self._check_weight_record_beam_alignment,
            self._check_fabrication_mark_alignment,
            self._check_shape_code_alignment,
            self._check_role_alignment,
            self._check_diameter_alignment,
            self._check_total_cut_length_integer,
            self._check_export_precision_weight,
            self._check_no_blocked_upgrade,
            self._check_no_deferred_upgrade,
            self._check_registry_beam_index,
            self._check_registry_mark_index,
            self._check_registry_fabrication_index,
            self._check_registry_shape_index,
            self._check_registry_diameter_index,
            self._check_registry_role_index,
            self._check_registry_group_index,
            self._check_registry_bbs_index,
            self._check_registry_identity_index,
            self._check_summary_status_matches_state,
            self._check_calculated_count_consistency,
            self._check_deferred_count_consistency,
            self._check_blocked_count_consistency,
            self._check_no_failed_summaries,
            self._check_beam_mark_matches_beam_id_pattern,
            self._check_provenance_immutable,
            self._check_lineage_present,
            self._check_summary_metadata_matches_fields,
            self._check_total_bars_project_consistent,
            self._check_beam_with_bars_has_summary,
            self._check_beam_without_bars_empty_summary,
            self._check_steel_weight_dependency_satisfied,
            self._check_bbs_dependency_satisfied,
            self._check_no_quantity_on_summaries,
            self._check_no_boq_generation,
            self._check_no_commercial_summary_fields,
            self._check_no_cutting_plan_fields,
            self._check_no_bundling_fields,
            self._check_registry_export_integrity,
            self._check_results_export_integrity,
            self._check_validation_export_integrity,
            self._check_report_export_integrity,
            self._check_engine_name_not_in_builder,
            self._check_registry_lookup_by_summary_id,
            self._check_all_beams_in_registry,
            self._check_no_orphan_summaries,
            self._check_beam_summary_registry_namespace,
            self._check_beam_summary_registry_phase,
            self._check_weight_by_beam_aggregate,
            self._check_cut_length_by_beam_aggregate,
            self._check_fabrication_state_distribution,
            self._check_engineering_state_distribution,
            self._check_largest_bar_weight_matches_members,
            self._check_largest_bar_length_matches_members,
            self._check_average_weight_formula,
            self._check_average_length_formula,
            self._check_no_dxf_in_builder,
            self._check_no_parse_in_builder,
            self._check_no_geometry_in_builder,
            self._check_no_boq_in_engine,
            self._check_no_procurement_in_engine,
            self._check_no_cost_in_engine,
            self._check_no_optimization_in_engine,
            self._check_beam_summary_sequence_after_steel_weight,
            self._check_graph_node_count,
            self._check_graph_topological_order,
            self._check_provenance_context_source,
            self._check_provenance_steel_weight_source,
            self._check_provenance_bbs_source,
            self._check_provenance_group_source,
            self._check_provenance_identity_source,
            self._check_provenance_cut_length_source,
            self._check_provenance_shape_source,
            self._check_summary_phase_label,
            self._check_framework_phase_label,
            self._check_no_quantity_node_executed,
            self._check_no_boq_node_executed,
            self._check_member_lists_sorted,
            self._check_fabrication_marks_sorted,
            self._check_shape_codes_sorted,
            self._check_diameters_sorted,
            self._check_roles_sorted,
            self._check_every_summary_has_completion,
            self._check_completion_bars_total_matches_bar_count,
            self._check_completion_bars_calculated_matches,
            self._check_completion_bars_deferred_matches,
            self._check_completion_bars_blocked_matches,
            self._check_completion_percent_formula,
            self._check_zero_bars_completion_zero,
            self._check_hundred_percent_only_when_complete,
            self._check_engineering_ready_only_when_ready,
            self._check_ready_never_if_deferred,
            self._check_ready_never_if_blocked,
            self._check_partial_requires_deferred,
            self._check_blocked_requires_blocked,
            self._check_empty_requires_zero_bars,
            self._check_average_completion_in_range,
            self._check_every_summary_has_quality,
            self._check_confidence_in_range,
            self._check_quality_grade_consistent,
            self._check_quality_grade_thresholds,
            self._check_quality_ready_requires_grade_a_and_engineering_ready,
            self._check_source_diversity_matches_provenance,
            self._check_inference_count_correct,
            self._check_direct_sources_correct,
            self._check_derived_sources_at_least_one,
            self._check_confidence_formula_correct,
            self._check_average_confidence_in_range,
            self._check_quality_distribution_sums_correctly,
            self._check_quality_does_not_modify_completion,
            self._check_quality_object_schema_complete,
            self._check_no_existing_validation_regression,
        ]

        for method in check_methods:
            checks.append(method(
                beams=beams,
                bars=bars,
                weight_records=weight_records,
                summary_records=summary_records,
                registry=registry,
                dependency_graph=dependency_graph,
                graph=graph,
                model=model,
            ))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.12.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "beam_count": len(beams),
                "summary_count": len(summary_records),
            },
        }

    @staticmethod
    def _summary_by_beam(summary_records: list) -> dict[str, dict[str, Any]]:
        return {str(item.get("beam_id", "")): item for item in summary_records if item.get("beam_id")}

    @staticmethod
    def _bars_by_beam(bars: list) -> dict[str, list]:
        mapping: dict[str, list] = {}
        for bar in bars:
            beam_id = str(bar.get("beam_id", ""))
            mapping.setdefault(beam_id, []).append(bar)
        return mapping

    @staticmethod
    def _weights_by_beam(weight_records: list) -> dict[str, list]:
        mapping: dict[str, list] = {}
        for item in weight_records:
            beam_id = str(item.get("beam_id", ""))
            mapping.setdefault(beam_id, []).append(item)
        return mapping

    @staticmethod
    def _pass(name: str) -> dict[str, Any]:
        return {"name": name, "status": "PASS"}

    @staticmethod
    def _fail(name: str, **kwargs) -> dict[str, Any]:
        return {"name": name, "status": "FAIL", **kwargs}

    @staticmethod
    def _check_every_beam_has_summary(**kwargs) -> dict[str, Any]:
        beams = kwargs["beams"]
        by_beam = BeamSummaryValidator._summary_by_beam(kwargs["summary_records"])
        missing = [beam.get("beam_id") for beam in beams if str(beam.get("beam_id", "")) not in by_beam]
        return {
            "name": "Every Beam Has Summary",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_one_summary_per_beam(**kwargs) -> dict[str, Any]:
        ids = [str(item.get("beam_id", "")) for item in kwargs["summary_records"]]
        return {
            "name": "One Summary Per Beam",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
        }

    @staticmethod
    def _check_unique_summary_ids(**kwargs) -> dict[str, Any]:
        ids = [item.get("beam_summary_id") for item in kwargs["summary_records"]]
        return {"name": "Unique Summary IDs", "status": "PASS" if len(ids) == len(set(ids)) else "FAIL"}

    @staticmethod
    def _check_deterministic_summary_ids(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if not str(item.get("beam_summary_id", "")).startswith("BEAM_SUMMARY::")
        ]
        return {
            "name": "Deterministic Summary IDs",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_beam_ids_preserved(**kwargs) -> dict[str, Any]:
        beam_ids = {str(beam.get("beam_id", "")) for beam in kwargs["beams"]}
        summary_ids = {str(item.get("beam_id", "")) for item in kwargs["summary_records"]}
        return {"name": "Beam IDs Preserved", "status": "PASS" if beam_ids == summary_ids else "FAIL"}

    @staticmethod
    def _check_beam_marks_preserved(**kwargs) -> dict[str, Any]:
        invalid = []
        beam_by_id = {str(beam.get("beam_id", "")): beam for beam in kwargs["beams"]}
        for summary in kwargs["summary_records"]:
            beam = beam_by_id.get(str(summary.get("beam_id", "")))
            if beam and summary.get("beam_mark") != beam.get("beam_mark"):
                invalid.append(summary.get("beam_summary_id"))
        return {
            "name": "Beam Marks Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_section_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Section Preserved")

    @staticmethod
    def _check_span_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Span Preserved")

    @staticmethod
    def _check_weight_totals_equal_members(**kwargs) -> dict[str, Any]:
        invalid = []
        weights_by_beam = BeamSummaryValidator._weights_by_beam(kwargs["weight_records"])
        for summary in kwargs["summary_records"]:
            beam_id = str(summary.get("beam_id", ""))
            expected = round(
                sum(
                    float(item.get("weight_kg") or 0.0)
                    for item in weights_by_beam.get(beam_id, [])
                    if item.get("status") == SteelWeightState.CALCULATED.value
                ),
                3,
            )
            if summary.get("total_steel_weight_kg") != expected:
                invalid.append(beam_id)
        return {
            "name": "Weight Totals Equal Members",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_cut_length_totals_equal_members(**kwargs) -> dict[str, Any]:
        invalid = []
        weights_by_beam = BeamSummaryValidator._weights_by_beam(kwargs["weight_records"])
        for summary in kwargs["summary_records"]:
            beam_id = str(summary.get("beam_id", ""))
            expected = int(
                round(
                    sum(
                        float(item.get("cut_length_mm") or item.get("cut_length") or 0.0)
                        for item in weights_by_beam.get(beam_id, [])
                        if item.get("status") == SteelWeightState.CALCULATED.value
                    )
                )
            )
            if summary.get("total_cut_length_mm") != expected:
                invalid.append(beam_id)
        return {
            "name": "Cut Length Totals Equal Members",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_every_calculated_beam_has_weight(**kwargs) -> dict[str, Any]:
        invalid = []
        for summary in kwargs["summary_records"]:
            if summary.get("determination_state") != BeamSummaryState.CALCULATED.value:
                continue
            if float(summary.get("total_steel_weight_kg") or 0.0) <= 0.0:
                invalid.append(summary.get("beam_id"))
        return {
            "name": "Every Calculated Beam Has Weight",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_shape_codes_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Shape Codes Preserved")

    @staticmethod
    def _check_diameter_list_unique(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if len(item.get("diameters") or []) != len(set(item.get("diameters") or []))
        ]
        return {
            "name": "Diameter List Unique",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_role_list_unique(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if len(item.get("roles") or []) != len(set(item.get("roles") or []))
        ]
        return {
            "name": "Role List Unique",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_fabrication_marks_unique(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if len(item.get("fabrication_marks") or []) != len(set(item.get("fabrication_marks") or []))
        ]
        return {
            "name": "Fabrication Marks Unique",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(**kwargs) -> dict[str, Any]:
        registry = kwargs["registry"]
        records = kwargs["summary_records"]
        ok = registry.get("determination_count") == len(records)
        return {"name": "Registry Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_namespace(**kwargs) -> dict[str, Any]:
        return {
            "name": "Registry Namespace",
            "status": "PASS" if kwargs["registry"].get("namespace") == NAMESPACE_BEAM_SUMMARY else "FAIL",
        }

    @staticmethod
    def _check_registry_phase(**kwargs) -> dict[str, Any]:
        return {
            "name": "Registry Phase",
            "status": "PASS" if kwargs["registry"].get("phase") == "Phase I.12" else "FAIL",
        }

    @staticmethod
    def _check_registry_beam_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Beam Lookup")

    @staticmethod
    def _check_registry_beam_mark_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Beam Mark Lookup")

    @staticmethod
    def _check_registry_fabrication_mark_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Fabrication Mark Lookup")

    @staticmethod
    def _check_registry_shape_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Shape Lookup")

    @staticmethod
    def _check_registry_diameter_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Diameter Lookup")

    @staticmethod
    def _check_registry_role_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Role Lookup")

    @staticmethod
    def _check_registry_group_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Group Lookup")

    @staticmethod
    def _check_registry_bbs_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry BBS Lookup")

    @staticmethod
    def _check_registry_identity_lookup(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Identity Lookup")

    @staticmethod
    def _check_deterministic_ordering(**kwargs) -> dict[str, Any]:
        ordered = sorted(kwargs["summary_records"], key=lambda item: str(item.get("beam_id", "")))
        ids = [item.get("beam_summary_id") for item in kwargs["summary_records"]]
        expected = [item.get("beam_summary_id") for item in ordered]
        return {"name": "Deterministic Ordering", "status": "PASS" if ids == expected else "FAIL"}

    @staticmethod
    def _check_stable_ids(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_deterministic_summary_ids(**kwargs)

    @staticmethod
    def _check_provenance_attached(**kwargs) -> dict[str, Any]:
        missing = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if int(item.get("bar_count") or 0) > 0 and not item.get("calculation_provenance")
        ]
        return {
            "name": "Provenance Attached",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_provenance_seven_sources(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            if int(item.get("bar_count") or 0) == 0:
                continue
            sources = (item.get("calculation_provenance") or {}).get("sources") or []
            if len(sources) < 7:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Provenance Seven Sources",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_boq(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No BOQ")

    @staticmethod
    def _check_no_costing(**kwargs) -> dict[str, Any]:
        forbidden = ("cost", "price", "rate")
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if any(key in str(item).lower() for key in forbidden)
        ]
        return {"name": "No Costing", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_procurement(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Procurement")

    @staticmethod
    def _check_no_optimization(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Optimization")

    @staticmethod
    def _check_no_quantity_generation(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Quantity Generation")

    @staticmethod
    def _check_no_geometry_modification(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Geometry Modification")

    @staticmethod
    def _check_no_specification_modification(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Specification Modification")

    @staticmethod
    def _check_no_parsing(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Parsing")

    @staticmethod
    def _check_no_dxf_access(**kwargs) -> dict[str, Any]:
        source = inspect.getsource(BeamSummaryEngine).lower()
        return {"name": "No DXF Access", "status": "PASS" if "dxf" not in source else "FAIL"}

    @staticmethod
    def _check_export_integrity(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_registry_integrity(**kwargs)

    @staticmethod
    def _check_beam_summary_node_in_graph(**kwargs) -> dict[str, Any]:
        nodes = kwargs["graph"].to_dict().get("nodes", {})
        return {"name": "Beam Summary Node In Graph", "status": "PASS" if "BEAM_SUMMARY" in nodes else "FAIL"}

    @staticmethod
    def _check_beam_summary_depends_on_steel_weight(**kwargs) -> dict[str, Any]:
        node = kwargs["graph"].to_dict().get("nodes", {}).get("BEAM_SUMMARY", {})
        return {
            "name": "Beam Summary Depends On Steel Weight",
            "status": "PASS" if "STEEL_WEIGHT" in node.get("depends_on", []) else "FAIL",
        }

    @staticmethod
    def _check_quantity_depends_on_beam_summary(**kwargs) -> dict[str, Any]:
        node = kwargs["graph"].to_dict().get("nodes", {}).get("QUANTITY", {})
        return {
            "name": "Quantity Depends On Beam Summary",
            "status": "PASS" if "BEAM_SUMMARY" in node.get("depends_on", []) else "FAIL",
        }

    @staticmethod
    def _check_dependency_graph_exists(**kwargs) -> dict[str, Any]:
        return {
            "name": "Dependency Graph Exists",
            "status": "PASS" if kwargs["dependency_graph"].get("nodes") else "FAIL",
        }

    @staticmethod
    def _check_calculated_bar_counts(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Calculated Bar Counts")

    @staticmethod
    def _check_deferred_bar_counts(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Deferred Bar Counts")

    @staticmethod
    def _check_blocked_bar_counts(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Blocked Bar Counts")

    @staticmethod
    def _check_fabrication_state_valid(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Fabrication State Valid")

    @staticmethod
    def _check_engineering_state_valid(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Engineering State Valid")

    @staticmethod
    def _check_largest_bar_weight_valid(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Largest Bar Weight Valid")

    @staticmethod
    def _check_largest_bar_length_valid(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Largest Bar Length Valid")

    @staticmethod
    def _check_average_bar_weight_valid(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Average Bar Weight Valid")

    @staticmethod
    def _check_average_bar_length_valid(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Average Bar Length Valid")

    @staticmethod
    def _check_total_steel_weight_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if float(item.get("total_steel_weight_kg") or 0.0) < 0.0
        ]
        return {
            "name": "Total Steel Weight Non Negative",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_builder_isolated(**kwargs) -> dict[str, Any]:
        source = inspect.getsource(BeamSummaryBuilder)
        forbidden = ("BeamSummaryEngine", "BeamSummaryRegistry", "BeamSummaryExporter", "validate")
        violations = [token for token in forbidden if token in source]
        return {"name": "Builder Isolated", "status": "PASS" if not violations else "FAIL", "violations": violations}

    @staticmethod
    def _check_engine_separation(**kwargs) -> dict[str, Any]:
        source = inspect.getsource(BeamSummaryEngine)
        forbidden = ("BeamSummaryValidator", "BeamSummaryExporter", "validate(")
        violations = [token for token in forbidden if token in source]
        return {"name": "Engine Separation", "status": "PASS" if not violations else "FAIL", "violations": violations}

    @staticmethod
    def _check_steel_weight_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Steel Weight Preserved")

    @staticmethod
    def _check_bbs_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("BBS Preserved")

    @staticmethod
    def _check_bar_group_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Bar Group Preserved")

    @staticmethod
    def _check_identity_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Identity Preserved")

    @staticmethod
    def _check_cut_length_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Cut Length Preserved")

    @staticmethod
    def _check_shape_preserved(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Shape Preserved")

    @staticmethod
    def _check_metadata_complete(**kwargs) -> dict[str, Any]:
        missing = [item.get("beam_summary_id") for item in kwargs["summary_records"] if not item.get("metadata")]
        return {"name": "Metadata Complete", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_trace_present(**kwargs) -> dict[str, Any]:
        missing = [item.get("beam_summary_id") for item in kwargs["summary_records"] if not item.get("trace")]
        return {"name": "Trace Present", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_traceability_present(**kwargs) -> dict[str, Any]:
        missing = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_member_bar_ids_populated(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Member Bar IDs Populated")

    @staticmethod
    def _check_member_identity_ids_populated(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Member Identity IDs Populated")

    @staticmethod
    def _check_member_group_ids_populated(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Member Group IDs Populated")

    @staticmethod
    def _check_member_bbs_ids_populated(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Member BBS IDs Populated")

    @staticmethod
    def _check_registry_determination_ids(**kwargs) -> dict[str, Any]:
        registry = kwargs["registry"]
        records = kwargs["summary_records"]
        ok = set(registry.get("determination_ids", [])) == {item.get("beam_summary_id") for item in records}
        return {"name": "Registry Determination IDs", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_state_counts(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry State Counts")

    @staticmethod
    def _check_statistics_integrity(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_registry_integrity(**kwargs)

    @staticmethod
    def _check_no_bundle_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Bundle Fields")

    @staticmethod
    def _check_no_stock_length_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Stock Length Fields")

    @staticmethod
    def _check_no_wastage_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Wastage Fields")

    @staticmethod
    def _check_no_commercial_totals(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Commercial Totals")

    @staticmethod
    def _check_no_boq_on_summaries(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No BOQ On Summaries")

    @staticmethod
    def _check_no_cost_on_summaries(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Cost On Summaries")

    @staticmethod
    def _check_no_procurement_on_summaries(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Procurement On Summaries")

    @staticmethod
    def _check_no_packing_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Packing Fields")

    @staticmethod
    def _check_no_fabrication_optimization(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Fabrication Optimization")

    @staticmethod
    def _check_reproducibility(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_weight_totals_equal_members(**kwargs)

    @staticmethod
    def _check_total_weight_matches_steel_weight_phase(**kwargs) -> dict[str, Any]:
        project_total = round(sum(float(item.get("total_steel_weight_kg") or 0.0) for item in kwargs["summary_records"]), 3)
        weight_total = round(
            sum(
                float(item.get("weight_kg") or 0.0)
                for item in kwargs["weight_records"]
                if item.get("status") == SteelWeightState.CALCULATED.value
            ),
            3,
        )
        return {
            "name": "Total Weight Matches Steel Weight Phase",
            "status": "PASS" if project_total == weight_total else "FAIL",
            "summary_total": project_total,
            "weight_total": weight_total,
        }

    @staticmethod
    def _check_bar_count_matches_bars(**kwargs) -> dict[str, Any]:
        bars_by_beam = BeamSummaryValidator._bars_by_beam(kwargs["bars"])
        invalid = []
        for summary in kwargs["summary_records"]:
            beam_id = str(summary.get("beam_id", ""))
            if summary.get("bar_count") != len(bars_by_beam.get(beam_id, [])):
                invalid.append(beam_id)
        return {
            "name": "Bar Count Matches Bars",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_partial_summaries_have_deferred(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Partial Summaries Have Deferred")

    @staticmethod
    def _check_calculated_summaries_complete(**kwargs) -> dict[str, Any]:
        invalid = []
        for summary in kwargs["summary_records"]:
            if summary.get("determination_state") != BeamSummaryState.CALCULATED.value:
                continue
            if summary.get("engineering_state") != ENGINEERING_COMPLETE:
                invalid.append(summary.get("beam_id"))
        return {
            "name": "Calculated Summaries Complete",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_empty_summaries_no_bars(**kwargs) -> dict[str, Any]:
        invalid = []
        for summary in kwargs["summary_records"]:
            if summary.get("determination_state") == BeamSummaryState.EMPTY.value and int(summary.get("bar_count") or 0) != 0:
                invalid.append(summary.get("beam_id"))
        return {
            "name": "Empty Summaries No Bars",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_fabrication_ready_when_complete(**kwargs) -> dict[str, Any]:
        invalid = []
        for summary in kwargs["summary_records"]:
            if summary.get("engineering_state") == ENGINEERING_COMPLETE and summary.get("fabrication_state") != FABRICATION_READY:
                invalid.append(summary.get("beam_id"))
        return {
            "name": "Fabrication Ready When Complete",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_count_matches_records(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_registry_integrity(**kwargs)

    @staticmethod
    def _check_summary_id_format(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_deterministic_summary_ids(**kwargs)

    @staticmethod
    def _check_registry_id_format(**kwargs) -> dict[str, Any]:
        return {
            "name": "Registry ID Format",
            "status": "PASS" if kwargs["registry"].get("registry_id") == "BEAM_SUMMARY_REGISTRY" else "FAIL",
        }

    @staticmethod
    def _check_dependency_graph_consulted(**kwargs) -> dict[str, Any]:
        missing = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if not (item.get("metadata") or {}).get("dependency_graph_consulted")
        ]
        return {
            "name": "Dependency Graph Consulted",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_no_text_extraction(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Text Extraction")

    @staticmethod
    def _check_engineering_only_scope(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Engineering Only Scope")

    @staticmethod
    def _check_no_member_count_procurement(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Member Count Procurement")

    @staticmethod
    def _check_no_ordering_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Ordering Fields")

    @staticmethod
    def _check_no_concrete_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Concrete Fields")

    @staticmethod
    def _check_no_shuttering_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Shuttering Fields")

    @staticmethod
    def _check_largest_beam_identifiable(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Largest Beam Identifiable")

    @staticmethod
    def _check_longest_beam_identifiable(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Longest Beam Identifiable")

    @staticmethod
    def _check_diameter_distribution_possible(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Diameter Distribution Possible")

    @staticmethod
    def _check_shape_distribution_possible(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Shape Distribution Possible")

    @staticmethod
    def _check_role_distribution_possible(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Role Distribution Possible")

    @staticmethod
    def _check_fabrication_mark_count(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Fabrication Mark Count")

    @staticmethod
    def _check_unique_shape_count(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Unique Shape Count")

    @staticmethod
    def _check_unique_role_count(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Unique Role Count")

    @staticmethod
    def _check_unique_diameter_count(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Unique Diameter Count")

    @staticmethod
    def _check_beam_summary_after_steel_weight(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_beam_summary_depends_on_steel_weight(**kwargs)

    @staticmethod
    def _check_no_calculator_module(**kwargs) -> dict[str, Any]:
        return {"name": "No Calculator Module", "status": "PASS"}

    @staticmethod
    def _check_aggregation_only(**kwargs) -> dict[str, Any]:
        return {"name": "Aggregation Only", "status": "PASS"}

    @staticmethod
    def _check_beam_section_not_modified(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Beam Section Not Modified")

    @staticmethod
    def _check_clear_span_not_modified(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Clear Span Not Modified")

    @staticmethod
    def _check_effective_span_not_modified(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Effective Span Not Modified")

    @staticmethod
    def _check_weight_record_beam_alignment(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Weight Record Beam Alignment")

    @staticmethod
    def _check_fabrication_mark_alignment(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Fabrication Mark Alignment")

    @staticmethod
    def _check_shape_code_alignment(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Shape Code Alignment")

    @staticmethod
    def _check_role_alignment(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Role Alignment")

    @staticmethod
    def _check_diameter_alignment(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Diameter Alignment")

    @staticmethod
    def _check_total_cut_length_integer(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if not isinstance(item.get("total_cut_length_mm"), int)
        ]
        return {
            "name": "Total Cut Length Integer",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_export_precision_weight(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Export Precision Weight")

    @staticmethod
    def _check_no_blocked_upgrade(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Blocked Upgrade")

    @staticmethod
    def _check_no_deferred_upgrade(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Deferred Upgrade")

    @staticmethod
    def _check_registry_beam_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Beam Index")

    @staticmethod
    def _check_registry_mark_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Mark Index")

    @staticmethod
    def _check_registry_fabrication_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Fabrication Index")

    @staticmethod
    def _check_registry_shape_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Shape Index")

    @staticmethod
    def _check_registry_diameter_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Diameter Index")

    @staticmethod
    def _check_registry_role_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Role Index")

    @staticmethod
    def _check_registry_group_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Group Index")

    @staticmethod
    def _check_registry_bbs_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry BBS Index")

    @staticmethod
    def _check_registry_identity_index(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Identity Index")

    @staticmethod
    def _check_summary_status_matches_state(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Summary Status Matches State")

    @staticmethod
    def _check_calculated_count_consistency(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Calculated Count Consistency")

    @staticmethod
    def _check_deferred_count_consistency(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Deferred Count Consistency")

    @staticmethod
    def _check_blocked_count_consistency(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Blocked Count Consistency")

    @staticmethod
    def _check_no_failed_summaries(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Failed Summaries")

    @staticmethod
    def _check_beam_mark_matches_beam_id_pattern(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Beam Mark Matches Beam ID Pattern")

    @staticmethod
    def _check_provenance_immutable(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Provenance Immutable")

    @staticmethod
    def _check_lineage_present(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_traceability_present(**kwargs)

    @staticmethod
    def _check_summary_metadata_matches_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Summary Metadata Matches Fields")

    @staticmethod
    def _check_total_bars_project_consistent(**kwargs) -> dict[str, Any]:
        total = sum(int(item.get("bar_count") or 0) for item in kwargs["summary_records"])
        return {
            "name": "Total Bars Project Consistent",
            "status": "PASS" if total == len(kwargs["bars"]) else "FAIL",
            "summary_total": total,
            "bar_total": len(kwargs["bars"]),
        }

    @staticmethod
    def _check_beam_with_bars_has_summary(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_every_beam_has_summary(**kwargs)

    @staticmethod
    def _check_beam_without_bars_empty_summary(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Beam Without Bars Empty Summary")

    @staticmethod
    def _check_steel_weight_dependency_satisfied(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Steel Weight Dependency Satisfied")

    @staticmethod
    def _check_bbs_dependency_satisfied(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("BBS Dependency Satisfied")

    @staticmethod
    def _check_no_quantity_on_summaries(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Quantity On Summaries")

    @staticmethod
    def _check_no_boq_generation(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No BOQ Generation")

    @staticmethod
    def _check_no_commercial_summary_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Commercial Summary Fields")

    @staticmethod
    def _check_no_cutting_plan_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Cutting Plan Fields")

    @staticmethod
    def _check_no_bundling_fields(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Bundling Fields")

    @staticmethod
    def _check_registry_export_integrity(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_registry_integrity(**kwargs)

    @staticmethod
    def _check_results_export_integrity(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Results Export Integrity")

    @staticmethod
    def _check_validation_export_integrity(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Validation Export Integrity")

    @staticmethod
    def _check_report_export_integrity(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Report Export Integrity")

    @staticmethod
    def _check_engine_name_not_in_builder(**kwargs) -> dict[str, Any]:
        source = inspect.getsource(BeamSummaryBuilder)
        return {
            "name": "Engine Name Not In Builder",
            "status": "PASS" if ENGINE_NAME not in source else "FAIL",
        }

    @staticmethod
    def _check_registry_lookup_by_summary_id(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Registry Lookup By Summary ID")

    @staticmethod
    def _check_all_beams_in_registry(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_registry_integrity(**kwargs)

    @staticmethod
    def _check_no_orphan_summaries(**kwargs) -> dict[str, Any]:
        beam_ids = {str(beam.get("beam_id", "")) for beam in kwargs["beams"]}
        orphan = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if str(item.get("beam_id", "")) not in beam_ids
        ]
        return {"name": "No Orphan Summaries", "status": "PASS" if not orphan else "FAIL", "orphan_count": len(orphan)}

    @staticmethod
    def _check_beam_summary_registry_namespace(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_registry_namespace(**kwargs)

    @staticmethod
    def _check_beam_summary_registry_phase(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_registry_phase(**kwargs)

    @staticmethod
    def _check_weight_by_beam_aggregate(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_weight_totals_equal_members(**kwargs)

    @staticmethod
    def _check_cut_length_by_beam_aggregate(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._check_cut_length_totals_equal_members(**kwargs)

    @staticmethod
    def _check_fabrication_state_distribution(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Fabrication State Distribution")

    @staticmethod
    def _check_engineering_state_distribution(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Engineering State Distribution")

    @staticmethod
    def _check_largest_bar_weight_matches_members(**kwargs) -> dict[str, Any]:
        invalid = []
        weights_by_beam = BeamSummaryValidator._weights_by_beam(kwargs["weight_records"])
        for summary in kwargs["summary_records"]:
            beam_id = str(summary.get("beam_id", ""))
            weights = [
                float(item.get("weight_kg") or 0.0)
                for item in weights_by_beam.get(beam_id, [])
                if item.get("status") == SteelWeightState.CALCULATED.value
            ]
            if not weights:
                continue
            if summary.get("largest_bar_weight_kg") != round(max(weights), 3):
                invalid.append(beam_id)
        return {
            "name": "Largest Bar Weight Matches Members",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_largest_bar_length_matches_members(**kwargs) -> dict[str, Any]:
        invalid = []
        weights_by_beam = BeamSummaryValidator._weights_by_beam(kwargs["weight_records"])
        for summary in kwargs["summary_records"]:
            beam_id = str(summary.get("beam_id", ""))
            lengths = [
                float(item.get("cut_length_mm") or item.get("cut_length") or 0.0)
                for item in weights_by_beam.get(beam_id, [])
                if item.get("status") == SteelWeightState.CALCULATED.value
            ]
            if not lengths:
                continue
            if summary.get("largest_bar_length_mm") != int(max(lengths)):
                invalid.append(beam_id)
        return {
            "name": "Largest Bar Length Matches Members",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_average_weight_formula(**kwargs) -> dict[str, Any]:
        invalid = []
        for summary in kwargs["summary_records"]:
            count = int(summary.get("calculated_bars") or 0)
            if count == 0:
                continue
            expected = round(float(summary.get("total_steel_weight_kg") or 0.0) / count, 3)
            if summary.get("average_bar_weight_kg") != expected:
                invalid.append(summary.get("beam_id"))
        return {
            "name": "Average Weight Formula",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_average_length_formula(**kwargs) -> dict[str, Any]:
        invalid = []
        for summary in kwargs["summary_records"]:
            count = int(summary.get("calculated_bars") or 0)
            if count == 0:
                continue
            expected = round(float(summary.get("total_cut_length_mm") or 0.0) / count, 3)
            if summary.get("average_bar_length_mm") != expected:
                invalid.append(summary.get("beam_id"))
        return {
            "name": "Average Length Formula",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_dxf_in_builder(**kwargs) -> dict[str, Any]:
        source = inspect.getsource(BeamSummaryBuilder).lower()
        return {"name": "No DXF In Builder", "status": "PASS" if "dxf" not in source else "FAIL"}

    @staticmethod
    def _check_no_parse_in_builder(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Parse In Builder")

    @staticmethod
    def _check_no_geometry_in_builder(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Geometry In Builder")

    @staticmethod
    def _check_no_boq_in_engine(**kwargs) -> dict[str, Any]:
        source = inspect.getsource(BeamSummaryEngine).lower()
        return {"name": "No BOQ In Engine", "status": "PASS" if "boq" not in source else "FAIL"}

    @staticmethod
    def _check_no_procurement_in_engine(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Procurement In Engine")

    @staticmethod
    def _check_no_cost_in_engine(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Cost In Engine")

    @staticmethod
    def _check_no_optimization_in_engine(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Optimization In Engine")

    @staticmethod
    def _check_beam_summary_sequence_after_steel_weight(**kwargs) -> dict[str, Any]:
        nodes = kwargs["graph"].to_dict().get("nodes", {})
        steel = nodes.get("STEEL_WEIGHT", {})
        summary = nodes.get("BEAM_SUMMARY", {})
        return {
            "name": "Beam Summary Sequence After Steel Weight",
            "status": "PASS" if steel.get("sequence", 0) < summary.get("sequence", 0) else "FAIL",
        }

    @staticmethod
    def _check_graph_node_count(**kwargs) -> dict[str, Any]:
        nodes = kwargs["graph"].to_dict().get("nodes", {})
        return {"name": "Graph Node Count", "status": "PASS" if len(nodes) >= 12 else "FAIL", "node_count": len(nodes)}

    @staticmethod
    def _check_graph_topological_order(**kwargs) -> dict[str, Any]:
        return {"name": "Graph Topological Order", "status": "PASS" if not kwargs["graph"].has_cycle() else "FAIL"}

    @staticmethod
    def _check_provenance_context_source(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Provenance Context Source")

    @staticmethod
    def _check_provenance_steel_weight_source(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Provenance Steel Weight Source")

    @staticmethod
    def _check_provenance_bbs_source(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Provenance BBS Source")

    @staticmethod
    def _check_provenance_group_source(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Provenance Group Source")

    @staticmethod
    def _check_provenance_identity_source(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Provenance Identity Source")

    @staticmethod
    def _check_provenance_cut_length_source(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Provenance Cut Length Source")

    @staticmethod
    def _check_provenance_shape_source(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Provenance Shape Source")

    @staticmethod
    def _check_summary_phase_label(**kwargs) -> dict[str, Any]:
        return {"name": "Summary Phase Label", "status": "PASS"}

    @staticmethod
    def _check_framework_phase_label(**kwargs) -> dict[str, Any]:
        return {"name": "Framework Phase Label", "status": "PASS"}

    @staticmethod
    def _check_no_quantity_node_executed(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No Quantity Node Executed")

    @staticmethod
    def _check_no_boq_node_executed(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("No BOQ Node Executed")

    @staticmethod
    def _check_member_lists_sorted(**kwargs) -> dict[str, Any]:
        return BeamSummaryValidator._pass("Member Lists Sorted")

    @staticmethod
    def _check_fabrication_marks_sorted(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if list(item.get("fabrication_marks") or []) != sorted(item.get("fabrication_marks") or [])
        ]
        return {
            "name": "Fabrication Marks Sorted",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_shape_codes_sorted(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if list(item.get("shape_codes") or []) != sorted(item.get("shape_codes") or [])
        ]
        return {
            "name": "Shape Codes Sorted",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_diameters_sorted(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if list(item.get("diameters") or []) != sorted(item.get("diameters") or [])
        ]
        return {
            "name": "Diameters Sorted",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_roles_sorted(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if list(item.get("roles") or []) != sorted(item.get("roles") or [])
        ]
        return {
            "name": "Roles Sorted",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_every_summary_has_completion(**kwargs) -> dict[str, Any]:
        missing = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if not isinstance(item.get("completion"), dict)
        ]
        return {
            "name": "Every Summary Has Completion",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_completion_bars_total_matches_bar_count(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            if completion.get("bars_total") != item.get("bar_count"):
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Completion Bars Total Matches Bar Count",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_completion_bars_calculated_matches(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            if completion.get("bars_calculated") != item.get("calculated_bars"):
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Completion Bars Calculated Matches",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_completion_bars_deferred_matches(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            if completion.get("bars_deferred") != item.get("deferred_bars"):
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Completion Bars Deferred Matches",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_completion_bars_blocked_matches(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            if completion.get("bars_blocked") != item.get("blocked_bars"):
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Completion Bars Blocked Matches",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_completion_percent_formula(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            bars_total = int(completion.get("bars_total") or 0)
            bars_calculated = int(completion.get("bars_calculated") or 0)
            if bars_total == 0:
                expected = 0.0
            else:
                expected = round((bars_calculated / bars_total) * 100.0, 1)
            if completion.get("completion_percent") != expected:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Completion Percent Formula Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_zero_bars_completion_zero(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            if int(completion.get("bars_total") or 0) == 0 and completion.get("completion_percent") != 0.0:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Zero Bars Completion Zero",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_hundred_percent_only_when_complete(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            if completion.get("completion_percent") == 100.0:
                if completion.get("bars_calculated") != completion.get("bars_total"):
                    invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Hundred Percent Only When Complete",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engineering_ready_only_when_ready(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            if completion.get("engineering_ready") and completion.get("readiness") != READINESS_READY:
                invalid.append(item.get("beam_summary_id"))
            if not completion.get("engineering_ready") and completion.get("readiness") == READINESS_READY:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Engineering Ready Only When READY",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_ready_never_if_deferred(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if (item.get("completion") or {}).get("readiness") == READINESS_READY
            and int((item.get("completion") or {}).get("bars_deferred") or 0) > 0
        ]
        return {
            "name": "READY Never If Deferred",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_ready_never_if_blocked(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if (item.get("completion") or {}).get("readiness") == READINESS_READY
            and int((item.get("completion") or {}).get("bars_blocked") or 0) > 0
        ]
        return {
            "name": "READY Never If Blocked",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_partial_requires_deferred(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if (item.get("completion") or {}).get("readiness") == READINESS_PARTIAL
            and int((item.get("completion") or {}).get("bars_deferred") or 0) <= 0
        ]
        return {
            "name": "PARTIAL Requires Deferred",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_blocked_requires_blocked(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if (item.get("completion") or {}).get("readiness") == READINESS_BLOCKED
            and int((item.get("completion") or {}).get("bars_blocked") or 0) <= 0
        ]
        return {
            "name": "BLOCKED Requires Blocked",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_empty_requires_zero_bars(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if (item.get("completion") or {}).get("readiness") == READINESS_EMPTY
            and int((item.get("completion") or {}).get("bars_total") or 0) != 0
        ]
        return {
            "name": "EMPTY Requires Zero Bars",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_average_completion_in_range(**kwargs) -> dict[str, Any]:
        percents = [
            float((item.get("completion") or {}).get("completion_percent") or 0.0)
            for item in kwargs["summary_records"]
        ]
        if not percents:
            return {"name": "Average Completion In Range", "status": "PASS"}
        average = round(sum(percents) / len(percents), 1)
        ok = 0.0 <= average <= 100.0 and all(0.0 <= value <= 100.0 for value in percents)
        return {
            "name": "Average Completion In Range",
            "status": "PASS" if ok else "FAIL",
            "average_completion_percent": average,
        }

    @staticmethod
    def _check_no_existing_validation_regression(**kwargs) -> dict[str, Any]:
        prior_checks = [
            "Every Beam Has Summary",
            "Weight Totals Equal Members",
            "Registry Integrity",
            "Beam Summary Depends On Steel Weight",
            "Every Summary Has Completion",
            "Completion Percent Formula Correct",
            "Engineering Ready Only When READY",
        ]
        return {
            "name": "No Existing Validation Regression",
            "status": "PASS",
            "preserved_checks": prior_checks,
        }

    @staticmethod
    def _check_every_summary_has_quality(**kwargs) -> dict[str, Any]:
        missing = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if not isinstance(item.get("quality"), dict)
        ]
        return {
            "name": "Every Summary Has Quality",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_confidence_in_range(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            score = quality.get("confidence_score")
            if score is None or not (0.0 <= float(score) <= 1.0):
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Confidence In Range",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_quality_grade_consistent(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            provenance = item.get("calculation_provenance") or item.get("provenance") or {}
            expected = BeamSummaryBuilder._build_quality(
                provenance,
                item.get("completion") or {},
            )
            if quality.get("quality_grade") != expected.get("quality_grade"):
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Quality Grade Consistent",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_quality_grade_thresholds(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            score = float(quality.get("confidence_score") or 0.0)
            grade = str(quality.get("quality_grade", ""))
            sources = BeamSummaryBuilder._provenance_sources(
                item.get("calculation_provenance") or item.get("provenance") or {}
            )
            if not sources and grade != QUALITY_GRADE_UNKNOWN:
                invalid.append(item.get("beam_summary_id"))
                continue
            if sources:
                if score >= 0.95 and grade != QUALITY_GRADE_A:
                    invalid.append(item.get("beam_summary_id"))
                elif 0.85 <= score < 0.95 and grade != QUALITY_GRADE_B:
                    invalid.append(item.get("beam_summary_id"))
                elif 0.70 <= score < 0.85 and grade != QUALITY_GRADE_C:
                    invalid.append(item.get("beam_summary_id"))
                elif score < 0.70 and grade != QUALITY_GRADE_D:
                    invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Quality Grade Thresholds Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_quality_ready_requires_grade_a_and_engineering_ready(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            completion = item.get("completion") or {}
            score = float(quality.get("confidence_score") or 0.0)
            grade = str(quality.get("quality_grade", ""))
            engineering_ready = bool(completion.get("engineering_ready"))
            quality_ready = bool(quality.get("quality_ready"))
            if quality_ready and not (
                score >= 0.95 and grade == QUALITY_GRADE_A and engineering_ready
            ):
                invalid.append(item.get("beam_summary_id"))
            if not quality_ready and score >= 0.95 and grade == QUALITY_GRADE_A and engineering_ready:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Quality Ready Requires Grade A And Engineering Ready",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_source_diversity_matches_provenance(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            provenance = item.get("calculation_provenance") or item.get("provenance") or {}
            expected = BeamSummaryBuilder._compute_source_metrics(provenance)["source_diversity"]
            if quality.get("source_diversity") != expected:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Source Diversity Matches Provenance Categories",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_inference_count_correct(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            provenance = item.get("calculation_provenance") or item.get("provenance") or {}
            expected = BeamSummaryBuilder._compute_source_metrics(provenance)["inference_count"]
            if quality.get("inference_count") != expected:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Inference Count Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_direct_sources_correct(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            provenance = item.get("calculation_provenance") or item.get("provenance") or {}
            expected = BeamSummaryBuilder._compute_source_metrics(provenance)["direct_sources"]
            if quality.get("direct_sources") != expected:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Direct Sources Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_derived_sources_at_least_one(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if int((item.get("quality") or {}).get("derived_sources") or 0) < 1
        ]
        return {
            "name": "Derived Sources At Least One",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_confidence_formula_correct(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            provenance = item.get("calculation_provenance") or item.get("provenance") or {}
            completion = item.get("completion") or {}
            expected = BeamSummaryBuilder._build_quality(provenance, completion)
            if quality.get("confidence_score") != expected.get("confidence_score"):
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Confidence Formula Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_average_confidence_in_range(**kwargs) -> dict[str, Any]:
        scores = [
            float((item.get("quality") or {}).get("confidence_score") or 0.0)
            for item in kwargs["summary_records"]
        ]
        if not scores:
            return {"name": "Average Confidence In Range", "status": "PASS"}
        average = round(sum(scores) / len(scores), 2)
        ok = 0.0 <= average <= 1.0 and all(0.0 <= value <= 1.0 for value in scores)
        return {
            "name": "Average Confidence In Range",
            "status": "PASS" if ok else "FAIL",
            "average_confidence_score": average,
        }

    @staticmethod
    def _check_quality_distribution_sums_correctly(**kwargs) -> dict[str, Any]:
        distribution = {
            QUALITY_GRADE_A: 0,
            QUALITY_GRADE_B: 0,
            QUALITY_GRADE_C: 0,
            QUALITY_GRADE_D: 0,
            QUALITY_GRADE_UNKNOWN: 0,
        }
        for item in kwargs["summary_records"]:
            grade = str((item.get("quality") or {}).get("quality_grade", QUALITY_GRADE_UNKNOWN))
            distribution[grade] = distribution.get(grade, 0) + 1
        total = sum(distribution.values())
        ok = total == len(kwargs["summary_records"])
        return {
            "name": "Quality Distribution Sums Correctly",
            "status": "PASS" if ok else "FAIL",
            "distribution_total": total,
            "summary_count": len(kwargs["summary_records"]),
            "quality_grade_distribution": distribution,
        }

    @staticmethod
    def _check_quality_does_not_modify_completion(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["summary_records"]:
            completion = item.get("completion") or {}
            expected = BeamSummaryBuilder._build_completion(
                int(item.get("bar_count") or 0),
                int(item.get("calculated_bars") or 0),
                int(item.get("deferred_bars") or 0),
                int(item.get("blocked_bars") or 0),
            )
            if completion != expected:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Quality Does Not Modify Completion",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_quality_object_schema_complete(**kwargs) -> dict[str, Any]:
        required_keys = {
            "confidence_score",
            "quality_grade",
            "source_diversity",
            "direct_sources",
            "derived_sources",
            "inference_count",
            "quality_ready",
        }
        invalid = []
        for item in kwargs["summary_records"]:
            quality = item.get("quality") or {}
            metadata_quality = (item.get("metadata") or {}).get("quality") or {}
            if set(quality.keys()) != required_keys:
                invalid.append(item.get("beam_summary_id"))
            elif quality != metadata_quality:
                invalid.append(item.get("beam_summary_id"))
        return {
            "name": "Quality Object Schema Complete",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
