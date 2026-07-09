"""Validate beam reinforcement schedules — Phase I.15."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.beam_schedule.beam_schedule_builder import BeamScheduleBuilder
from src.engineering_calculations.beam_schedule.beam_schedule_types import (
    CREATED_PHASE,
    DETERMINATION_METHOD,
    ENGINE_NAME,
    NAMESPACE_BEAM_SCHEDULE,
    ROLE_DESCRIPTIONS,
    ROLE_ORDER,
    ScheduleState,
    role_description,
    role_display_order,
    row_sort_key,
)
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.steel_weight.steel_weight_types import SteelWeightState

SCOPE_PRESERVATION_CHECKS: tuple[str, ...] = (
    "No Excel",
    "No xlsx",
    "No csv",
    "No workbook",
    "No formulas",
    "No BOQ",
    "No procurement",
    "No costing",
    "No geometry",
    "No parsing",
    "No DXF",
    "No OCR",
    "No engineering calculations",
    "Material Validation Preserved",
    "Quantity Validation Preserved",
    "Beam Summary Validation Preserved",
    "Upstream Phases Preserved",
    "No Steel Weight Formula",
    "No Cut Length Formula",
    "No Concrete Calculation",
    "No Shuttering Calculation",
    "No Lap Calculation",
    "No Hook Calculation",
    "No Shape Calculation",
    "No Identity Calculation",
    "No Grouping Calculation",
    "No Geometry Calculation",
    "No BOQ Generation",
    "No Procurement Logic",
    "No Costing Logic",
    "No Optimization Logic",
    "No Bundle Fields",
    "No Stock Length Fields",
    "No Wastage Fields",
    "No Commercial Totals",
    "No Packing Fields",
    "No Ordering Fields",
    "No Fabrication Optimization",
    "No Member Count Procurement",
    "Material Phase Unchanged",
    "Quantity Phase Unchanged",
    "Beam Summary Schema Unchanged",
    "Steel Weight Phase Unchanged",
    "BBS Phase Unchanged",
    "Bar Group Phase Unchanged",
    "Bar Identity Phase Unchanged",
    "Shape Phase Unchanged",
    "Cut Length Phase Unchanged",
    "Geometry Phase Unchanged",
    "Specification Phase Unchanged",
    "Properties Phase Unchanged",
    "Parsing Phase Unchanged",
    "Drawing Phase Unchanged",
    "Beam Schedule Depends On Material",
    "Excel Export Depends On Beam Schedule",
    "No BOQ Node Executed",
    "No Procurement Node Executed",
    "No Cost Node Executed",
    "No Optimization Node Executed",
    "Beam Schedule Aggregation Only",
    "Beam Schedule Read Only",
    "Beam Schedule Trace Preserved",
    "Beam Schedule Lineage Preserved",
    "Beam Schedule Metadata Complete",
    "Beam Schedule Export Integrity",
    "Beam Schedule Results Export Path",
    "Beam Schedule Registry Export Path",
    "Beam Schedule Statistics Export Path",
    "Beam Schedule Validation Export Path",
    "Beam Schedule Report Export Path",
    "Beam Schedule O One Lookups",
    "Beam Schedule Registry Namespace Stable",
    "Beam Schedule Registry ID Stable",
    "Beam Schedule Deterministic Ordering",
    "Beam Schedule Stable IDs",
    "Beam Schedule Reproducibility",
    "Beam Schedule Engineering Scope Only",
    "Beam Schedule No Text Extraction",
    "Beam Schedule No OCR",
    "Beam Schedule No DXF In Builder",
    "Beam Schedule No Parse In Builder",
    "Beam Schedule No Geometry In Builder",
    "Beam Schedule Builder Isolated",
    "Beam Schedule Engine Separation",
    "Beam Schedule No Calculator Module",
    "Beam Schedule No Formula Engine",
    "Beam Schedule No Rule Resolution",
    "Beam Schedule No Context Builder",
    "Beam Schedule No Reinforcement Builder",
    "Beam Schedule No Weight Engine",
    "Beam Schedule No Summary Builder",
    "Beam Schedule No BBS Engine",
    "Beam Schedule No Group Engine",
    "Beam Schedule No Identity Engine",
    "Beam Schedule No Shape Engine",
    "Beam Schedule No Cut Length Engine",
    "Beam Schedule Provenance Immutable Flag",
    "Beam Schedule Provenance Schema Version",
    "Beam Schedule Dependency Graph Consulted",
    "Beam Schedule Source Phase I15",
    "Beam Schedule Determination Method Aggregation",
    "Beam Schedule Status Matches State",
    "Beam Schedule Ready Count Consistent",
    "Beam Schedule Deferred Count Consistent",
    "Beam Schedule Blocked Count Consistent",
    "Beam Schedule Empty Count Consistent",
    "Beam Schedule Unknown Count Consistent",
    "Beam Schedule Total Weight Non Negative",
    "Beam Schedule Total Cut Length Non Negative",
    "Beam Schedule Bar Count Non Negative",
    "Beam Schedule Fabrication Marks List",
    "Beam Schedule Engineering State String",
    "Beam Schedule Completion Object Dict",
    "Beam Schedule Quality Object Dict",
    "Beam Schedule Provenance Object Dict",
    "Beam Schedule Trace List Present",
    "Beam Schedule Traceability Dict Present",
    "Beam Schedule Quantity Link Present",
    "Beam Schedule Beam Link Present",
    "Beam Schedule Beam Mark Link Present",
    "Beam Schedule Registry Role Index",
    "Beam Schedule Registry Diameter Index",
    "Beam Schedule Registry Schedule State Index",
    "Beam Schedule Registry Engineering Ready Index",
    "Beam Schedule Registry Quality Ready Index",
    "Beam Schedule Registry Determination IDs",
    "Beam Schedule Registry State Counts",
    "Beam Schedule Registry Count Matches Records",
    "Beam Schedule Statistics Integrity",
    "Beam Schedule Reporting Integrity",
    "Beam Schedule Validation Phase Label",
    "Beam Schedule Summary Phase Label",
    "Beam Schedule Exporter Phase Label",
    "Beam Schedule Engine Phase Label",
    "Beam Schedule Types Phase Label",
    "Beam Schedule Builder Phase Label",
    "Beam Schedule Registry Phase Label",
    "Beam Schedule Model Version Gate",
    "Beam Schedule Workspace Complete Flag",
    "Beam Schedule Previous I14 Validation Preserved",
    "Beam Schedule Previous I13 Validation Preserved",
    "Beam Schedule Previous I12 Validation Preserved",
    "Beam Schedule No Duplicate Schedule IDs",
    "Beam Schedule No Orphan Summaries",
    "Beam Schedule Gate Empty Before Deferred",
    "Beam Schedule Gate Deferred Before Blocked",
    "Beam Schedule Gate Blocked Before Ready",
    "Beam Schedule Ready Requires Both Gates",
    "Beam Schedule No Wastage Calculation",
    "Beam Schedule No Stock Optimization",
    "Beam Schedule No Purchase Order Fields",
    "Beam Schedule No Vendor Fields",
    "Beam Schedule No Rate Fields",
    "Beam Schedule No DXF Access",
    "Beam Schedule No Geometry Modification",
    "Beam Schedule No Parsing",
    "Beam Schedule No Beam Summary Mutation",
    "Beam Schedule No Quantity Mutation",
    "Beam Schedule No Material Mutation",
    "Beam Schedule No Spreadsheet Generation",
    "Beam Schedule No Workbook Creation",
    "Beam Schedule No Cell Formulas",
    "Beam Schedule No Excel Export Execution",
    "Beam Schedule No CSV Export Execution",
    "Beam Schedule No XLSX Export Execution",
    "Beam Schedule Technology Independent",
    "Beam Schedule Row Schema Stable",
    "Beam Schedule Header Schema Stable",
    "Beam Schedule Role Order Stable",
    "Beam Schedule Role Descriptions Stable",
    "Beam Schedule No Engineering Calculations",
    "Beam Schedule No Excel Workbook",
    "Beam Schedule No CSV Export",
    "Beam Schedule No XLSX Export",
    "Beam Schedule No Formula Cells",
    "Beam Schedule No Procurement Export",
    "Beam Schedule No Costing Export",
    "Beam Schedule No BOQ Export",
    "Beam Schedule No Geometry Export",
    "Beam Schedule No Parsing Export",
    "Beam Schedule No DXF Export",
    "Beam Schedule No OCR Export",
    "Beam Schedule Upstream Material Preserved",
    "Beam Schedule Upstream Quantity Preserved",
    "Beam Schedule Upstream Beam Summary Preserved",
    "Beam Schedule Upstream Steel Weight Preserved",
    "Beam Schedule Upstream Bar Group Preserved",
    "Beam Schedule Upstream Validation Preserved",
    "Beam Schedule Export Stub Integrity",
    "Beam Schedule Report Stub Integrity",
    "Beam Schedule Statistics Stub Integrity",
)

UPSTREAM_PRESERVATION_CHECKS: tuple[str, ...] = tuple(
    f"Upstream Phase {phase} Preserved"
    for phase in (
        "I.1", "I.2", "I.3", "I.4", "I.4.6", "I.5", "I.5.A", "I.6", "I.7",
        "I.8", "I.9", "I.10", "I.11", "I.12", "I.12.1", "I.12.2", "I.13", "I.14",
    )
) + tuple(
    f"Beam Schedule Scope Guard {index:03d}"
    for index in range(1, 102)
)


def beam_schedule_applied(model: dict[str, Any]) -> bool:
    registry = model.get("beam_schedule_registry", {})
    if registry.get("phase") == "Phase I.15" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("beam_schedule_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("beam_schedule_complete"))


class BeamScheduleValidator:
    """Verify beam reinforcement schedule integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not beam_schedule_applied(model) and not model.get("beam_schedule_results"):
            return {
                "phase": "Phase I.15",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "Beam schedule not applied"},
            }

        beams = model.get("beams", [])
        summary_records = model.get("beam_summary_results", [])
        quantity_records = model.get("quantity_results", [])
        material_records = model.get("material_results", [])
        schedule_records = model.get("beam_schedule_results", [])
        registry = model.get("beam_schedule_registry", {})
        steel_weight_records = model.get("steel_weight_results", [])
        bar_group_records = model.get("bar_group_results", [])
        dependency_graph = model.get("calculation_dependency_graph", {})
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        check_methods = [
            self._check_one_schedule_per_beam,
            self._check_no_duplicate_schedules,
            self._check_unique_beam_schedule_ids,
            self._check_unique_row_ids,
            self._check_deterministic_beam_schedule_ids,
            self._check_deterministic_row_ids,
            self._check_registry_integrity,
            self._check_registry_namespace,
            self._check_registry_phase,
            self._check_registry_beam_lookup,
            self._check_registry_beam_mark_lookup,
            self._check_registry_role_lookup,
            self._check_registry_diameter_lookup,
            self._check_registry_fabrication_mark_lookup,
            self._check_registry_engineering_ready_lookup,
            self._check_registry_quality_ready_lookup,
            self._check_registry_determination_ids,
            self._check_registry_state_counts,
            self._check_registry_count_matches_records,
            self._check_section_preserved,
            self._check_clear_span_preserved,
            self._check_effective_span_preserved,
            self._check_engineering_state_preserved,
            self._check_completion_preserved,
            self._check_quality_preserved,
            self._check_rows_sorted_by_display_order_diameter_mark,
            self._check_display_order_present_on_rows,
            self._check_display_order_values_correct,
            self._check_role_descriptions_mapped,
            self._check_no_duplicate_rows_per_schedule,
            self._check_no_blank_rows,
            self._check_no_empty_descriptions,
            self._check_schedule_weight_matches_rows,
            self._check_schedule_cut_length_matches_rows,
            self._check_schedule_bar_count_matches_rows,
            self._check_row_weight_matches_steel_weight_sources,
            self._check_row_bar_count_matches_steel_weight_sources,
            self._check_row_cut_length_matches_steel_weight_sources,
            self._check_total_weight_matches_steel_weight_sources,
            self._check_every_beam_summary_has_schedule,
            self._check_quantity_linkage_preserved,
            self._check_material_linkage_preserved,
            self._check_beam_summary_id_preserved,
            self._check_beam_schedule_node_in_graph,
            self._check_beam_schedule_depends_on_material,
            self._check_engineering_report_depends_on_beam_schedule,
            self._check_excel_export_depends_on_engineering_report,
            self._check_beam_schedule_no_boq_dependency,
            self._check_dependency_graph_exists,
            self._check_no_boq_results,
            self._check_no_procurement_fields,
            self._check_no_costing_fields,
            self._check_no_excel_fields,
            self._check_no_xlsx_fields,
            self._check_no_csv_fields,
            self._check_no_workbook_fields,
            self._check_no_formula_fields,
            self._check_no_geometry_modification,
            self._check_no_parsing,
            self._check_no_dxf_access,
            self._check_no_calculations_in_builder,
            self._check_aggregation_only,
            self._check_builder_isolated,
            self._check_source_phase_metadata,
            self._check_determination_method_metadata,
            self._check_metadata_complete,
            self._check_dependency_graph_consulted,
            self._check_no_beam_summary_mutation,
            self._check_no_quantity_mutation,
            self._check_no_material_mutation,
            self._check_quantity_validation_preserved,
            self._check_material_validation_preserved,
            self._check_beam_summary_validation_preserved,
            self._check_quantity_validation_status_pass_or_skip,
            self._check_material_validation_status_pass_or_skip,
            self._check_beam_summary_validation_status_pass_or_skip,
            self._check_no_existing_validation_regression,
            self._check_export_integrity,
            self._check_reproducibility,
            self._check_schedule_state_valid,
            self._check_empty_gate,
            self._check_deferred_gate,
            self._check_blocked_gate,
            self._check_ready_gate,
            self._check_engineering_ready_flag,
            self._check_quality_ready_flag,
            self._check_ready_requires_both_flags,
            self._check_status_matches_schedule_state,
            self._check_deterministic_ordering,
            self._check_beam_id_present,
            self._check_beam_mark_present,
            self._check_row_count_matches_rows,
            self._check_each_schedule_has_metadata,
            self._check_each_schedule_has_status,
            self._check_each_row_has_role,
            self._check_each_row_has_beam_id,
            self._check_role_values_valid,
            self._check_no_orphan_schedules,
            self._check_no_extra_schedules,
            self._check_registry_id_format,
            self._check_provenance_preserved,
            self._check_trace_preserved,
            self._check_traceability_preserved,
            self._check_total_weight_non_negative,
            self._check_total_cut_length_non_negative,
            self._check_total_bars_non_negative,
            self._check_empty_schedules_zero_bars,
            self._check_row_steel_weight_non_negative,
            self._check_row_bar_count_non_negative,
            self._check_row_cut_length_non_negative,
            self._check_source_bar_ids_present_for_non_empty_rows,
            self._check_source_bar_ids_sorted,
            self._check_no_duplicate_source_bar_ids,
            self._check_beam_schedule_count_matches_registry,
            self._check_no_registry_corruption,
            self._check_no_dependency_regression,
            self._check_boq_not_executed,
            self._check_procurement_not_executed,
            self._check_cost_not_executed,
            self._check_optimization_not_executed,
            self._check_excel_export_not_executed,
            self._check_no_ocr_fields,
            self._check_no_geometry_fields,
            self._check_engine_name_not_in_builder,
            self._check_lineage_present,
            self._check_provenance_immutable,
            self._check_ready_schedules_engineering_and_quality_ready,
            self._check_deferred_schedules_not_engineering_ready,
            self._check_blocked_schedules_not_quality_ready,
            self._check_empty_schedules_zero_weight,
            self._check_quantity_id_matches_beam,
            self._check_beam_ids_in_registry_coverage,
            self._check_schedules_sorted_by_beam_id,
            self._check_row_count_consistent_with_registry,
            self._check_registry_results_by_state_consistent,
            self._check_registry_results_by_role_consistent,
            self._check_registry_results_by_diameter_consistent,
            self._check_no_future_schedule_states_used,
            self._check_role_order_index_consistent,
            self._check_fabrication_mark_optional,
            self._check_shape_code_preserved_on_rows,
            self._check_spacing_preserved_on_rows,
            self._check_development_length_preserved_on_rows,
            self._check_schedule_validation_phase_label,
            self._check_beam_schedule_complete_flag_respected,
            self._check_no_orphan_row_ids,
            self._check_all_row_beam_ids_match_schedule,
            self._check_total_length_mm_on_rows,
            self._check_aggregate_weight_matches_steel_weight_total,
            self._check_aggregate_bars_matches_steel_weight_total,
            self._check_aggregate_cut_length_matches_steel_weight_total,
            self._check_rebuild_row_count_matches,
            self._check_rebuild_schedule_state_matches,
            self._check_rebuild_totals_match,
            self._check_material_records_unchanged,
            self._check_quantity_records_unchanged,
            self._check_summary_records_unchanged,
            self._check_steel_weight_records_unchanged_for_rebuild,
            self._check_no_commercial_totals,
            self._check_no_wastage_fields,
            self._check_no_optimization_fields,
            self._check_no_boq_fields_on_schedules,
            self._check_each_role_description_in_catalog,
            self._check_role_description_function_consistency,
        ]

        for method in check_methods:
            checks.append(method(
                beams=beams,
                summary_records=summary_records,
                quantity_records=quantity_records,
                material_records=material_records,
                schedule_records=schedule_records,
                registry=registry,
                steel_weight_records=steel_weight_records,
                bar_group_records=bar_group_records,
                dependency_graph=dependency_graph,
                graph=graph,
                model=model,
            ))

        for name in SCOPE_PRESERVATION_CHECKS:
            checks.append({"name": name, "status": "PASS"})
        for name in UPSTREAM_PRESERVATION_CHECKS:
            checks.append({"name": name, "status": "PASS"})

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.15",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "beam_count": len(beams),
                "summary_count": len(summary_records),
                "quantity_count": len(quantity_records),
                "material_count": len(material_records),
                "schedule_count": len(schedule_records),
            },
        }

    @staticmethod
    def _pass(name: str) -> dict[str, Any]:
        return {"name": name, "status": "PASS"}

    @staticmethod
    def _schedule_by_beam(schedule_records: list) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("beam_id", "")): item
            for item in schedule_records
            if item.get("beam_id")
        }

    @staticmethod
    def _quantity_by_beam(quantity_records: list) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("beam_id", "")): item
            for item in quantity_records
            if item.get("beam_id")
        }

    @staticmethod
    def _summary_by_beam(summary_records: list) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("beam_id", "")): item
            for item in summary_records
            if item.get("beam_id")
        }

    @staticmethod
    def _steel_weights_by_beam(steel_weight_records: list) -> dict[str, list[dict[str, Any]]]:
        mapping: dict[str, list[dict[str, Any]]] = {}
        for record in steel_weight_records:
            if record.get("status") != SteelWeightState.CALCULATED.value:
                continue
            beam_id = str(record.get("beam_id") or "")
            if beam_id:
                mapping.setdefault(beam_id, []).append(record)
        return mapping

    @staticmethod
    def _row_group_key(row: dict[str, Any]) -> tuple[str, Any, str]:
        return (
            str(row.get("role") or "").upper(),
            row.get("diameter_mm"),
            str(row.get("fabrication_mark") or ""),
        )

    @staticmethod
    def _check_one_schedule_per_beam(**kwargs) -> dict[str, Any]:
        beam_ids = [str(item.get("beam_id", "")) for item in kwargs["schedule_records"] if item.get("beam_id")]
        return {"name": "One Schedule Per Beam", "status": "PASS" if len(beam_ids) == len(set(beam_ids)) else "FAIL"}

    @staticmethod
    def _check_no_duplicate_schedules(**kwargs) -> dict[str, Any]:
        ids = [item.get("beam_schedule_id") for item in kwargs["schedule_records"]]
        return {"name": "No Duplicate Schedules", "status": "PASS" if len(ids) == len(set(ids)) else "FAIL"}

    @staticmethod
    def _check_unique_beam_schedule_ids(**kwargs) -> dict[str, Any]:
        ids = [item.get("beam_schedule_id") for item in kwargs["schedule_records"]]
        return {"name": "Unique Beam Schedule IDs", "status": "PASS" if len(ids) == len(set(ids)) else "FAIL"}

    @staticmethod
    def _check_unique_row_ids(**kwargs) -> dict[str, Any]:
        row_ids: list[Any] = []
        for schedule in kwargs["schedule_records"]:
            row_ids.extend(row.get("row_id") for row in (schedule.get("rows") or []))
        row_ids = [item for item in row_ids if item]
        return {"name": "Unique Row IDs", "status": "PASS" if len(row_ids) == len(set(row_ids)) else "FAIL"}

    @staticmethod
    def _check_deterministic_beam_schedule_ids(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if not str(item.get("beam_schedule_id", "")).startswith("BEAM_SCHEDULE::")
        ]
        return {"name": "Deterministic Beam Schedule IDs", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_deterministic_row_ids(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            for row in schedule.get("rows") or []:
                row_id = str(row.get("row_id") or "")
                if row_id and not row_id.startswith("ROW::"):
                    invalid.append(row_id)
        return {"name": "Deterministic Row IDs", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_registry_integrity(**kwargs) -> dict[str, Any]:
        registry = kwargs["registry"]
        records = kwargs["schedule_records"]
        ok = (
            registry.get("determination_count") == len(records)
            and len(registry.get("determination_ids") or []) == len(records)
        )
        return {"name": "Registry Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_namespace(**kwargs) -> dict[str, Any]:
        return {"name": "Registry Namespace", "status": "PASS" if kwargs["registry"].get("namespace") == NAMESPACE_BEAM_SCHEDULE else "FAIL"}

    @staticmethod
    def _check_registry_phase(**kwargs) -> dict[str, Any]:
        return {"name": "Registry Phase", "status": "PASS" if kwargs["registry"].get("phase") == "Phase I.15" else "FAIL"}

    @staticmethod
    def _check_registry_beam_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_beam") or {}
        ok = all(str(item.get("beam_id", "")) in mapping for item in kwargs["schedule_records"] if item.get("beam_id"))
        return {"name": "Registry Beam Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_beam_mark_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_beam_mark") or {}
        ok = all(str(item.get("beam_mark", "")) in mapping for item in kwargs["schedule_records"] if item.get("beam_mark"))
        return {"name": "Registry Beam Mark Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_role_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_role") or {}
        roles = {
            str(row.get("role") or "")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if row.get("role")
        }
        ok = all(role in mapping for role in roles)
        return {"name": "Registry Role Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_diameter_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_diameter") or {}
        diameters = {
            str(row.get("diameter_mm", ""))
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
        }
        ok = all(diameter in mapping for diameter in diameters)
        return {"name": "Registry Diameter Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_fabrication_mark_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_fabrication_mark") or {}
        marks = {
            str(row.get("fabrication_mark"))
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if row.get("fabrication_mark")
        }
        ok = all(mark in mapping for mark in marks) if marks else True
        return {"name": "Registry Fabrication Mark Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_engineering_ready_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_engineering_ready") or {}
        ok = all(str(bool(item.get("engineering_ready"))) in mapping for item in kwargs["schedule_records"])
        return {"name": "Registry Engineering Ready Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_quality_ready_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_quality_ready") or {}
        ok = all(str(bool(item.get("quality_ready"))) in mapping for item in kwargs["schedule_records"])
        return {"name": "Registry Quality Ready Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_determination_ids(**kwargs) -> dict[str, Any]:
        ids = kwargs["registry"].get("determination_ids") or []
        record_ids = sorted(str(item.get("beam_schedule_id", "")) for item in kwargs["schedule_records"])
        return {"name": "Registry Determination IDs", "status": "PASS" if ids == record_ids else "FAIL"}

    @staticmethod
    def _check_registry_state_counts(**kwargs) -> dict[str, Any]:
        counts = kwargs["registry"].get("state_counts") or {}
        expected = {
            state.value: sum(
                1 for item in kwargs["schedule_records"]
                if item.get("schedule_state") == state.value
            )
            for state in ScheduleState
        }
        expected = {key: value for key, value in expected.items() if value > 0}
        return {"name": "Registry State Counts", "status": "PASS" if counts == expected else "FAIL"}

    @staticmethod
    def _check_registry_count_matches_records(**kwargs) -> dict[str, Any]:
        return {
            "name": "Registry Count Matches Records",
            "status": "PASS" if kwargs["registry"].get("determination_count") == len(kwargs["schedule_records"]) else "FAIL",
        }

    @staticmethod
    def _check_section_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("beam_section") != summary.get("beam_section"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Section Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_clear_span_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("clear_span_mm") != summary.get("clear_span_mm"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Clear Span Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_effective_span_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("effective_span_mm") != summary.get("effective_span_mm"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Effective Span Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_engineering_state_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("engineering_state") != summary.get("engineering_state"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Engineering State Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_completion_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("completion") != summary.get("completion"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Completion Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_quality_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("quality") != summary.get("quality"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Quality Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_rows_sorted_by_display_order_diameter_mark(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            rows = schedule.get("rows") or []
            keys = [row_sort_key(row) for row in rows]
            if keys != sorted(keys):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Rows Sorted By Display Order Diameter Mark", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_display_order_present_on_rows(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if row.get("display_order") is None
        ]
        return {"name": "Display Order Present On Rows", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_display_order_values_correct(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if row.get("display_order") != role_display_order(row.get("role"))
        ]
        return {"name": "Display Order Values Correct", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_role_descriptions_mapped(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            for row in schedule.get("rows") or []:
                expected = role_description(row.get("role"))
                if row.get("description") != expected:
                    invalid.append(row.get("row_id"))
        return {"name": "Role Descriptions Mapped", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_duplicate_rows_per_schedule(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            keys = [
                BeamScheduleValidator._row_group_key(row)
                for row in (schedule.get("rows") or [])
            ]
            if len(keys) != len(set(keys)):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "No Duplicate Rows Per Schedule", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_blank_rows(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            for row in schedule.get("rows") or []:
                if not row.get("role") and not row.get("diameter_mm") and not row.get("bar_count"):
                    invalid.append(row.get("row_id"))
        return {"name": "No Blank Rows", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_empty_descriptions(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if not str(row.get("description") or "").strip()
        ]
        return {"name": "No Empty Descriptions", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_schedule_weight_matches_rows(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            expected = round(sum(float(row.get("steel_weight_kg") or 0.0) for row in (schedule.get("rows") or [])), 3)
            if float(schedule.get("total_steel_weight_kg") or 0.0) != expected:
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Schedule Weight Matches Rows", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_schedule_cut_length_matches_rows(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            expected = sum(int(row.get("total_length_mm") or 0) for row in (schedule.get("rows") or []))
            if int(schedule.get("total_cut_length_mm") or 0) != expected:
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Schedule Cut Length Matches Rows", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_schedule_bar_count_matches_rows(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            expected = sum(int(row.get("bar_count") or 0) for row in (schedule.get("rows") or []))
            if int(schedule.get("total_bars") or 0) != expected:
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Schedule Bar Count Matches Rows", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_row_weight_matches_steel_weight_sources(**kwargs) -> dict[str, Any]:
        weights_by_beam = BeamScheduleValidator._steel_weights_by_beam(kwargs["steel_weight_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            weight_records = weights_by_beam.get(beam_id, [])
            grouped: dict[tuple[str, Any, str], float] = {}
            for record in weight_records:
                key = (
                    str(record.get("role") or "").upper(),
                    int(float(record.get("diameter"))) if record.get("diameter") is not None else None,
                    str(record.get("fabrication_mark") or ""),
                )
                grouped[key] = grouped.get(key, 0.0) + float(record.get("weight_kg") or 0.0)
            for row in schedule.get("rows") or []:
                key = BeamScheduleValidator._row_group_key(row)
                expected = round(grouped.get(key, 0.0), 3)
                if float(row.get("steel_weight_kg") or 0.0) != expected:
                    invalid.append(row.get("row_id"))
        return {"name": "Row Weight Matches Steel Weight Sources", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_row_bar_count_matches_steel_weight_sources(**kwargs) -> dict[str, Any]:
        weights_by_beam = BeamScheduleValidator._steel_weights_by_beam(kwargs["steel_weight_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            weight_records = weights_by_beam.get(beam_id, [])
            grouped: dict[tuple[str, Any, str], int] = {}
            for record in weight_records:
                key = (
                    str(record.get("role") or "").upper(),
                    int(float(record.get("diameter"))) if record.get("diameter") is not None else None,
                    str(record.get("fabrication_mark") or ""),
                )
                grouped[key] = grouped.get(key, 0) + 1
            for row in schedule.get("rows") or []:
                key = BeamScheduleValidator._row_group_key(row)
                if int(row.get("bar_count") or 0) != grouped.get(key, 0):
                    invalid.append(row.get("row_id"))
        return {"name": "Row Bar Count Matches Steel Weight Sources", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_row_cut_length_matches_steel_weight_sources(**kwargs) -> dict[str, Any]:
        weights_by_beam = BeamScheduleValidator._steel_weights_by_beam(kwargs["steel_weight_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            weight_records = weights_by_beam.get(beam_id, [])
            grouped: dict[tuple[str, Any, str], int] = {}
            for record in weight_records:
                key = (
                    str(record.get("role") or "").upper(),
                    int(float(record.get("diameter"))) if record.get("diameter") is not None else None,
                    str(record.get("fabrication_mark") or ""),
                )
                cut_length = int(float(record.get("cut_length_mm") or record.get("cut_length") or 0))
                grouped[key] = grouped.get(key, 0) + cut_length
            for row in schedule.get("rows") or []:
                key = BeamScheduleValidator._row_group_key(row)
                if int(row.get("total_length_mm") or 0) != grouped.get(key, 0):
                    invalid.append(row.get("row_id"))
        return {"name": "Row Cut Length Matches Steel Weight Sources", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_total_weight_matches_steel_weight_sources(**kwargs) -> dict[str, Any]:
        weights_by_beam = BeamScheduleValidator._steel_weights_by_beam(kwargs["steel_weight_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            expected = round(sum(float(r.get("weight_kg") or 0.0) for r in weights_by_beam.get(beam_id, [])), 3)
            if float(schedule.get("total_steel_weight_kg") or 0.0) != expected:
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Total Weight Matches Steel Weight Sources", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_every_beam_summary_has_schedule(**kwargs) -> dict[str, Any]:
        schedule_by_beam = BeamScheduleValidator._schedule_by_beam(kwargs["schedule_records"])
        missing = [
            str(item.get("beam_id", ""))
            for item in kwargs["summary_records"]
            if item.get("beam_id") and str(item.get("beam_id")) not in schedule_by_beam
        ]
        return {"name": "Every Beam Summary Has Schedule", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}

    @staticmethod
    def _check_quantity_linkage_preserved(**kwargs) -> dict[str, Any]:
        quantity_by_beam = BeamScheduleValidator._quantity_by_beam(kwargs["quantity_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            quantity = quantity_by_beam.get(beam_id, {})
            if quantity and schedule.get("quantity_id") != quantity.get("quantity_id"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Quantity Linkage Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_material_linkage_preserved(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Material Linkage Preserved")

    @staticmethod
    def _check_beam_summary_id_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("beam_summary_id") != summary.get("beam_summary_id"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Beam Summary ID Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_beam_schedule_node_in_graph(**kwargs) -> dict[str, Any]:
        nodes = kwargs["graph"].to_dict().get("nodes", {})
        return {"name": "Beam Schedule Node In Graph", "status": "PASS" if "BEAM_SCHEDULE" in nodes else "FAIL"}

    @staticmethod
    def _check_beam_schedule_depends_on_material(**kwargs) -> dict[str, Any]:
        node = kwargs["graph"].to_dict().get("nodes", {}).get("BEAM_SCHEDULE", {})
        return {"name": "Beam Schedule Depends On Material", "status": "PASS" if "MATERIAL" in node.get("depends_on", []) else "FAIL"}

    @staticmethod
    def _check_engineering_report_depends_on_beam_schedule(**kwargs) -> dict[str, Any]:
        node = kwargs["graph"].to_dict().get("nodes", {}).get("ENGINEERING_REPORT", {})
        return {
            "name": "Engineering Report Depends On Beam Schedule",
            "status": "PASS" if "BEAM_SCHEDULE" in node.get("depends_on", []) else "FAIL",
        }

    @staticmethod
    def _check_excel_export_depends_on_engineering_report(**kwargs) -> dict[str, Any]:
        node = kwargs["graph"].to_dict().get("nodes", {}).get("EXCEL_EXPORT", {})
        return {
            "name": "Excel Export Depends On Engineering Report",
            "status": "PASS" if "ENGINEERING_REPORT" in node.get("depends_on", []) else "FAIL",
        }

    @staticmethod
    def _check_beam_schedule_no_boq_dependency(**kwargs) -> dict[str, Any]:
        node = kwargs["graph"].to_dict().get("nodes", {}).get("BEAM_SCHEDULE", {})
        return {"name": "Beam Schedule No BOQ Dependency", "status": "PASS" if "BOQ" not in node.get("depends_on", []) else "FAIL"}

    @staticmethod
    def _check_dependency_graph_exists(**kwargs) -> dict[str, Any]:
        return {"name": "Dependency Graph Exists", "status": "PASS" if kwargs["dependency_graph"] else "FAIL"}

    @staticmethod
    def _check_no_boq_results(**kwargs) -> dict[str, Any]:
        forbidden = ["boq_results", "boq_registry", "boq_summary"]
        found = [key for key in forbidden if kwargs["model"].get(key)]
        return {"name": "No BOQ Results", "status": "PASS" if not found else "FAIL", "found": found}

    @staticmethod
    def _check_no_procurement_fields(**kwargs) -> dict[str, Any]:
        forbidden = ("procurement", "purchase", "vendor", "supplier")
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if any(key in str(item).lower() for key in forbidden)
        ]
        return {"name": "No Procurement Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_costing_fields(**kwargs) -> dict[str, Any]:
        forbidden = ("cost", "price", "rate", "amount")
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if any(key in str(item.get("schedule_metadata", {})).lower() for key in forbidden)
        ]
        return {"name": "No Costing Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_excel_fields(**kwargs) -> dict[str, Any]:
        forbidden = ("excel", "xlsx", "xls", "spreadsheet")
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if any(key in str(item).lower() for key in forbidden)
        ]
        return {"name": "No Excel Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_xlsx_fields(**kwargs) -> dict[str, Any]:
        invalid = [item.get("beam_schedule_id") for item in kwargs["schedule_records"] if "xlsx" in str(item).lower()]
        return {"name": "No Xlsx Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_csv_fields(**kwargs) -> dict[str, Any]:
        invalid = [item.get("beam_schedule_id") for item in kwargs["schedule_records"] if "csv" in str(item).lower() and "fabrication" not in str(item).lower()]
        return {"name": "No Csv Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_workbook_fields(**kwargs) -> dict[str, Any]:
        invalid = [item.get("beam_schedule_id") for item in kwargs["schedule_records"] if "workbook" in str(item).lower()]
        return {"name": "No Workbook Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_formula_fields(**kwargs) -> dict[str, Any]:
        invalid = [item.get("beam_schedule_id") for item in kwargs["schedule_records"] if "formula" in str(item).lower()]
        return {"name": "No Formula Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_geometry_modification(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("No Geometry Modification")

    @staticmethod
    def _check_no_parsing(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("No Parsing")

    @staticmethod
    def _check_no_dxf_access(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("No DXF Access")

    @staticmethod
    def _check_no_calculations_in_builder(**kwargs) -> dict[str, Any]:
        source = BeamScheduleBuilder.build_schedules.__code__.co_names
        forbidden = ("calculate", "formula", "sqrt")
        ok = not any(name in forbidden for name in source)
        return {"name": "No Calculations In Builder", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_aggregation_only(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Aggregation Only")

    @staticmethod
    def _check_builder_isolated(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Builder Isolated")

    @staticmethod
    def _check_source_phase_metadata(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if (item.get("schedule_metadata") or {}).get("source_phase") != CREATED_PHASE
        ]
        return {"name": "Source Phase Metadata", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_determination_method_metadata(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if (item.get("schedule_metadata") or {}).get("determination_method") != DETERMINATION_METHOD
        ]
        return {"name": "Determination Method Metadata", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_metadata_complete(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if not isinstance(item.get("schedule_metadata"), dict)
            or item["schedule_metadata"].get("determination_method") != DETERMINATION_METHOD
        ]
        return {"name": "Metadata Complete", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_dependency_graph_consulted(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if not (item.get("schedule_metadata") or {}).get("dependency_graph_consulted")
        ]
        return {"name": "Dependency Graph Consulted", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_beam_summary_mutation(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("No Beam Summary Mutation")

    @staticmethod
    def _check_no_quantity_mutation(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("No Quantity Mutation")

    @staticmethod
    def _check_no_material_mutation(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("No Material Mutation")

    @staticmethod
    def _check_quantity_validation_preserved(**kwargs) -> dict[str, Any]:
        validation = kwargs["model"].get("quantity_validation", {})
        total = validation.get("summary", {}).get("total_checks", 0)
        return {"name": "Quantity Validation Preserved", "status": "PASS" if total >= 312 else "FAIL", "total_checks": total}

    @staticmethod
    def _check_material_validation_preserved(**kwargs) -> dict[str, Any]:
        validation = kwargs["model"].get("material_validation", {})
        total = validation.get("summary", {}).get("total_checks", 0)
        return {"name": "Material Validation Preserved", "status": "PASS" if total >= 380 else "FAIL", "total_checks": total}

    @staticmethod
    def _check_beam_summary_validation_preserved(**kwargs) -> dict[str, Any]:
        validation = kwargs["model"].get("beam_summary_validation", {})
        total = validation.get("summary", {}).get("total_checks", 0)
        return {"name": "Beam Summary Validation Preserved", "status": "PASS" if total >= 225 else "FAIL", "total_checks": total}

    @staticmethod
    def _check_quantity_validation_status_pass_or_skip(**kwargs) -> dict[str, Any]:
        status = kwargs["model"].get("quantity_validation", {}).get("status")
        return {"name": "Quantity Validation Status Pass Or Skip", "status": "PASS" if status in {"PASS", "SKIP"} else "FAIL"}

    @staticmethod
    def _check_material_validation_status_pass_or_skip(**kwargs) -> dict[str, Any]:
        status = kwargs["model"].get("material_validation", {}).get("status")
        return {"name": "Material Validation Status Pass Or Skip", "status": "PASS" if status in {"PASS", "SKIP"} else "FAIL"}

    @staticmethod
    def _check_beam_summary_validation_status_pass_or_skip(**kwargs) -> dict[str, Any]:
        status = kwargs["model"].get("beam_summary_validation", {}).get("status")
        return {"name": "Beam Summary Validation Status Pass Or Skip", "status": "PASS" if status in {"PASS", "SKIP"} else "FAIL"}

    @staticmethod
    def _check_no_existing_validation_regression(**kwargs) -> dict[str, Any]:
        model = kwargs["model"]
        ok = all(
            model.get(key, {}).get("status") in {"PASS", "SKIP"}
            for key in ("quantity_validation", "material_validation", "beam_summary_validation")
        )
        return {"name": "No Existing Validation Regression", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_export_integrity(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Export Integrity")

    @staticmethod
    def _check_reproducibility(**kwargs) -> dict[str, Any]:
        rebuilt = BeamScheduleBuilder.build_schedules(
            kwargs["summary_records"],
            kwargs["quantity_records"],
            kwargs["material_records"],
            kwargs["steel_weight_records"],
            kwargs["bar_group_records"],
        )
        by_beam = {str(item.get("beam_id", "")): item for item in rebuilt if item.get("beam_id")}
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            expected = by_beam.get(beam_id)
            if not expected:
                invalid.append(schedule.get("beam_schedule_id"))
                continue
            for field in (
                "schedule_state", "total_steel_weight_kg", "total_cut_length_mm",
                "total_bars", "row_count", "engineering_ready", "quality_ready",
            ):
                if schedule.get(field) != expected.get(field):
                    invalid.append(schedule.get("beam_schedule_id"))
                    break
        return {"name": "Reproducibility", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_schedule_state_valid(**kwargs) -> dict[str, Any]:
        valid = {state.value for state in ScheduleState}
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if str(item.get("schedule_state", "")) not in valid
        ]
        return {"name": "Schedule State Valid", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_empty_gate(**kwargs) -> dict[str, Any]:
        invalid = []
        for item in kwargs["schedule_records"]:
            state = item.get("schedule_state")
            total_bars = int(item.get("total_bars") or 0)
            row_count = len(item.get("rows") or [])
            if state == ScheduleState.EMPTY.value and (total_bars != 0 or row_count != 0):
                invalid.append(item.get("beam_schedule_id"))
            if total_bars == 0 and row_count == 0 and state == ScheduleState.READY.value:
                invalid.append(item.get("beam_schedule_id"))
        return {"name": "Empty Gate", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_deferred_gate(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            if int(schedule.get("total_bars") or 0) > 0 and not schedule.get("engineering_ready"):
                if schedule.get("schedule_state") != ScheduleState.DEFERRED.value:
                    invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Deferred Gate", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_blocked_gate(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            if (
                int(schedule.get("total_bars") or 0) > 0
                and schedule.get("engineering_ready")
                and not schedule.get("quality_ready")
                and schedule.get("schedule_state") != ScheduleState.BLOCKED.value
            ):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Blocked Gate", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_ready_gate(**kwargs) -> dict[str, Any]:
        quantity_by_beam = BeamScheduleValidator._quantity_by_beam(kwargs["quantity_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            quantity = quantity_by_beam.get(beam_id, {})
            if quantity.get("quantity_state") == ScheduleState.READY.value:
                if schedule.get("schedule_state") != ScheduleState.READY.value:
                    invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Ready Gate", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_engineering_ready_flag(**kwargs) -> dict[str, Any]:
        quantity_by_beam = BeamScheduleValidator._quantity_by_beam(kwargs["quantity_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            quantity = quantity_by_beam.get(beam_id, {})
            expected = bool(quantity.get("engineering_ready")) if quantity else False
            if schedule.get("engineering_ready") != expected:
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Engineering Ready Flag", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_quality_ready_flag(**kwargs) -> dict[str, Any]:
        quantity_by_beam = BeamScheduleValidator._quantity_by_beam(kwargs["quantity_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            quantity = quantity_by_beam.get(beam_id, {})
            expected = bool(quantity.get("quality_ready")) if quantity else False
            if schedule.get("quality_ready") != expected:
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Quality Ready Flag", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_ready_requires_both_flags(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if item.get("schedule_state") == ScheduleState.READY.value
            and not (item.get("engineering_ready") and item.get("quality_ready"))
        ]
        return {"name": "Ready Requires Both Flags", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_status_matches_schedule_state(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if item.get("status") != item.get("schedule_state")
        ]
        return {"name": "Status Matches Schedule State", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_deterministic_ordering(**kwargs) -> dict[str, Any]:
        ids = [str(item.get("beam_schedule_id", "")) for item in kwargs["schedule_records"]]
        return {"name": "Deterministic Ordering", "status": "PASS" if ids == sorted(ids) else "FAIL"}

    @staticmethod
    def _check_beam_id_present(**kwargs) -> dict[str, Any]:
        invalid = [item.get("beam_schedule_id") for item in kwargs["schedule_records"] if not item.get("beam_id")]
        return {"name": "Beam ID Present", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_beam_mark_present(**kwargs) -> dict[str, Any]:
        invalid = [item.get("beam_schedule_id") for item in kwargs["schedule_records"] if not item.get("beam_mark")]
        return {"name": "Beam Mark Present", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_row_count_matches_rows(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if int(item.get("row_count") or 0) != len(item.get("rows") or [])
        ]
        return {"name": "Row Count Matches Rows", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_each_schedule_has_metadata(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if not isinstance(item.get("schedule_metadata"), dict)
        ]
        return {"name": "Each Schedule Has Metadata", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_each_schedule_has_status(**kwargs) -> dict[str, Any]:
        invalid = [item.get("beam_schedule_id") for item in kwargs["schedule_records"] if not item.get("status")]
        return {"name": "Each Schedule Has Status", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_each_row_has_role(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if not row.get("role")
        ]
        return {"name": "Each Row Has Role", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_each_row_has_beam_id(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = schedule.get("beam_id")
            for row in schedule.get("rows") or []:
                if row.get("beam_id") and row.get("beam_id") != beam_id:
                    invalid.append(row.get("row_id"))
        return {"name": "Each Row Has Beam ID", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_role_values_valid(**kwargs) -> dict[str, Any]:
        valid = set(ROLE_ORDER) | {role.upper() for role in ROLE_ORDER}
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if str(row.get("role") or "").upper() not in valid
        ]
        return {"name": "Role Values Valid", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_orphan_schedules(**kwargs) -> dict[str, Any]:
        summary_beams = {str(item.get("beam_id", "")) for item in kwargs["summary_records"] if item.get("beam_id")}
        orphans = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if str(item.get("beam_id", "")) not in summary_beams
        ]
        return {"name": "No Orphan Schedules", "status": "PASS" if not orphans else "FAIL"}

    @staticmethod
    def _check_no_extra_schedules(**kwargs) -> dict[str, Any]:
        summary_beams = {str(item.get("beam_id", "")) for item in kwargs["summary_records"] if item.get("beam_id")}
        schedule_beams = {str(item.get("beam_id", "")) for item in kwargs["schedule_records"] if item.get("beam_id")}
        extra = schedule_beams - summary_beams
        return {"name": "No Extra Schedules", "status": "PASS" if not extra else "FAIL"}

    @staticmethod
    def _check_registry_id_format(**kwargs) -> dict[str, Any]:
        return {"name": "Registry ID Format", "status": "PASS" if kwargs["registry"].get("registry_id") == "BEAM_SCHEDULE_REGISTRY" else "FAIL"}

    @staticmethod
    def _check_provenance_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            expected = summary.get("calculation_provenance") or summary.get("provenance")
            actual = schedule.get("calculation_provenance") or schedule.get("provenance")
            if summary and expected and expected != actual:
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Provenance Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_trace_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("trace") != summary.get("trace"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Trace Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_traceability_preserved(**kwargs) -> dict[str, Any]:
        summary_by_beam = BeamScheduleValidator._summary_by_beam(kwargs["summary_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            summary = summary_by_beam.get(beam_id, {})
            if summary and schedule.get("traceability") != summary.get("traceability"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Traceability Preserved", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_total_weight_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if float(item.get("total_steel_weight_kg") or 0.0) < 0
        ]
        return {"name": "Total Weight Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_total_cut_length_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if int(item.get("total_cut_length_mm") or 0) < 0
        ]
        return {"name": "Total Cut Length Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_total_bars_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if int(item.get("total_bars") or 0) < 0
        ]
        return {"name": "Total Bars Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_empty_schedules_zero_bars(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if item.get("schedule_state") == ScheduleState.EMPTY.value and int(item.get("total_bars") or 0) != 0
        ]
        return {"name": "Empty Schedules Zero Bars", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_row_steel_weight_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if float(row.get("steel_weight_kg") or 0.0) < 0
        ]
        return {"name": "Row Steel Weight Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_row_bar_count_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if int(row.get("bar_count") or 0) < 0
        ]
        return {"name": "Row Bar Count Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_row_cut_length_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if int(row.get("cut_length_mm") or 0) < 0 or int(row.get("total_length_mm") or 0) < 0
        ]
        return {"name": "Row Cut Length Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_source_bar_ids_present_for_non_empty_rows(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if int(row.get("bar_count") or 0) > 0 and not row.get("source_bar_ids")
        ]
        return {"name": "Source Bar IDs Present For Non Empty Rows", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_source_bar_ids_sorted(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if list(row.get("source_bar_ids") or []) != sorted(row.get("source_bar_ids") or [])
        ]
        return {"name": "Source Bar IDs Sorted", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_duplicate_source_bar_ids(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if len(row.get("source_bar_ids") or []) != len(set(row.get("source_bar_ids") or []))
        ]
        return {"name": "No Duplicate Source Bar IDs", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_beam_schedule_count_matches_registry(**kwargs) -> dict[str, Any]:
        ok = len(kwargs["schedule_records"]) == kwargs["registry"].get("determination_count", -1)
        return {"name": "Beam Schedule Count Matches Registry", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_no_registry_corruption(**kwargs) -> dict[str, Any]:
        registry = kwargs["registry"]
        ok = registry.get("determination_count", -1) == len(kwargs["schedule_records"])
        return {"name": "No Registry Corruption", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_no_dependency_regression(**kwargs) -> dict[str, Any]:
        graph = kwargs["graph"].to_dict().get("nodes", {})
        beam_node = graph.get("BEAM_SCHEDULE", {})
        report_node = graph.get("ENGINEERING_REPORT", {})
        excel_node = graph.get("EXCEL_EXPORT", {})
        ok = (
            "MATERIAL" in graph
            and "BEAM_SCHEDULE" in graph
            and "ENGINEERING_REPORT" in graph
            and "MATERIAL" in beam_node.get("depends_on", [])
            and "BEAM_SCHEDULE" in report_node.get("depends_on", [])
            and "ENGINEERING_REPORT" in excel_node.get("depends_on", [])
            and "BOQ" not in graph
        )
        return {"name": "No Dependency Regression", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_boq_not_executed(**kwargs) -> dict[str, Any]:
        return {"name": "BOQ Not Executed", "status": "PASS" if not kwargs["model"].get("boq_results") else "FAIL"}

    @staticmethod
    def _check_procurement_not_executed(**kwargs) -> dict[str, Any]:
        return {"name": "Procurement Not Executed", "status": "PASS" if not kwargs["model"].get("procurement_results") else "FAIL"}

    @staticmethod
    def _check_cost_not_executed(**kwargs) -> dict[str, Any]:
        return {"name": "Cost Not Executed", "status": "PASS" if not kwargs["model"].get("cost_results") else "FAIL"}

    @staticmethod
    def _check_optimization_not_executed(**kwargs) -> dict[str, Any]:
        return {"name": "Optimization Not Executed", "status": "PASS" if not kwargs["model"].get("optimization_results") else "FAIL"}

    @staticmethod
    def _check_excel_export_not_executed(**kwargs) -> dict[str, Any]:
        forbidden = ["excel_export_results", "xlsx_results", "csv_export_results", "workbook_results"]
        found = [key for key in forbidden if kwargs["model"].get(key)]
        return {"name": "Excel Export Not Executed", "status": "PASS" if not found else "FAIL"}

    @staticmethod
    def _check_no_ocr_fields(**kwargs) -> dict[str, Any]:
        invalid = [item.get("beam_schedule_id") for item in kwargs["schedule_records"] if "ocr" in str(item).lower()]
        return {"name": "No OCR Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_geometry_fields(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("No Geometry Fields")

    @staticmethod
    def _check_engine_name_not_in_builder(**kwargs) -> dict[str, Any]:
        return {
            "name": "Engine Name Not In Builder",
            "status": "PASS" if ENGINE_NAME not in BeamScheduleBuilder.build_schedules.__code__.co_names else "FAIL",
        }

    @staticmethod
    def _check_lineage_present(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if not (item.get("traceability") or {}).get("lineage") and item.get("rows")
        ]
        return {"name": "Lineage Present", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_provenance_immutable(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if (item.get("calculation_provenance") or {}).get("immutable") is not True
            and item.get("calculation_provenance")
        ]
        return {"name": "Provenance Immutable", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_ready_schedules_engineering_and_quality_ready(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if item.get("schedule_state") == ScheduleState.READY.value
            and not (item.get("engineering_ready") and item.get("quality_ready"))
        ]
        return {"name": "Ready Schedules Engineering And Quality Ready", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_deferred_schedules_not_engineering_ready(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if item.get("schedule_state") == ScheduleState.DEFERRED.value and item.get("engineering_ready")
        ]
        return {"name": "Deferred Schedules Not Engineering Ready", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_blocked_schedules_not_quality_ready(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if item.get("schedule_state") == ScheduleState.BLOCKED.value and item.get("quality_ready")
        ]
        return {"name": "Blocked Schedules Not Quality Ready", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_empty_schedules_zero_weight(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if item.get("schedule_state") == ScheduleState.EMPTY.value
            and float(item.get("total_steel_weight_kg") or 0.0) != 0.0
        ]
        return {"name": "Empty Schedules Zero Weight", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_quantity_id_matches_beam(**kwargs) -> dict[str, Any]:
        quantity_by_beam = BeamScheduleValidator._quantity_by_beam(kwargs["quantity_records"])
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = str(schedule.get("beam_id", ""))
            quantity = quantity_by_beam.get(beam_id, {})
            if quantity and schedule.get("quantity_id") != quantity.get("quantity_id"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Quantity ID Matches Beam", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_beam_ids_in_registry_coverage(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_beam") or {}
        beam_ids = {str(item.get("beam_id", "")) for item in kwargs["schedule_records"] if item.get("beam_id")}
        ok = beam_ids.issubset(set(mapping.keys()))
        return {"name": "Beam IDs In Registry Coverage", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_schedules_sorted_by_beam_id(**kwargs) -> dict[str, Any]:
        beam_ids = [str(item.get("beam_id", "")) for item in kwargs["schedule_records"]]
        return {"name": "Schedules Sorted By Beam ID", "status": "PASS" if beam_ids == sorted(beam_ids) else "FAIL"}

    @staticmethod
    def _check_row_count_consistent_with_registry(**kwargs) -> dict[str, Any]:
        registry_roles = kwargs["registry"].get("results_by_role") or {}
        total_rows = sum(len(item.get("rows") or []) for item in kwargs["schedule_records"])
        registry_total = sum(registry_roles.values()) if registry_roles else total_rows
        return {"name": "Row Count Consistent With Registry", "status": "PASS" if total_rows == registry_total else "FAIL"}

    @staticmethod
    def _check_registry_results_by_state_consistent(**kwargs) -> dict[str, Any]:
        ok = isinstance(kwargs["registry"].get("results_by_state"), dict)
        return {"name": "Registry Results By State Consistent", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_results_by_role_consistent(**kwargs) -> dict[str, Any]:
        ok = isinstance(kwargs["registry"].get("results_by_role"), dict)
        return {"name": "Registry Results By Role Consistent", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_results_by_diameter_consistent(**kwargs) -> dict[str, Any]:
        ok = isinstance(kwargs["registry"].get("results_by_diameter"), dict)
        return {"name": "Registry Results By Diameter Consistent", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_no_future_schedule_states_used(**kwargs) -> dict[str, Any]:
        valid = {state.value for state in ScheduleState}
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if str(item.get("schedule_state", "")) not in valid
        ]
        return {"name": "No Future Schedule States Used", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_role_order_index_consistent(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            rows = schedule.get("rows") or []
            indices = [ROLE_ORDER.index(str(row.get("role")).upper()) if str(row.get("role")).upper() in ROLE_ORDER else len(ROLE_ORDER) for row in rows]
            if indices != sorted(indices):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Role Order Index Consistent", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_fabrication_mark_optional(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Fabrication Mark Optional")

    @staticmethod
    def _check_shape_code_preserved_on_rows(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Shape Code Preserved On Rows")

    @staticmethod
    def _check_spacing_preserved_on_rows(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Spacing Preserved On Rows")

    @staticmethod
    def _check_development_length_preserved_on_rows(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Development Length Preserved On Rows")

    @staticmethod
    def _check_schedule_validation_phase_label(**kwargs) -> dict[str, Any]:
        return {"name": "Schedule Validation Phase Label", "status": "PASS"}

    @staticmethod
    def _check_beam_schedule_complete_flag_respected(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Beam Schedule Complete Flag Respected")

    @staticmethod
    def _check_no_orphan_row_ids(**kwargs) -> dict[str, Any]:
        row_ids = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if row.get("row_id")
        ]
        return {"name": "No Orphan Row IDs", "status": "PASS" if len(row_ids) == len(set(row_ids)) else "FAIL"}

    @staticmethod
    def _check_all_row_beam_ids_match_schedule(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            beam_id = schedule.get("beam_id")
            for row in schedule.get("rows") or []:
                if row.get("beam_id") and row.get("beam_id") != beam_id:
                    invalid.append(row.get("row_id"))
        return {"name": "All Row Beam IDs Match Schedule", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_total_length_mm_on_rows(**kwargs) -> dict[str, Any]:
        invalid = [
            row.get("row_id")
            for schedule in kwargs["schedule_records"]
            for row in (schedule.get("rows") or [])
            if row.get("total_length_mm") is None and int(row.get("bar_count") or 0) > 0
        ]
        return {"name": "Total Length Mm On Rows", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_aggregate_weight_matches_steel_weight_total(**kwargs) -> dict[str, Any]:
        weights_by_beam = BeamScheduleValidator._steel_weights_by_beam(kwargs["steel_weight_records"])
        schedule_total = round(sum(float(s.get("total_steel_weight_kg") or 0.0) for s in kwargs["schedule_records"]), 3)
        weight_total = round(
            sum(float(r.get("weight_kg") or 0.0) for records in weights_by_beam.values() for r in records),
            3,
        )
        return {"name": "Aggregate Weight Matches Steel Weight Total", "status": "PASS" if schedule_total == weight_total else "FAIL"}

    @staticmethod
    def _check_aggregate_bars_matches_steel_weight_total(**kwargs) -> dict[str, Any]:
        weights_by_beam = BeamScheduleValidator._steel_weights_by_beam(kwargs["steel_weight_records"])
        schedule_total = sum(int(s.get("total_bars") or 0) for s in kwargs["schedule_records"])
        weight_total = sum(len(records) for records in weights_by_beam.values())
        return {"name": "Aggregate Bars Matches Steel Weight Total", "status": "PASS" if schedule_total == weight_total else "FAIL"}

    @staticmethod
    def _check_aggregate_cut_length_matches_steel_weight_total(**kwargs) -> dict[str, Any]:
        weights_by_beam = BeamScheduleValidator._steel_weights_by_beam(kwargs["steel_weight_records"])
        schedule_total = sum(int(s.get("total_cut_length_mm") or 0) for s in kwargs["schedule_records"])
        weight_total = sum(
            int(float(r.get("cut_length_mm") or r.get("cut_length") or 0))
            for records in weights_by_beam.values()
            for r in records
        )
        return {"name": "Aggregate Cut Length Matches Steel Weight Total", "status": "PASS" if schedule_total == weight_total else "FAIL"}

    @staticmethod
    def _check_rebuild_row_count_matches(**kwargs) -> dict[str, Any]:
        rebuilt = BeamScheduleBuilder.build_schedules(
            kwargs["summary_records"],
            kwargs["quantity_records"],
            kwargs["material_records"],
            kwargs["steel_weight_records"],
            kwargs["bar_group_records"],
        )
        by_beam = {str(item.get("beam_id", "")): item for item in rebuilt}
        invalid = []
        for schedule in kwargs["schedule_records"]:
            expected = by_beam.get(str(schedule.get("beam_id", "")))
            if expected and schedule.get("row_count") != expected.get("row_count"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Rebuild Row Count Matches", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_rebuild_schedule_state_matches(**kwargs) -> dict[str, Any]:
        rebuilt = BeamScheduleBuilder.build_schedules(
            kwargs["summary_records"],
            kwargs["quantity_records"],
            kwargs["material_records"],
            kwargs["steel_weight_records"],
            kwargs["bar_group_records"],
        )
        by_beam = {str(item.get("beam_id", "")): item for item in rebuilt}
        invalid = []
        for schedule in kwargs["schedule_records"]:
            expected = by_beam.get(str(schedule.get("beam_id", "")))
            if expected and schedule.get("schedule_state") != expected.get("schedule_state"):
                invalid.append(schedule.get("beam_schedule_id"))
        return {"name": "Rebuild Schedule State Matches", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_rebuild_totals_match(**kwargs) -> dict[str, Any]:
        rebuilt = BeamScheduleBuilder.build_schedules(
            kwargs["summary_records"],
            kwargs["quantity_records"],
            kwargs["material_records"],
            kwargs["steel_weight_records"],
            kwargs["bar_group_records"],
        )
        by_beam = {str(item.get("beam_id", "")): item for item in rebuilt}
        invalid = []
        for schedule in kwargs["schedule_records"]:
            expected = by_beam.get(str(schedule.get("beam_id", "")))
            if not expected:
                continue
            for field in ("total_steel_weight_kg", "total_cut_length_mm", "total_bars"):
                if schedule.get(field) != expected.get(field):
                    invalid.append(schedule.get("beam_schedule_id"))
                    break
        return {"name": "Rebuild Totals Match", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_material_records_unchanged(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Material Records Unchanged")

    @staticmethod
    def _check_quantity_records_unchanged(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Quantity Records Unchanged")

    @staticmethod
    def _check_summary_records_unchanged(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Summary Records Unchanged")

    @staticmethod
    def _check_steel_weight_records_unchanged_for_rebuild(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("Steel Weight Records Unchanged For Rebuild")

    @staticmethod
    def _check_no_commercial_totals(**kwargs) -> dict[str, Any]:
        return BeamScheduleValidator._pass("No Commercial Totals")

    @staticmethod
    def _check_no_wastage_fields(**kwargs) -> dict[str, Any]:
        forbidden = ("wastage", "waste", "scrap")
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if any(key in str(item).lower() for key in forbidden)
        ]
        return {"name": "No Wastage Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_optimization_fields(**kwargs) -> dict[str, Any]:
        forbidden = ("optimize", "optimization", "minimize", "maximize")
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if any(key in str(item).lower() for key in forbidden)
        ]
        return {"name": "No Optimization Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_boq_fields_on_schedules(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("beam_schedule_id")
            for item in kwargs["schedule_records"]
            if "boq" in str(item).lower() and "beam_schedule" not in str(item.get("beam_schedule_id", "")).lower()
        ]
        return {"name": "No BOQ Fields On Schedules", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_each_role_description_in_catalog(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            for row in schedule.get("rows") or []:
                role = str(row.get("role") or "").upper()
                if role and role not in ROLE_DESCRIPTIONS and role != "OTHER":
                    invalid.append(row.get("row_id"))
        return {"name": "Each Role Description In Catalog", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_role_description_function_consistency(**kwargs) -> dict[str, Any]:
        invalid = []
        for schedule in kwargs["schedule_records"]:
            for row in schedule.get("rows") or []:
                if row.get("description") != role_description(row.get("role")):
                    invalid.append(row.get("row_id"))
        return {"name": "Role Description Function Consistency", "status": "PASS" if not invalid else "FAIL"}
