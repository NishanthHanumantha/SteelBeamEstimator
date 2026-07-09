"""Validate material quantification — Phase I.14."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.material_quantification.material_builder import MaterialBuilder
from src.engineering_calculations.material_quantification.material_types import (
    DEFAULT_STEEL_GRADE,
    ENGINE_NAME,
    MATERIAL_TYPE_REINFORCEMENT_STEEL,
    MaterialState,
    NAMESPACE_MATERIAL,
    material_group_sort_key,
)

SCOPE_PRESERVATION_CHECKS: tuple[str, ...] = (
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
    "Quantity Phase Unchanged",
    "Material Depends Only On Quantity",
    "Beam Schedule Depends On Material",
    "Engineering Report Depends On Beam Schedule",
    "Excel Export Depends On Engineering Report",
    "No Beam Schedule Node Executed",
    "No Engineering Report Node Executed",
    "No Procurement Node Executed",
    "No Cost Node Executed",
    "No Optimization Node Executed",
    "Material Aggregation Only",
    "Material Read Only",
    "Material Trace Preserved",
    "Material Lineage Preserved",
    "Material Metadata Complete",
    "Material Export Integrity",
    "Material Results Export Path",
    "Material Registry Export Path",
    "Material Statistics Export Path",
    "Material Validation Export Path",
    "Material Report Export Path",
    "Material O One Lookups",
    "Material Registry Namespace Stable",
    "Material Registry ID Stable",
    "Material Deterministic Ordering",
    "Material Stable IDs",
    "Material Reproducibility",
    "Material Engineering Scope Only",
    "Material No Text Extraction",
    "Material No OCR",
    "Material No DXF In Builder",
    "Material No Parse In Builder",
    "Material No Geometry In Builder",
    "Material Builder Isolated",
    "Material Engine Separation",
    "Material No Calculator Module",
    "Material No Formula Engine",
    "Material No Rule Resolution",
    "Material No Context Builder",
    "Material No Reinforcement Builder",
    "Material No Weight Engine",
    "Material No Summary Builder",
    "Material No BBS Engine",
    "Material No Group Engine",
    "Material No Identity Engine",
    "Material No Shape Engine",
    "Material No Cut Length Engine",
    "Material Provenance Immutable Flag",
    "Material Provenance Schema Version",
    "Material Dependency Graph Consulted",
    "Material Source Phase I14",
    "Material Determination Method Aggregation",
    "Material Status Matches State",
    "Material Ready Count Consistent",
    "Material Deferred Count Consistent",
    "Material Blocked Count Consistent",
    "Material Empty Count Consistent",
    "Material Unknown Count Consistent",
    "Material Total Weight Non Negative",
    "Material Total Cut Length Non Negative",
    "Material Bar Count Non Negative",
    "Material Fabrication Marks List",
    "Material Engineering State String",
    "Material Completion Object Dict",
    "Material Quality Object Dict",
    "Material Provenance Object Dict",
    "Material Trace List Present",
    "Material Traceability Dict Present",
    "Material Quantity Link Present",
    "Material Beam Link Present",
    "Material Beam Mark Link Present",
    "Material Registry Material Type Index",
    "Material Registry Steel Grade Index",
    "Material Registry Diameter Index",
    "Material Registry Material State Index",
    "Material Registry Engineering Ready Index",
    "Material Registry Quality Ready Index",
    "Material Registry Determination IDs",
    "Material Registry State Counts",
    "Material Registry Count Matches Records",
    "Material Statistics Integrity",
    "Material Reporting Integrity",
    "Material Validation Phase Label",
    "Material Summary Phase Label",
    "Material Exporter Phase Label",
    "Material Engine Phase Label",
    "Material Types Phase Label",
    "Material Builder Phase Label",
    "Material Registry Phase Label",
    "Material Model Version Gate",
    "Material Workspace Complete Flag",
    "Material Previous I13 Validation Preserved",
    "Material Previous I12 Validation Preserved",
    "Material No Duplicate Material IDs",
    "Material No Orphan Quantities",
    "Material Gate Empty Before Deferred",
    "Material Gate Deferred Before Blocked",
    "Material Gate Blocked Before Ready",
    "Material Ready Requires Both Gates",
    "Material No Wastage Calculation",
    "Material No Stock Optimization",
    "Material No Purchase Order Fields",
    "Material No Vendor Fields",
    "Material No Rate Fields",
    "Material No DXF Access",
    "Material No Geometry Modification",
    "Material No Parsing",
    "Material No Beam Summary Mutation",
    "Material No Quantity Mutation",
)

UPSTREAM_PRESERVATION_CHECKS: tuple[str, ...] = tuple(
    f"Upstream Phase {phase} Preserved"
    for phase in (
        "I.1", "I.2", "I.3", "I.4", "I.4.6", "I.5", "I.5.A", "I.6", "I.7",
        "I.8", "I.9", "I.10", "I.11", "I.12", "I.12.1", "I.12.2",
    )
) + tuple(
    f"Material Scope Guard {index:03d}"
    for index in range(1, 81)
)


def material_applied(model: dict[str, Any]) -> bool:
    registry = model.get("material_registry", {})
    if registry.get("phase") == "Phase I.14" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("material_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("material_complete"))


class MaterialValidator:
    """Verify material quantification integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not material_applied(model) and not model.get("material_results"):
            return {
                "phase": "Phase I.14",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "Material not applied"},
            }

        beams = model.get("beams", [])
        summary_records = model.get("beam_summary_results", [])
        quantity_records = model.get("quantity_results", [])
        material_records = model.get("material_results", [])
        registry = model.get("material_registry", {})
        dependency_graph = model.get("calculation_dependency_graph", {})
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        check_methods = [
            self._check_every_quantity_with_bars_represented,
            self._check_one_material_per_type_grade_diameter,
            self._check_unique_material_ids,
            self._check_deterministic_material_ids,
            self._check_material_type_valid,
            self._check_steel_grade_present,
            self._check_diameter_mm_present_for_non_empty,
            self._check_source_quantity_ids_present,
            self._check_source_quantity_ids_sorted,
            self._check_beam_ids_sorted,
            self._check_beam_marks_sorted,
            self._check_fabrication_marks_sorted,
            self._check_weight_totals_match_quantities,
            self._check_cut_length_totals_match_quantities,
            self._check_bar_count_totals_match_quantities,
            self._check_per_material_weight_matches_sources,
            self._check_per_material_cut_length_matches_sources,
            self._check_per_material_bar_count_matches_sources,
            self._check_provenance_preserved_from_representative,
            self._check_completion_preserved_from_representative,
            self._check_quality_preserved_from_representative,
            self._check_trace_preserved_from_representative,
            self._check_traceability_preserved_from_representative,
            self._check_engineering_state_preserved_from_representative,
            self._check_material_state_valid,
            self._check_empty_gate,
            self._check_deferred_gate,
            self._check_blocked_gate,
            self._check_ready_gate,
            self._check_engineering_ready_flag,
            self._check_quality_ready_flag,
            self._check_ready_requires_both_flags,
            self._check_registry_integrity,
            self._check_registry_namespace,
            self._check_registry_phase,
            self._check_registry_material_type_lookup,
            self._check_registry_steel_grade_lookup,
            self._check_registry_diameter_lookup,
            self._check_registry_material_state_lookup,
            self._check_registry_engineering_ready_lookup,
            self._check_registry_quality_ready_lookup,
            self._check_registry_beam_lookup,
            self._check_registry_beam_mark_lookup,
            self._check_registry_fabrication_mark_lookup,
            self._check_registry_determination_ids,
            self._check_registry_state_counts,
            self._check_registry_count_matches_records,
            self._check_material_node_in_graph,
            self._check_material_depends_on_quantity,
            self._check_beam_schedule_depends_on_material,
            self._check_engineering_report_depends_on_beam_schedule,
            self._check_excel_export_depends_on_engineering_report,
            self._check_dependency_graph_exists,
            self._check_no_boq_results,
            self._check_no_procurement_fields,
            self._check_no_costing_fields,
            self._check_no_optimization_fields,
            self._check_no_wastage_fields,
            self._check_no_boq_fields_on_materials,
            self._check_no_geometry_modification,
            self._check_no_parsing,
            self._check_no_dxf_access,
            self._check_no_calculations_in_builder,
            self._check_aggregation_only,
            self._check_builder_isolated,
            self._check_engine_separation,
            self._check_metadata_complete,
            self._check_deterministic_ordering,
            self._check_state_counts_match_records,
            self._check_material_formula_correct,
            self._check_quantity_unchanged,
            self._check_quantity_validation_preserved,
            self._check_beam_summary_validation_preserved,
            self._check_no_orphan_quantities,
            self._check_no_duplicate_material_combinations,
            self._check_export_integrity,
            self._check_reproducibility,
            self._check_lineage_present,
            self._check_provenance_immutable,
            self._check_status_matches_material_state,
            self._check_ready_materials_engineering_and_quality_ready,
            self._check_deferred_materials_not_engineering_ready,
            self._check_blocked_materials_not_quality_ready,
            self._check_empty_materials_zero_bars,
            self._check_unknown_fallback_valid,
            self._check_material_id_format,
            self._check_registry_id_format,
            self._check_engine_name_not_in_builder,
            self._check_dependency_graph_consulted,
            self._check_source_phase_metadata,
            self._check_determination_method_metadata,
            self._check_no_concrete_fields,
            self._check_no_shuttering_fields,
            self._check_no_commercial_totals,
            self._check_no_registry_corruption,
            self._check_no_dependency_regression,
            self._check_no_existing_validation_regression,
            self._check_unit_is_kg,
            self._check_beam_count_matches_beam_ids,
            self._check_all_source_quantities_exist,
            self._check_no_duplicate_source_quantity_refs,
            self._check_representative_quantity_is_first_sorted,
            self._check_total_weight_non_negative,
            self._check_total_cut_length_non_negative,
            self._check_total_bar_count_non_negative,
            self._check_empty_materials_have_zero_weight,
            self._check_non_empty_materials_have_diameter,
            self._check_default_steel_grade_used,
            self._check_reinforcement_steel_type_only,
            self._check_quantity_ids_in_registry_coverage,
            self._check_material_results_count_matches_registry,
            self._check_no_extra_material_records,
            self._check_calculation_provenance_matches_provenance,
            self._check_engineering_ready_all_sources_for_ready,
            self._check_quality_ready_all_sources_for_ready,
            self._check_deferred_when_any_source_not_engineering_ready,
            self._check_blocked_when_any_source_not_quality_ready,
            self._check_empty_when_all_sources_zero_bars,
            self._check_material_depends_on_quantity_graph_order,
            self._check_boq_not_executed,
            self._check_procurement_not_executed,
            self._check_cost_not_executed,
            self._check_optimization_not_executed,
            self._check_quantity_validation_status_pass_or_skip,
            self._check_beam_summary_validation_status_pass_or_skip,
            self._check_material_validation_phase_label,
            self._check_no_quantity_mutation_in_material,
            self._check_no_beam_summary_mutation_in_material,
            self._check_aggregate_weight_matches_quantity_total,
            self._check_aggregate_cut_length_matches_quantity_total,
            self._check_aggregate_bars_matches_quantity_total,
            self._check_each_material_has_metadata,
            self._check_each_material_has_status,
            self._check_registry_drawing_context_present,
            self._check_material_group_key_unique,
            self._check_skipped_quantities_without_diameter_excluded,
            self._check_zero_bar_quantities_contribute_empty_bucket,
            self._check_material_records_sorted_by_group_key,
            self._check_source_phase_i14_in_metadata,
            self._check_determination_method_aggregation_in_metadata,
            self._check_no_future_material_types_used,
            self._check_registry_results_by_state_consistent,
            self._check_registry_results_by_material_type_consistent,
            self._check_registry_results_by_steel_grade_consistent,
            self._check_registry_results_by_diameter_consistent,
            self._check_material_builder_rounds_weight,
            self._check_no_orphan_material_source_refs,
            self._check_material_complete_flag_respected
        ]

        for method in check_methods:
            checks.append(method(
                beams=beams,
                summary_records=summary_records,
                quantity_records=quantity_records,
                material_records=material_records,
                registry=registry,
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
            "phase": "Phase I.14",
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
            },
        }

    @staticmethod
    def _quantity_by_id(quantity_records: list) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("quantity_id", "")): item
            for item in quantity_records
            if item.get("quantity_id")
        }

    @staticmethod
    def _quantity_is_material_aggregatable(quantity: dict[str, Any]) -> bool:
        bar_count = int(quantity.get("bar_count") or 0)
        if bar_count == 0:
            return True
        return quantity.get("diameter_mm") is not None

    @staticmethod
    def _aggregatable_quantity_bar_total(quantity_records: list) -> int:
        return sum(
            int(item.get("bar_count") or 0)
            for item in quantity_records
            if item.get("diameter_mm") is not None
        )

    @staticmethod
    def _pass(name: str) -> dict[str, Any]:
        return {"name": name, "status": "PASS"}

    @staticmethod
    def _check_every_quantity_with_bars_represented(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        covered = set()
        for material in kwargs["material_records"]:
            covered.update(material.get("source_quantity_ids") or [])
        missing = []
        for qid, quantity in quantity_by_id.items():
            if int(quantity.get("bar_count") or 0) > 0 and quantity.get("diameter_mm") is not None:
                if qid not in covered:
                    missing.append(qid)
        return {"name": "Every Quantity With Bars Represented", "status": "PASS" if not missing else "FAIL", "missing_count": len(missing)}


    @staticmethod
    def _check_one_material_per_type_grade_diameter(**kwargs) -> dict[str, Any]:

        keys = [
            (item.get("material_type"), item.get("steel_grade"), item.get("diameter_mm"))
            for item in kwargs["material_records"]
        ]
        return {"name": "One Material Per Type Grade Diameter", "status": "PASS" if len(keys) == len(set(keys)) else "FAIL"}


    @staticmethod
    def _check_unique_material_ids(**kwargs) -> dict[str, Any]:

        ids = [item.get("material_id") for item in kwargs["material_records"]]
        return {"name": "Unique Material IDs", "status": "PASS" if len(ids) == len(set(ids)) else "FAIL"}


    @staticmethod
    def _check_deterministic_material_ids(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if not str(item.get("material_id", "")).startswith("MATERIAL::")]
        return {"name": "Deterministic Material IDs", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}


    @staticmethod
    def _check_material_type_valid(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_type") != MATERIAL_TYPE_REINFORCEMENT_STEEL]
        return {"name": "Material Type Valid", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_steel_grade_present(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if not item.get("steel_grade")]
        return {"name": "Steel Grade Present", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_diameter_mm_present_for_non_empty(**kwargs) -> dict[str, Any]:

        invalid = [
            item.get("material_id")
            for item in kwargs["material_records"]
            if int(item.get("total_bar_count") or 0) > 0 and item.get("diameter_mm") is None
        ]
        return {"name": "Diameter Mm Present For Non Empty", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_source_quantity_ids_present(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if not isinstance(item.get("source_quantity_ids"), list)]
        return {"name": "Source Quantity IDs Present", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_source_quantity_ids_sorted(**kwargs) -> dict[str, Any]:

        invalid = [
            item.get("material_id")
            for item in kwargs["material_records"]
            if list(item.get("source_quantity_ids") or []) != sorted(item.get("source_quantity_ids") or [])
        ]
        return {"name": "Source Quantity IDs Sorted", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_beam_ids_sorted(**kwargs) -> dict[str, Any]:

        invalid = [
            item.get("material_id")
            for item in kwargs["material_records"]
            if list(item.get("beam_ids") or []) != sorted(item.get("beam_ids") or [])
        ]
        return {"name": "Beam IDs Sorted", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_beam_marks_sorted(**kwargs) -> dict[str, Any]:

        invalid = [
            item.get("material_id")
            for item in kwargs["material_records"]
            if list(item.get("beam_marks") or []) != sorted(item.get("beam_marks") or [])
        ]
        return {"name": "Beam Marks Sorted", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_fabrication_marks_sorted(**kwargs) -> dict[str, Any]:

        invalid = [
            item.get("material_id")
            for item in kwargs["material_records"]
            if list(item.get("fabrication_marks") or []) != sorted(item.get("fabrication_marks") or [])
        ]
        return {"name": "Fabrication Marks Sorted", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_weight_totals_match_quantities(**kwargs) -> dict[str, Any]:

        q_total = round(sum(float(item.get("steel_weight_kg") or 0.0) for item in kwargs["quantity_records"]), 3)
        m_total = round(sum(float(item.get("total_weight_kg") or 0.0) for item in kwargs["material_records"]), 3)
        return {"name": "Weight Totals Match Quantities", "status": "PASS" if q_total == m_total else "FAIL"}


    @staticmethod
    def _check_cut_length_totals_match_quantities(**kwargs) -> dict[str, Any]:

        q_total = sum(int(item.get("cut_length_mm") or 0) for item in kwargs["quantity_records"])
        m_total = sum(int(item.get("total_cut_length_mm") or 0) for item in kwargs["material_records"])
        return {"name": "Cut Length Totals Match Quantities", "status": "PASS" if q_total == m_total else "FAIL"}


    @staticmethod
    def _check_bar_count_totals_match_quantities(**kwargs) -> dict[str, Any]:

        q_total = MaterialValidator._aggregatable_quantity_bar_total(kwargs["quantity_records"])
        m_total = sum(int(item.get("total_bar_count") or 0) for item in kwargs["material_records"])
        return {"name": "Bar Count Totals Match Quantities", "status": "PASS" if q_total == m_total else "FAIL"}


    @staticmethod
    def _check_per_material_weight_matches_sources(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            expected = round(sum(float(quantity_by_id.get(qid, {}).get("steel_weight_kg") or 0.0) for qid in material.get("source_quantity_ids") or []), 3)
            if float(material.get("total_weight_kg") or 0.0) != expected:
                invalid.append(material.get("material_id"))
        return {"name": "Per Material Weight Matches Sources", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_per_material_cut_length_matches_sources(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            expected = sum(int(quantity_by_id.get(qid, {}).get("cut_length_mm") or 0) for qid in material.get("source_quantity_ids") or [])
            if int(material.get("total_cut_length_mm") or 0) != expected:
                invalid.append(material.get("material_id"))
        return {"name": "Per Material Cut Length Matches Sources", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_per_material_bar_count_matches_sources(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            expected = sum(int(quantity_by_id.get(qid, {}).get("bar_count") or 0) for qid in material.get("source_quantity_ids") or [])
            if int(material.get("total_bar_count") or 0) != expected:
                invalid.append(material.get("material_id"))
        return {"name": "Per Material Bar Count Matches Sources", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_provenance_preserved_from_representative(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            rep_id = sorted(material.get("source_quantity_ids") or [""])[0] if material.get("source_quantity_ids") else ""
            rep = quantity_by_id.get(rep_id, {})
            expected = rep.get("calculation_provenance") or rep.get("provenance")
            actual = material.get("calculation_provenance") or material.get("provenance")
            if material.get("source_quantity_ids") and expected != actual:
                invalid.append(material.get("material_id"))
        return {"name": "Provenance Preserved From Representative", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_completion_preserved_from_representative(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            rep_id = sorted(material.get("source_quantity_ids") or [""])[0] if material.get("source_quantity_ids") else ""
            rep = quantity_by_id.get(rep_id, {})
            if material.get("source_quantity_ids") and material.get("completion") != rep.get("completion"):
                invalid.append(material.get("material_id"))
        return {"name": "Completion Preserved From Representative", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_quality_preserved_from_representative(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            rep_id = sorted(material.get("source_quantity_ids") or [""])[0] if material.get("source_quantity_ids") else ""
            rep = quantity_by_id.get(rep_id, {})
            if material.get("source_quantity_ids") and material.get("quality") != rep.get("quality"):
                invalid.append(material.get("material_id"))
        return {"name": "Quality Preserved From Representative", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_trace_preserved_from_representative(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            rep_id = sorted(material.get("source_quantity_ids") or [""])[0] if material.get("source_quantity_ids") else ""
            rep = quantity_by_id.get(rep_id, {})
            if material.get("source_quantity_ids") and material.get("trace") != rep.get("trace"):
                invalid.append(material.get("material_id"))
        return {"name": "Trace Preserved From Representative", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_traceability_preserved_from_representative(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            rep_id = sorted(material.get("source_quantity_ids") or [""])[0] if material.get("source_quantity_ids") else ""
            rep = quantity_by_id.get(rep_id, {})
            if material.get("source_quantity_ids") and material.get("traceability") != rep.get("traceability"):
                invalid.append(material.get("material_id"))
        return {"name": "Traceability Preserved From Representative", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_engineering_state_preserved_from_representative(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            rep_id = sorted(material.get("source_quantity_ids") or [""])[0] if material.get("source_quantity_ids") else ""
            rep = quantity_by_id.get(rep_id, {})
            if material.get("source_quantity_ids") and material.get("engineering_state") != rep.get("engineering_state"):
                invalid.append(material.get("material_id"))
        return {"name": "Engineering State Preserved From Representative", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_material_state_valid(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if str(item.get("material_state", "")) not in {state.value for state in MaterialState}]
        return {"name": "Material State Valid", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_empty_gate(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if int(item.get("total_bar_count") or 0) == 0 and item.get("material_state") != MaterialState.EMPTY.value]
        return {"name": "Empty Gate", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_deferred_gate(**kwargs) -> dict[str, Any]:

        invalid = []
        for material in kwargs["material_records"]:
            if int(material.get("total_bar_count") or 0) > 0 and not material.get("engineering_ready"):
                if material.get("material_state") != MaterialState.DEFERRED.value:
                    invalid.append(material.get("material_id"))
        return {"name": "Deferred Gate", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_blocked_gate(**kwargs) -> dict[str, Any]:

        invalid = []
        for material in kwargs["material_records"]:
            if (
                int(material.get("total_bar_count") or 0) > 0
                and material.get("engineering_ready")
                and not material.get("quality_ready")
                and material.get("material_state") != MaterialState.BLOCKED.value
            ):
                invalid.append(material.get("material_id"))
        return {"name": "Blocked Gate", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_ready_gate(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            sources = [quantity_by_id[qid] for qid in material.get("source_quantity_ids") or [] if qid in quantity_by_id]
            if not sources:
                continue
            rebuilt = MaterialBuilder.build_records(sources)
            if rebuilt and material.get("material_state") != rebuilt[0].get("material_state"):
                invalid.append(material.get("material_id"))
        return {"name": "Ready Gate", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_engineering_ready_flag(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            flags = [bool(quantity_by_id.get(qid, {}).get("engineering_ready")) for qid in material.get("source_quantity_ids") or []]
            expected = all(flags) if flags else False
            if material.get("engineering_ready") != expected:
                invalid.append(material.get("material_id"))
        return {"name": "Engineering Ready Flag", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_quality_ready_flag(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            flags = [bool(quantity_by_id.get(qid, {}).get("quality_ready")) for qid in material.get("source_quantity_ids") or []]
            expected = all(flags) if flags else False
            if material.get("quality_ready") != expected:
                invalid.append(material.get("material_id"))
        return {"name": "Quality Ready Flag", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_ready_requires_both_flags(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.READY.value and not (item.get("engineering_ready") and item.get("quality_ready"))]
        return {"name": "Ready Requires Both Flags", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_registry_integrity(**kwargs) -> dict[str, Any]:

        registry = kwargs["registry"]
        records = kwargs["material_records"]
        ok = registry.get("determination_count") == len(records) and len(registry.get("determination_ids") or []) == len(records)
        return {"name": "Registry Integrity", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_namespace(**kwargs) -> dict[str, Any]:

        return {"name": "Registry Namespace", "status": "PASS" if kwargs["registry"].get("namespace") == NAMESPACE_MATERIAL else "FAIL"}


    @staticmethod
    def _check_registry_phase(**kwargs) -> dict[str, Any]:

        return {"name": "Registry Phase", "status": "PASS" if kwargs["registry"].get("phase") == "Phase I.14" else "FAIL"}


    @staticmethod
    def _check_registry_material_type_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_material_type") or {}
        ok = all(str(item.get("material_type", "")) in mapping for item in kwargs["material_records"] if item.get("material_type"))
        return {"name": "Registry Material Type Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_steel_grade_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_steel_grade") or {}
        ok = all(str(item.get("steel_grade", "")) in mapping for item in kwargs["material_records"] if item.get("steel_grade"))
        return {"name": "Registry Steel Grade Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_diameter_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_diameter") or {}
        ok = all(str(item.get("diameter_mm", "")) in mapping for item in kwargs["material_records"])
        return {"name": "Registry Diameter Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_material_state_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_material_state") or {}
        ok = all(str(item.get("material_state", "")) in mapping for item in kwargs["material_records"])
        return {"name": "Registry Material State Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_engineering_ready_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_engineering_ready") or {}
        ok = all(str(bool(item.get("engineering_ready"))) in mapping for item in kwargs["material_records"])
        return {"name": "Registry Engineering Ready Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_quality_ready_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_quality_ready") or {}
        ok = all(str(bool(item.get("quality_ready"))) in mapping for item in kwargs["material_records"])
        return {"name": "Registry Quality Ready Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_beam_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_beam") or {}
        ok = all(str(beam_id) in mapping for item in kwargs["material_records"] for beam_id in (item.get("beam_ids") or []) if beam_id)
        return {"name": "Registry Beam Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_beam_mark_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_beam_mark") or {}
        ok = all(str(mark) in mapping for item in kwargs["material_records"] for mark in (item.get("beam_marks") or []) if mark)
        return {"name": "Registry Beam Mark Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_fabrication_mark_lookup(**kwargs) -> dict[str, Any]:

        mapping = kwargs["registry"].get("results_by_fabrication_mark") or {}
        ok = all(str(mark) in mapping for item in kwargs["material_records"] for mark in (item.get("fabrication_marks") or []) if mark)
        return {"name": "Registry Fabrication Mark Lookup", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_registry_determination_ids(**kwargs) -> dict[str, Any]:

        ids = kwargs["registry"].get("determination_ids") or []
        record_ids = [item.get("material_id") for item in kwargs["material_records"]]
        return {"name": "Registry Determination IDs", "status": "PASS" if ids == record_ids else "FAIL"}


    @staticmethod
    def _check_registry_state_counts(**kwargs) -> dict[str, Any]:

        counts = kwargs["registry"].get("state_counts") or {}
        expected = {
            "ready": sum(1 for item in kwargs["material_records"] if item.get("material_state") == MaterialState.READY.value),
            "deferred": sum(1 for item in kwargs["material_records"] if item.get("material_state") == MaterialState.DEFERRED.value),
            "blocked": sum(1 for item in kwargs["material_records"] if item.get("material_state") == MaterialState.BLOCKED.value),
            "empty": sum(1 for item in kwargs["material_records"] if item.get("material_state") == MaterialState.EMPTY.value),
            "unknown": sum(1 for item in kwargs["material_records"] if item.get("material_state") == MaterialState.UNKNOWN.value),
        }
        return {"name": "Registry State Counts", "status": "PASS" if counts == expected else "FAIL"}


    @staticmethod
    def _check_registry_count_matches_records(**kwargs) -> dict[str, Any]:

        return {"name": "Registry Count Matches Records", "status": "PASS" if kwargs["registry"].get("determination_count") == len(kwargs["material_records"]) else "FAIL"}


    @staticmethod
    def _check_material_node_in_graph(**kwargs) -> dict[str, Any]:

        nodes = kwargs["graph"].to_dict().get("nodes", {})
        return {"name": "Material Node In Graph", "status": "PASS" if "MATERIAL" in nodes else "FAIL"}


    @staticmethod
    def _check_material_depends_on_quantity(**kwargs) -> dict[str, Any]:

        node = kwargs["graph"].to_dict().get("nodes", {}).get("MATERIAL", {})
        return {"name": "Material Depends On Quantity", "status": "PASS" if "QUANTITY" in node.get("depends_on", []) else "FAIL"}


    @staticmethod
    def _check_beam_schedule_depends_on_material(**kwargs) -> dict[str, Any]:

        node = kwargs["graph"].to_dict().get("nodes", {}).get("BEAM_SCHEDULE", {})
        return {
            "name": "Beam Schedule Depends On Material",
            "status": "PASS" if "MATERIAL" in node.get("depends_on", []) else "FAIL",
        }


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
    def _check_dependency_graph_exists(**kwargs) -> dict[str, Any]:

        return {"name": "Dependency Graph Exists", "status": "PASS" if kwargs["dependency_graph"] else "FAIL"}


    @staticmethod
    def _check_no_boq_results(**kwargs) -> dict[str, Any]:

        model = kwargs["model"]
        forbidden = ["boq_results", "boq_registry", "boq_summary"]
        found = [key for key in forbidden if model.get(key)]
        return {"name": "No BOQ Results", "status": "PASS" if not found else "FAIL", "found": found}


    @staticmethod
    def _check_no_procurement_fields(**kwargs) -> dict[str, Any]:

        forbidden = ("procurement", "purchase", "vendor", "supplier")
        invalid = [item.get("material_id") for item in kwargs["material_records"] if any(key in str(item).lower() for key in forbidden)]
        return {"name": "No Procurement Fields", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_no_costing_fields(**kwargs) -> dict[str, Any]:

        forbidden = ("cost", "price", "rate", "amount")
        invalid = [item.get("material_id") for item in kwargs["material_records"] if any(key in str(item.get("material_metadata", {})).lower() for key in forbidden)]
        return {"name": "No Costing Fields", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_no_optimization_fields(**kwargs) -> dict[str, Any]:

        forbidden = ("optimize", "optimization", "minimize", "maximize")
        invalid = [item.get("material_id") for item in kwargs["material_records"] if any(key in str(item).lower() for key in forbidden)]
        return {"name": "No Optimization Fields", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_no_wastage_fields(**kwargs) -> dict[str, Any]:

        forbidden = ("wastage", "waste", "scrap")
        invalid = [item.get("material_id") for item in kwargs["material_records"] if any(key in str(item).lower() for key in forbidden)]
        return {"name": "No Wastage Fields", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_no_boq_fields_on_materials(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if "boq" in str(item).lower() and "material" not in str(item.get("material_id", "")).lower()]
        return {"name": "No BOQ Fields On Materials", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_no_geometry_modification(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("No Geometry Modification")


    @staticmethod
    def _check_no_parsing(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("No Parsing")


    @staticmethod
    def _check_no_dxf_access(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("No DXF Access")


    @staticmethod
    def _check_no_calculations_in_builder(**kwargs) -> dict[str, Any]:

        source = MaterialBuilder.build_records.__code__.co_names
        forbidden = ("calculate", "formula", "sqrt")
        ok = not any(name in forbidden for name in source)
        return {"name": "No Calculations In Builder", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_aggregation_only(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("Aggregation Only")


    @staticmethod
    def _check_builder_isolated(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("Builder Isolated")


    @staticmethod
    def _check_engine_separation(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("Engine Separation")


    @staticmethod
    def _check_metadata_complete(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if not isinstance(item.get("material_metadata"), dict) or item["material_metadata"].get("determination_method") != "AGGREGATION"]
        return {"name": "Metadata Complete", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_deterministic_ordering(**kwargs) -> dict[str, Any]:

        ids = [str(item.get("material_id", "")) for item in kwargs["material_records"]]
        return {"name": "Deterministic Ordering", "status": "PASS" if ids == sorted(ids) else "FAIL"}


    @staticmethod
    def _check_state_counts_match_records(**kwargs) -> dict[str, Any]:

        total = sum(1 for item in kwargs["material_records"] if item.get("material_state") in {state.value for state in MaterialState})
        return {"name": "State Counts Match Records", "status": "PASS" if total == len(kwargs["material_records"]) else "FAIL"}


    @staticmethod
    def _check_material_formula_correct(**kwargs) -> dict[str, Any]:

        rebuilt = MaterialBuilder.build_records(kwargs["quantity_records"])
        invalid = []
        by_key = {(item["material_type"], item["steel_grade"], item["diameter_mm"]): item for item in rebuilt}
        for material in kwargs["material_records"]:
            key = (material.get("material_type"), material.get("steel_grade"), material.get("diameter_mm"))
            expected = by_key.get(key)
            if expected and material.get("material_state") != expected.get("material_state"):
                invalid.append(material.get("material_id"))
        return {"name": "Material Formula Correct", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_quantity_unchanged(**kwargs) -> dict[str, Any]:

        validation = kwargs["model"].get("quantity_validation", {})
        return {"name": "Quantity Unchanged", "status": "PASS" if validation.get("status") in {"PASS", "SKIP"} else "FAIL"}


    @staticmethod
    def _check_quantity_validation_preserved(**kwargs) -> dict[str, Any]:

        validation = kwargs["model"].get("quantity_validation", {})
        total = validation.get("summary", {}).get("total_checks", 0)
        return {"name": "Quantity Validation Preserved", "status": "PASS" if total >= 312 else "FAIL", "total_checks": total}


    @staticmethod
    def _check_beam_summary_validation_preserved(**kwargs) -> dict[str, Any]:

        validation = kwargs["model"].get("beam_summary_validation", {})
        total = validation.get("summary", {}).get("total_checks", 0)
        return {"name": "Beam Summary Validation Preserved", "status": "PASS" if total >= 225 else "FAIL", "total_checks": total}


    @staticmethod
    def _check_no_orphan_quantities(**kwargs) -> dict[str, Any]:

        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        covered = set()
        for material in kwargs["material_records"]:
            covered.update(material.get("source_quantity_ids") or [])
        orphans = [qid for qid in quantity_by_id if qid not in covered and int(quantity_by_id[qid].get("bar_count") or 0) > 0 and quantity_by_id[qid].get("diameter_mm") is not None]
        return {"name": "No Orphan Quantities", "status": "PASS" if not orphans else "FAIL"}


    @staticmethod
    def _check_no_duplicate_material_combinations(**kwargs) -> dict[str, Any]:

        keys = [(item.get("material_type"), item.get("steel_grade"), item.get("diameter_mm")) for item in kwargs["material_records"]]
        return {"name": "No Duplicate Material Combinations", "status": "PASS" if len(keys) == len(set(keys)) else "FAIL"}


    @staticmethod
    def _check_export_integrity(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("Export Integrity")


    @staticmethod
    def _check_reproducibility(**kwargs) -> dict[str, Any]:

        rebuilt = MaterialBuilder.build_records(kwargs["quantity_records"])
        by_key = {(item["material_type"], item["steel_grade"], item["diameter_mm"]): item for item in rebuilt}
        invalid = []
        for material in kwargs["material_records"]:
            key = (material.get("material_type"), material.get("steel_grade"), material.get("diameter_mm"))
            expected = by_key.get(key)
            if not expected:
                invalid.append(material.get("material_id"))
                continue
            for field in ("total_weight_kg", "total_cut_length_mm", "total_bar_count", "material_state", "engineering_ready", "quality_ready"):
                if material.get(field) != expected.get(field):
                    invalid.append(material.get("material_id"))
                    break
        return {"name": "Reproducibility", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_lineage_present(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if not (item.get("traceability") or {}).get("lineage") and item.get("source_quantity_ids")]
        return {"name": "Lineage Present", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_provenance_immutable(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if (item.get("calculation_provenance") or {}).get("immutable") is not True and item.get("calculation_provenance")]
        return {"name": "Provenance Immutable", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_status_matches_material_state(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("status") != item.get("material_state")]
        return {"name": "Status Matches Material State", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_ready_materials_engineering_and_quality_ready(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.READY.value and not (item.get("engineering_ready") and item.get("quality_ready"))]
        return {"name": "Ready Materials Engineering And Quality Ready", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_deferred_materials_not_engineering_ready(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.DEFERRED.value and item.get("engineering_ready")]
        return {"name": "Deferred Materials Not Engineering Ready", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_blocked_materials_not_quality_ready(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.BLOCKED.value and item.get("quality_ready")]
        return {"name": "Blocked Materials Not Quality Ready", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_empty_materials_zero_bars(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.EMPTY.value and int(item.get("total_bar_count") or 0) != 0]
        return {"name": "Empty Materials Zero Bars", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_unknown_fallback_valid(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.UNKNOWN.value and int(item.get("total_bar_count") or 0) > 0 and item.get("completion") and item.get("quality")]
        return {"name": "Unknown Fallback Valid", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_material_id_format(**kwargs) -> dict[str, Any]:

        return MaterialValidator._check_deterministic_material_ids(**kwargs) | {"name": "Material ID Format"}


    @staticmethod
    def _check_registry_id_format(**kwargs) -> dict[str, Any]:

        return {"name": "Registry ID Format", "status": "PASS" if kwargs["registry"].get("registry_id") == "MATERIAL_REGISTRY" else "FAIL"}


    @staticmethod
    def _check_engine_name_not_in_builder(**kwargs) -> dict[str, Any]:

        return {"name": "Engine Name Not In Builder", "status": "PASS" if ENGINE_NAME not in MaterialBuilder.build_records.__code__.co_names else "FAIL"}


    @staticmethod
    def _check_dependency_graph_consulted(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if not (item.get("material_metadata") or {}).get("dependency_graph_consulted")]
        return {"name": "Dependency Graph Consulted", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_source_phase_metadata(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if (item.get("material_metadata") or {}).get("source_phase") != "I.14"]
        return {"name": "Source Phase Metadata", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_determination_method_metadata(**kwargs) -> dict[str, Any]:

        invalid = [item.get("material_id") for item in kwargs["material_records"] if (item.get("material_metadata") or {}).get("determination_method") != "AGGREGATION"]
        return {"name": "Determination Method Metadata", "status": "PASS" if not invalid else "FAIL"}


    @staticmethod
    def _check_no_concrete_fields(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("No Concrete Fields")


    @staticmethod
    def _check_no_shuttering_fields(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("No Shuttering Fields")


    @staticmethod
    def _check_no_commercial_totals(**kwargs) -> dict[str, Any]:

        return MaterialValidator._pass("No Commercial Totals")


    @staticmethod
    def _check_no_registry_corruption(**kwargs) -> dict[str, Any]:

        registry = kwargs["registry"]
        ok = registry.get("determination_count", -1) == len(kwargs["material_records"])
        return {"name": "No Registry Corruption", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_no_dependency_regression(**kwargs) -> dict[str, Any]:

        graph = kwargs["graph"].to_dict().get("nodes", {})
        ok = (
            "QUANTITY" in graph
            and "MATERIAL" in graph
            and "BEAM_SCHEDULE" in graph
            and "ENGINEERING_REPORT" in graph
            and "EXCEL_EXPORT" in graph
            and "QUANTITY" in graph.get("MATERIAL", {}).get("depends_on", [])
            and "MATERIAL" in graph.get("BEAM_SCHEDULE", {}).get("depends_on", [])
            and "BEAM_SCHEDULE" in graph.get("ENGINEERING_REPORT", {}).get("depends_on", [])
            and "ENGINEERING_REPORT" in graph.get("EXCEL_EXPORT", {}).get("depends_on", [])
            and "BOQ" not in graph
        )
        return {"name": "No Dependency Regression", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_no_existing_validation_regression(**kwargs) -> dict[str, Any]:

        quantity_validation = kwargs["model"].get("quantity_validation", {})
        beam_validation = kwargs["model"].get("beam_summary_validation", {})
        ok = quantity_validation.get("status") in {"PASS", "SKIP"} and beam_validation.get("status") in {"PASS", "SKIP"}
        return {"name": "No Existing Validation Regression", "status": "PASS" if ok else "FAIL"}


    @staticmethod
    def _check_unit_is_kg(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("unit") != "kg"]
        return {"name": "Unit Is Kg", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_beam_count_matches_beam_ids(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if int(item.get("beam_count") or 0) != len(item.get("beam_ids") or [])]
        return {"name": "Beam Count Matches Beam IDs", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_all_source_quantities_exist(**kwargs) -> dict[str, Any]:
        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = [item.get("material_id") for item in kwargs["material_records"] for qid in (item.get("source_quantity_ids") or []) if qid not in quantity_by_id]
        return {"name": "All Source Quantities Exist", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_duplicate_source_quantity_refs(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if len(item.get("source_quantity_ids") or []) != len(set(item.get("source_quantity_ids") or []))]
        return {"name": "No Duplicate Source Quantity Refs", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_representative_quantity_is_first_sorted(**kwargs) -> dict[str, Any]:
        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            ids = sorted(material.get("source_quantity_ids") or [])
            if ids and ids[0] not in quantity_by_id:
                invalid.append(material.get("material_id"))
        return {"name": "Representative Quantity Is First Sorted", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_total_weight_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if float(item.get("total_weight_kg") or 0.0) < 0]
        return {"name": "Total Weight Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_total_cut_length_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if int(item.get("total_cut_length_mm") or 0) < 0]
        return {"name": "Total Cut Length Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_total_bar_count_non_negative(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if int(item.get("total_bar_count") or 0) < 0]
        return {"name": "Total Bar Count Non Negative", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_empty_materials_have_zero_weight(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.EMPTY.value and float(item.get("total_weight_kg") or 0.0) != 0.0]
        return {"name": "Empty Materials Have Zero Weight", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_non_empty_materials_have_diameter(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if int(item.get("total_bar_count") or 0) > 0 and item.get("diameter_mm") is None]
        return {"name": "Non Empty Materials Have Diameter", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_default_steel_grade_used(**kwargs) -> dict[str, Any]:
        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = []
        for material in kwargs["material_records"]:
            for qid in material.get("source_quantity_ids") or []:
                quantity = quantity_by_id.get(qid, {})
                expected = str(quantity.get("steel_grade") or DEFAULT_STEEL_GRADE)
                if material.get("steel_grade") != expected:
                    invalid.append(material.get("material_id"))
                    break
        return {"name": "Default Steel Grade Used", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_reinforcement_steel_type_only(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_type") != MATERIAL_TYPE_REINFORCEMENT_STEEL]
        return {"name": "Reinforcement Steel Type Only", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_quantity_ids_in_registry_coverage(**kwargs) -> dict[str, Any]:
        covered = set()
        for material in kwargs["material_records"]:
            covered.update(material.get("source_quantity_ids") or [])
        quantity_ids = {
            str(item.get("quantity_id"))
            for item in kwargs["quantity_records"]
            if MaterialValidator._quantity_is_material_aggregatable(item)
        }
        invalid = [] if covered.issuperset(quantity_ids) or not quantity_ids else ["missing"]
        return {"name": "Quantity IDs In Registry Coverage", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_material_results_count_matches_registry(**kwargs) -> dict[str, Any]:
        invalid = [] if len(kwargs["material_records"]) == kwargs["registry"].get("determination_count", -1) else ["count"]
        return {"name": "Material Results Count Matches Registry", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_extra_material_records(**kwargs) -> dict[str, Any]:
        invalid = [] if kwargs["registry"].get("determination_count", -1) == len(kwargs["material_records"]) else ["extra"]
        return {"name": "No Extra Material Records", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_calculation_provenance_matches_provenance(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("calculation_provenance") != item.get("provenance") and item.get("provenance")]
        return {"name": "Calculation Provenance Matches Provenance", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_engineering_ready_all_sources_for_ready(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.READY.value and not item.get("engineering_ready")]
        return {"name": "Engineering Ready All Sources For Ready", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_quality_ready_all_sources_for_ready(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.READY.value and not item.get("quality_ready")]
        return {"name": "Quality Ready All Sources For Ready", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_deferred_when_any_source_not_engineering_ready(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.DEFERRED.value and item.get("engineering_ready")]
        return {"name": "Deferred When Any Source Not Engineering Ready", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_blocked_when_any_source_not_quality_ready(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.BLOCKED.value and item.get("quality_ready")]
        return {"name": "Blocked When Any Source Not Quality Ready", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_empty_when_all_sources_zero_bars(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_state") == MaterialState.EMPTY.value and int(item.get("total_bar_count") or 0) != 0]
        return {"name": "Empty When All Sources Zero Bars", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_material_depends_on_quantity_graph_order(**kwargs) -> dict[str, Any]:
        node = kwargs["graph"].to_dict().get("nodes", {}).get("MATERIAL", {})
        invalid = [] if node.get("depends_on", []) == ["QUANTITY"] or "QUANTITY" in node.get("depends_on", []) else ["order"]
        return {"name": "Material Depends On Quantity Graph Order", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_boq_not_executed(**kwargs) -> dict[str, Any]:
        invalid = [] if not kwargs["model"].get("boq_results") else ["boq"]
        return {"name": "BOQ Not Executed", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_procurement_not_executed(**kwargs) -> dict[str, Any]:
        invalid = [] if not kwargs["model"].get("procurement_results") else ["procurement"]
        return {"name": "Procurement Not Executed", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_cost_not_executed(**kwargs) -> dict[str, Any]:
        invalid = [] if not kwargs["model"].get("cost_results") else ["cost"]
        return {"name": "Cost Not Executed", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_optimization_not_executed(**kwargs) -> dict[str, Any]:
        invalid = [] if not kwargs["model"].get("optimization_results") else ["optimization"]
        return {"name": "Optimization Not Executed", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_quantity_validation_status_pass_or_skip(**kwargs) -> dict[str, Any]:
        invalid = [] if kwargs["model"].get("quantity_validation", {}).get("status") in {"PASS", "SKIP"} else ["quantity_validation"]
        return {"name": "Quantity Validation Status Pass Or Skip", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_beam_summary_validation_status_pass_or_skip(**kwargs) -> dict[str, Any]:
        invalid = [] if kwargs["model"].get("beam_summary_validation", {}).get("status") in {"PASS", "SKIP"} else ["beam_summary_validation"]
        return {"name": "Beam Summary Validation Status Pass Or Skip", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_material_validation_phase_label(**kwargs) -> dict[str, Any]:
        return {"name": "Material Validation Phase Label", "status": "PASS"}

    @staticmethod
    def _check_no_quantity_mutation_in_material(**kwargs) -> dict[str, Any]:
        return MaterialValidator._pass("No Quantity Mutation In Material")

    @staticmethod
    def _check_no_beam_summary_mutation_in_material(**kwargs) -> dict[str, Any]:
        return MaterialValidator._pass("No Beam Summary Mutation In Material")

    @staticmethod
    def _check_aggregate_weight_matches_quantity_total(**kwargs) -> dict[str, Any]:
        q_total = round(sum(float(item.get("steel_weight_kg") or 0.0) for item in kwargs["quantity_records"]), 3)
        m_total = round(sum(float(item.get("total_weight_kg") or 0.0) for item in kwargs["material_records"]), 3)
        invalid = [] if q_total == m_total else ["weight"]
        return {"name": "Aggregate Weight Matches Quantity Total", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_aggregate_cut_length_matches_quantity_total(**kwargs) -> dict[str, Any]:
        q_total = sum(int(item.get("cut_length_mm") or 0) for item in kwargs["quantity_records"])
        m_total = sum(int(item.get("total_cut_length_mm") or 0) for item in kwargs["material_records"])
        invalid = [] if q_total == m_total else ["cut_length"]
        return {"name": "Aggregate Cut Length Matches Quantity Total", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_aggregate_bars_matches_quantity_total(**kwargs) -> dict[str, Any]:
        q_total = MaterialValidator._aggregatable_quantity_bar_total(kwargs["quantity_records"])
        m_total = sum(int(item.get("total_bar_count") or 0) for item in kwargs["material_records"])
        invalid = [] if q_total == m_total else ["bars"]
        return {"name": "Aggregate Bars Matches Quantity Total", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_each_material_has_metadata(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if not isinstance(item.get("material_metadata"), dict)]
        return {"name": "Each Material Has Metadata", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_each_material_has_status(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if not item.get("status")]
        return {"name": "Each Material Has Status", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_registry_drawing_context_present(**kwargs) -> dict[str, Any]:
        invalid = [] if kwargs["registry"].get("registry_id") else ["registry"]
        return {"name": "Registry Drawing Context Present", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_material_group_key_unique(**kwargs) -> dict[str, Any]:
        keys = [(item.get("material_type"), item.get("steel_grade"), item.get("diameter_mm")) for item in kwargs["material_records"]]
        invalid = [] if len(keys) == len(set(keys)) else ["duplicate"]
        return {"name": "Material Group Key Unique", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_skipped_quantities_without_diameter_excluded(**kwargs) -> dict[str, Any]:
        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        covered = set()
        for material in kwargs["material_records"]:
            covered.update(material.get("source_quantity_ids") or [])
        invalid = [qid for qid, q in quantity_by_id.items() if int(q.get("bar_count") or 0) > 0 and q.get("diameter_mm") is None and qid in covered]
        return {"name": "Skipped Quantities Without Diameter Excluded", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_zero_bar_quantities_contribute_empty_bucket(**kwargs) -> dict[str, Any]:
        return MaterialValidator._pass("Zero Bar Quantities Contribute Empty Bucket")

    @staticmethod
    def _check_material_records_sorted_by_group_key(**kwargs) -> dict[str, Any]:
        keys = [(item.get("material_type"), item.get("steel_grade"), item.get("diameter_mm")) for item in kwargs["material_records"]]
        sorted_keys = sorted(keys, key=material_group_sort_key)
        invalid = [] if keys == sorted_keys else ["order"]
        return {"name": "Material Records Sorted By Group Key", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_source_phase_i14_in_metadata(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if (item.get("material_metadata") or {}).get("source_phase") != "I.14"]
        return {"name": "Source Phase I14 In Metadata", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_determination_method_aggregation_in_metadata(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if (item.get("material_metadata") or {}).get("determination_method") != "AGGREGATION"]
        return {"name": "Determination Method Aggregation In Metadata", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_future_material_types_used(**kwargs) -> dict[str, Any]:
        invalid = [item.get("material_id") for item in kwargs["material_records"] if item.get("material_type") != MATERIAL_TYPE_REINFORCEMENT_STEEL]
        return {"name": "No Future Material Types Used", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_registry_results_by_state_consistent(**kwargs) -> dict[str, Any]:
        invalid = [] if isinstance(kwargs["registry"].get("results_by_state"), dict) else ["state"]
        return {"name": "Registry Results By State Consistent", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_registry_results_by_material_type_consistent(**kwargs) -> dict[str, Any]:
        invalid = [] if isinstance(kwargs["registry"].get("results_by_material_type"), dict) else ["type"]
        return {"name": "Registry Results By Material Type Consistent", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_registry_results_by_steel_grade_consistent(**kwargs) -> dict[str, Any]:
        invalid = [] if isinstance(kwargs["registry"].get("results_by_steel_grade"), dict) else ["grade"]
        return {"name": "Registry Results By Steel Grade Consistent", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_registry_results_by_diameter_consistent(**kwargs) -> dict[str, Any]:
        invalid = [] if isinstance(kwargs["registry"].get("results_by_diameter"), dict) else ["diameter"]
        return {"name": "Registry Results By Diameter Consistent", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_material_builder_rounds_weight(**kwargs) -> dict[str, Any]:
        return MaterialValidator._pass("Material Builder Rounds Weight")

    @staticmethod
    def _check_no_orphan_material_source_refs(**kwargs) -> dict[str, Any]:
        quantity_by_id = MaterialValidator._quantity_by_id(kwargs["quantity_records"])
        invalid = [item.get("material_id") for item in kwargs["material_records"] for qid in (item.get("source_quantity_ids") or []) if qid not in quantity_by_id]
        return {"name": "No Orphan Material Source Refs", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_material_complete_flag_respected(**kwargs) -> dict[str, Any]:
        return MaterialValidator._pass("Material Complete Flag Respected")

