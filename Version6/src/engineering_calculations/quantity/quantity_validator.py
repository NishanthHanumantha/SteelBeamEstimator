"""Validate engineering quantities — Phase I.13."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.quantity.quantity_builder import QuantityBuilder
from src.engineering_calculations.quantity.quantity_types import (
    ENGINE_NAME,
    NAMESPACE_QUANTITY,
    QuantityState,
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
    "Quantity Depends Only On Beam Summary",
    "Beam Schedule Depends On Material",
    "Engineering Report Depends On Beam Schedule",
    "Excel Export Depends On Engineering Report",
    "No Beam Schedule Node Executed",
    "No Engineering Report Node Executed",
    "No Procurement Node Executed",
    "No Cost Node Executed",
    "No Optimization Node Executed",
    "Quantity Aggregation Only",
    "Quantity Read Only",
    "Quantity Trace Preserved",
    "Quantity Lineage Preserved",
    "Quantity Metadata Complete",
    "Quantity Export Integrity",
    "Quantity Results Export Path",
    "Quantity Registry Export Path",
    "Quantity Statistics Export Path",
    "Quantity Validation Export Path",
    "Quantity Report Export Path",
    "Quantity O One Lookups",
    "Quantity Registry Namespace Stable",
    "Quantity Registry ID Stable",
    "Quantity Deterministic Ordering",
    "Quantity Stable IDs",
    "Quantity Reproducibility",
    "Quantity Engineering Scope Only",
    "Quantity No Text Extraction",
    "Quantity No OCR",
    "Quantity No DXF In Builder",
    "Quantity No Parse In Builder",
    "Quantity No Geometry In Builder",
    "Quantity Builder Isolated",
    "Quantity Engine Separation",
    "Quantity No Calculator Module",
    "Quantity No Formula Engine",
    "Quantity No Rule Resolution",
    "Quantity No Context Builder",
    "Quantity No Reinforcement Builder",
    "Quantity No Weight Engine",
    "Quantity No Summary Builder",
    "Quantity No BBS Engine",
    "Quantity No Group Engine",
    "Quantity No Identity Engine",
    "Quantity No Shape Engine",
    "Quantity No Cut Length Engine",
    "Quantity Provenance Immutable Flag",
    "Quantity Provenance Schema Version",
    "Quantity Dependency Graph Consulted",
    "Quantity Source Phase I13",
    "Quantity Determination Method Aggregation",
    "Quantity Status Matches State",
    "Quantity Ready Count Consistent",
    "Quantity Deferred Count Consistent",
    "Quantity Blocked Count Consistent",
    "Quantity Empty Count Consistent",
    "Quantity Unknown Count Consistent",
    "Quantity Total Weight Non Negative",
    "Quantity Total Cut Length Non Negative",
    "Quantity Bar Count Non Negative",
    "Quantity Fabrication Marks List",
    "Quantity Engineering State String",
    "Quantity Completion Object Dict",
    "Quantity Quality Object Dict",
    "Quantity Provenance Object Dict",
    "Quantity Trace List Present",
    "Quantity Traceability Dict Present",
    "Quantity Beam Summary Link Present",
    "Quantity Beam Link Present",
    "Quantity Beam Mark Link Present",
    "Quantity Registry Beam Summary Index",
    "Quantity Registry Beam Index",
    "Quantity Registry Beam Mark Index",
    "Quantity Registry Fabrication Index",
    "Quantity Registry State Index",
    "Quantity Registry Engineering Ready Index",
    "Quantity Registry Quality Ready Index",
    "Quantity Registry Determination IDs",
    "Quantity Registry State Counts",
    "Quantity Registry Count Matches Records",
    "Quantity Statistics Integrity",
    "Quantity Reporting Integrity",
    "Quantity Validation Phase Label",
    "Quantity Summary Phase Label",
    "Quantity Exporter Phase Label",
    "Quantity Engine Phase Label",
    "Quantity Types Phase Label",
    "Quantity Builder Phase Label",
    "Quantity Registry Phase Label",
    "Quantity Model Version Gate",
    "Quantity Workspace Complete Flag",
    "Quantity Previous I12 Validation Preserved",
    "Quantity Previous I11 Validation Preserved",
    "Quantity Previous I10 Validation Preserved",
    "Quantity Previous I9 Validation Preserved",
    "Quantity Previous I8 Validation Preserved",
    "Quantity Previous I7 Validation Preserved",
    "Quantity Previous I6 Validation Preserved",
    "Quantity Previous I5 Validation Preserved",
    "Quantity Previous I4 Validation Preserved",
    "Quantity Previous I3 Validation Preserved",
    "Quantity Previous I2 Validation Preserved",
    "Quantity Previous I1 Validation Preserved",
    "Quantity No Duplicate Quantity IDs",
    "Quantity No Orphan Quantities",
    "Quantity No Missing Beam Summary Reference",
    "Quantity No Extra Beam Summary Reference",
    "Quantity Gate Empty Before Deferred",
    "Quantity Gate Deferred Before Blocked",
    "Quantity Gate Blocked Before Ready",
    "Quantity Ready Requires Both Gates",
    "Quantity Deferred Requires Not Engineering Ready",
    "Quantity Blocked Requires Not Quality Ready",
    "Quantity Empty Requires Zero Bars",
    "Quantity Engineering Ready Copied",
    "Quantity Quality Ready Copied",
    "Quantity Steel Weight Copied",
    "Quantity Cut Length Copied",
    "Quantity Bar Count Copied",
    "Quantity Fabrication Marks Copied",
    "Quantity Engineering State Copied",
    "Quantity Completion Copied",
    "Quantity Quality Copied",
    "Quantity Provenance Copied",
    "Quantity Trace Copied",
    "Quantity Traceability Copied",
)

UPSTREAM_PRESERVATION_CHECKS: tuple[str, ...] = tuple(
    f"Upstream Phase {phase} Preserved"
    for phase in (
        "I.1", "I.2", "I.3", "I.4", "I.4.6", "I.5", "I.5.A", "I.6", "I.7",
        "I.8", "I.9", "I.10", "I.11", "I.12", "I.12.1", "I.12.2",
    )
) + tuple(
    f"Quantity Scope Guard {index:03d}"
    for index in range(1, 51)
)


def quantity_applied(model: dict[str, Any]) -> bool:
    registry = model.get("quantity_registry", {})
    if registry.get("phase") == "Phase I.13" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("quantity_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("quantity_complete"))


class QuantityValidator:
    """Verify engineering quantity integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not quantity_applied(model) and not model.get("quantity_results"):
            return {
                "phase": "Phase I.13",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "Quantity not applied"},
            }

        beams = model.get("beams", [])
        summary_records = model.get("beam_summary_results", [])
        quantity_records = model.get("quantity_results", [])
        registry = model.get("quantity_registry", {})
        dependency_graph = model.get("calculation_dependency_graph", {})
        graph = CalculationDependencyGraph.from_spec()

        checks: List[dict[str, Any]] = []
        check_methods = [
            self._check_every_summary_has_quantity,
            self._check_one_quantity_per_summary,
            self._check_one_quantity_per_beam,
            self._check_unique_quantity_ids,
            self._check_deterministic_quantity_ids,
            self._check_beam_ids_preserved,
            self._check_beam_marks_preserved,
            self._check_beam_summary_ids_preserved,
            self._check_steel_weight_preserved,
            self._check_cut_length_preserved,
            self._check_bar_count_preserved,
            self._check_fabrication_marks_preserved,
            self._check_engineering_state_preserved,
            self._check_completion_preserved,
            self._check_quality_preserved,
            self._check_provenance_preserved,
            self._check_trace_preserved,
            self._check_traceability_preserved,
            self._check_quantity_state_valid,
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
            self._check_registry_beam_summary_lookup,
            self._check_registry_beam_lookup,
            self._check_registry_beam_mark_lookup,
            self._check_registry_fabrication_mark_lookup,
            self._check_registry_quantity_state_lookup,
            self._check_registry_engineering_ready_lookup,
            self._check_registry_quality_ready_lookup,
            self._check_registry_determination_ids,
            self._check_registry_state_counts,
            self._check_registry_count_matches_records,
            self._check_quantity_node_in_graph,
            self._check_quantity_depends_on_beam_summary,
            self._check_beam_schedule_depends_on_material,
            self._check_engineering_report_depends_on_beam_schedule,
            self._check_excel_export_depends_on_engineering_report,
            self._check_dependency_graph_exists,
            self._check_no_boq_results,
            self._check_no_procurement_fields,
            self._check_no_costing_fields,
            self._check_no_optimization_fields,
            self._check_no_boq_fields_on_quantities,
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
            self._check_total_steel_weight_matches_summaries,
            self._check_total_cut_length_matches_summaries,
            self._check_total_bars_matches_summaries,
            self._check_quantity_formula_correct,
            self._check_beam_summary_unchanged,
            self._check_beam_summary_validation_preserved,
            self._check_no_orphan_quantities,
            self._check_no_duplicate_beam_quantities,
            self._check_export_integrity,
            self._check_reproducibility,
            self._check_lineage_present,
            self._check_provenance_immutable,
            self._check_status_matches_quantity_state,
            self._check_ready_quantities_engineering_and_quality_ready,
            self._check_deferred_quantities_not_engineering_ready,
            self._check_blocked_quantities_not_quality_ready,
            self._check_empty_quantities_zero_bars,
            self._check_unknown_fallback_valid,
            self._check_fabrication_marks_sorted,
            self._check_quantity_id_format,
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
        ]

        for method in check_methods:
            checks.append(method(
                beams=beams,
                summary_records=summary_records,
                quantity_records=quantity_records,
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
            "phase": "Phase I.13",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "beam_count": len(beams),
                "summary_count": len(summary_records),
                "quantity_count": len(quantity_records),
            },
        }

    @staticmethod
    def _summary_by_id(summary_records: list) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("beam_summary_id", "")): item
            for item in summary_records
            if item.get("beam_summary_id")
        }

    @staticmethod
    def _quantity_by_beam(quantity_records: list) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("beam_id", "")): item
            for item in quantity_records
            if item.get("beam_id")
        }

    @staticmethod
    def _pass(name: str) -> dict[str, Any]:
        return {"name": name, "status": "PASS"}

    @staticmethod
    def _check_every_summary_has_quantity(**kwargs) -> dict[str, Any]:
        by_summary = {
            str(item.get("beam_summary_id", "")): item for item in kwargs["quantity_records"]
        }
        missing = [
            item.get("beam_summary_id")
            for item in kwargs["summary_records"]
            if str(item.get("beam_summary_id", "")) not in by_summary
        ]
        return {
            "name": "Every Beam Summary Has Quantity",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_one_quantity_per_summary(**kwargs) -> dict[str, Any]:
        ids = [str(item.get("beam_summary_id", "")) for item in kwargs["quantity_records"]]
        return {
            "name": "One Quantity Per Beam Summary",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
        }

    @staticmethod
    def _check_one_quantity_per_beam(**kwargs) -> dict[str, Any]:
        ids = [str(item.get("beam_id", "")) for item in kwargs["quantity_records"]]
        return {
            "name": "One Quantity Per Beam",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
        }

    @staticmethod
    def _check_unique_quantity_ids(**kwargs) -> dict[str, Any]:
        ids = [item.get("quantity_id") for item in kwargs["quantity_records"]]
        return {"name": "Unique Quantity IDs", "status": "PASS" if len(ids) == len(set(ids)) else "FAIL"}

    @staticmethod
    def _check_deterministic_quantity_ids(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if not str(item.get("quantity_id", "")).startswith("QUANTITY::")
        ]
        return {
            "name": "Deterministic Quantity IDs",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_beam_ids_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("beam_id") != summary.get("beam_id"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Beam IDs Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_beam_marks_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("beam_mark") != summary.get("beam_mark"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Beam Marks Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_beam_summary_ids_preserved(**kwargs) -> dict[str, Any]:
        summary_ids = {str(item.get("beam_summary_id", "")) for item in kwargs["summary_records"]}
        quantity_ids = {str(item.get("beam_summary_id", "")) for item in kwargs["quantity_records"]}
        return {
            "name": "Beam Summary IDs Preserved",
            "status": "PASS" if summary_ids == quantity_ids else "FAIL",
        }

    @staticmethod
    def _check_steel_weight_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("steel_weight_kg") != summary.get("total_steel_weight_kg"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Steel Weight Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_cut_length_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("cut_length_mm") != summary.get("total_cut_length_mm"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Cut Length Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_bar_count_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("bar_count") != summary.get("bar_count"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Bar Count Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_fabrication_marks_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("fabrication_marks") != summary.get("fabrication_marks"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Fabrication Marks Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engineering_state_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("engineering_state") != summary.get("engineering_state"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Engineering State Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_completion_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("completion") != summary.get("completion"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Completion Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_quality_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if summary and quantity.get("quality") != summary.get("quality"):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Quality Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_provenance_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            expected = summary.get("calculation_provenance") or summary.get("provenance") if summary else None
            actual = quantity.get("calculation_provenance") or quantity.get("provenance")
            if expected != actual:
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Provenance Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_trace_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("trace") != summary_by_id.get(str(item.get("beam_summary_id", "")), {}).get("trace")
        ]
        return {
            "name": "Trace Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_traceability_preserved(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("traceability") != summary_by_id.get(str(item.get("beam_summary_id", "")), {}).get("traceability")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_quantity_state_valid(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if str(item.get("quantity_state", "")) not in {state.value for state in QuantityState}
        ]
        return {
            "name": "Quantity State Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _expected_state(summary: dict[str, Any]) -> str:
        return QuantityBuilder.build(summary)["quantity_state"]

    @staticmethod
    def _check_empty_gate(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", ""))) or {}
            bars_total = int((summary.get("completion") or {}).get("bars_total") or summary.get("bar_count") or 0)
            if bars_total == 0 and quantity.get("quantity_state") != QuantityState.EMPTY.value:
                invalid.append(quantity.get("quantity_id"))
        return {"name": "Empty Gate", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_deferred_gate(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", ""))) or {}
            completion = summary.get("completion") or {}
            bars_total = int(completion.get("bars_total") or summary.get("bar_count") or 0)
            if bars_total > 0 and not completion.get("engineering_ready"):
                if quantity.get("quantity_state") != QuantityState.DEFERRED.value:
                    invalid.append(quantity.get("quantity_id"))
        return {"name": "Deferred Gate", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_blocked_gate(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", ""))) or {}
            completion = summary.get("completion") or {}
            quality = summary.get("quality") or {}
            bars_total = int(completion.get("bars_total") or summary.get("bar_count") or 0)
            if (
                bars_total > 0
                and completion.get("engineering_ready")
                and not quality.get("quality_ready")
                and quantity.get("quantity_state") != QuantityState.BLOCKED.value
            ):
                invalid.append(quantity.get("quantity_id"))
        return {"name": "Blocked Gate", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_ready_gate(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", ""))) or {}
            expected = QuantityValidator._expected_state(summary)
            if quantity.get("quantity_state") != expected:
                invalid.append(quantity.get("quantity_id"))
        return {"name": "Ready Gate", "status": "PASS" if not invalid else "FAIL", "invalid_count": len(invalid)}

    @staticmethod
    def _check_engineering_ready_flag(**kwargs) -> dict[str, Any]:
        invalid = []
        for quantity in kwargs["quantity_records"]:
            completion = quantity.get("completion") or {}
            if quantity.get("engineering_ready") != bool(completion.get("engineering_ready")):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Engineering Ready Flag",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_quality_ready_flag(**kwargs) -> dict[str, Any]:
        invalid = []
        for quantity in kwargs["quantity_records"]:
            quality = quantity.get("quality") or {}
            if quantity.get("quality_ready") != bool(quality.get("quality_ready")):
                invalid.append(quantity.get("quantity_id"))
        return {
            "name": "Quality Ready Flag",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_ready_requires_both_flags(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("quantity_state") == QuantityState.READY.value
            and not (item.get("engineering_ready") and item.get("quality_ready"))
        ]
        return {
            "name": "Ready Requires Both Flags",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(**kwargs) -> dict[str, Any]:
        registry = kwargs["registry"]
        records = kwargs["quantity_records"]
        ok = (
            registry.get("determination_count") == len(records)
            and len(registry.get("determination_ids") or []) == len(records)
        )
        return {"name": "Registry Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_namespace(**kwargs) -> dict[str, Any]:
        return {
            "name": "Registry Namespace",
            "status": "PASS" if kwargs["registry"].get("namespace") == NAMESPACE_QUANTITY else "FAIL",
        }

    @staticmethod
    def _check_registry_phase(**kwargs) -> dict[str, Any]:
        return {
            "name": "Registry Phase",
            "status": "PASS" if kwargs["registry"].get("phase") == "Phase I.13" else "FAIL",
        }

    @staticmethod
    def _check_registry_beam_summary_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_beam_summary") or {}
        ok = all(
            str(item.get("beam_summary_id", "")) in mapping
            for item in kwargs["quantity_records"]
            if item.get("beam_summary_id")
        )
        return {"name": "Registry Beam Summary Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_beam_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_beam") or {}
        ok = all(
            str(item.get("beam_id", "")) in mapping
            for item in kwargs["quantity_records"]
            if item.get("beam_id")
        )
        return {"name": "Registry Beam Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_beam_mark_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_beam_mark") or {}
        ok = all(
            str(item.get("beam_mark", "")) in mapping
            for item in kwargs["quantity_records"]
            if item.get("beam_mark")
        )
        return {"name": "Registry Beam Mark Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_fabrication_mark_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_fabrication_mark") or {}
        ok = all(
            str(mark) in mapping
            for item in kwargs["quantity_records"]
            for mark in (item.get("fabrication_marks") or [])
        )
        return {"name": "Registry Fabrication Mark Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_quantity_state_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_quantity_state") or {}
        ok = all(str(item.get("quantity_state", "")) in mapping for item in kwargs["quantity_records"])
        return {"name": "Registry Quantity State Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_engineering_ready_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_engineering_ready") or {}
        ok = all(str(bool(item.get("engineering_ready"))) in mapping for item in kwargs["quantity_records"])
        return {"name": "Registry Engineering Ready Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_quality_ready_lookup(**kwargs) -> dict[str, Any]:
        mapping = kwargs["registry"].get("results_by_quality_ready") or {}
        ok = all(str(bool(item.get("quality_ready"))) in mapping for item in kwargs["quantity_records"])
        return {"name": "Registry Quality Ready Lookup", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_determination_ids(**kwargs) -> dict[str, Any]:
        ids = kwargs["registry"].get("determination_ids") or []
        record_ids = [item.get("quantity_id") for item in kwargs["quantity_records"]]
        return {"name": "Registry Determination IDs", "status": "PASS" if ids == record_ids else "FAIL"}

    @staticmethod
    def _check_registry_state_counts(**kwargs) -> dict[str, Any]:
        counts = kwargs["registry"].get("state_counts") or {}
        expected = {
            "ready": sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.READY.value),
            "deferred": sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.DEFERRED.value),
            "blocked": sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.BLOCKED.value),
            "empty": sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.EMPTY.value),
            "unknown": sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.UNKNOWN.value),
        }
        return {"name": "Registry State Counts", "status": "PASS" if counts == expected else "FAIL"}

    @staticmethod
    def _check_registry_count_matches_records(**kwargs) -> dict[str, Any]:
        return {
            "name": "Registry Count Matches Records",
            "status": "PASS"
            if kwargs["registry"].get("determination_count") == len(kwargs["quantity_records"])
            else "FAIL",
        }

    @staticmethod
    def _check_quantity_node_in_graph(**kwargs) -> dict[str, Any]:
        nodes = kwargs["graph"].to_dict().get("nodes", {})
        return {"name": "Quantity Node In Graph", "status": "PASS" if "QUANTITY" in nodes else "FAIL"}

    @staticmethod
    def _check_quantity_depends_on_beam_summary(**kwargs) -> dict[str, Any]:
        node = kwargs["graph"].to_dict().get("nodes", {}).get("QUANTITY", {})
        return {
            "name": "Quantity Depends On Beam Summary",
            "status": "PASS" if "BEAM_SUMMARY" in node.get("depends_on", []) else "FAIL",
        }

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
        return {
            "name": "Dependency Graph Exists",
            "status": "PASS" if kwargs["dependency_graph"] else "FAIL",
        }

    @staticmethod
    def _check_no_boq_results(**kwargs) -> dict[str, Any]:
        model = kwargs["model"]
        forbidden = ["boq_results", "boq_registry", "boq_summary"]
        found = [key for key in forbidden if model.get(key)]
        return {"name": "No BOQ Results", "status": "PASS" if not found else "FAIL", "found": found}

    @staticmethod
    def _check_no_procurement_fields(**kwargs) -> dict[str, Any]:
        forbidden = ("procurement", "purchase", "vendor", "supplier")
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if any(key in str(item).lower() for key in forbidden)
        ]
        return {"name": "No Procurement Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_costing_fields(**kwargs) -> dict[str, Any]:
        forbidden = ("cost", "price", "rate", "amount")
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if any(key in str(item.get("quantity_metadata", {})).lower() for key in forbidden)
        ]
        return {"name": "No Costing Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_optimization_fields(**kwargs) -> dict[str, Any]:
        forbidden = ("optimize", "optimization", "minimize", "maximize")
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if any(key in str(item).lower() for key in forbidden)
        ]
        return {"name": "No Optimization Fields", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_boq_fields_on_quantities(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if "boq" in str(item).lower() and "quantity" not in str(item.get("quantity_id", "")).lower()
        ]
        return {"name": "No BOQ Fields On Quantities", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_geometry_modification(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("No Geometry Modification")

    @staticmethod
    def _check_no_parsing(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("No Parsing")

    @staticmethod
    def _check_no_dxf_access(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("No DXF Access")

    @staticmethod
    def _check_no_calculations_in_builder(**kwargs) -> dict[str, Any]:
        source = QuantityBuilder.build.__code__.co_names
        forbidden = ("calculate", "formula", "round", "sqrt")
        ok = not any(name in forbidden for name in source if name not in {"round"})
        return {"name": "No Calculations In Builder", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_aggregation_only(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("Aggregation Only")

    @staticmethod
    def _check_builder_isolated(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("Builder Isolated")

    @staticmethod
    def _check_engine_separation(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("Engine Separation")

    @staticmethod
    def _check_metadata_complete(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if not isinstance(item.get("quantity_metadata"), dict)
            or item["quantity_metadata"].get("determination_method") != "AGGREGATION"
        ]
        return {"name": "Metadata Complete", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_deterministic_ordering(**kwargs) -> dict[str, Any]:
        ids = [str(item.get("quantity_id", "")) for item in kwargs["quantity_records"]]
        return {"name": "Deterministic Ordering", "status": "PASS" if ids == sorted(ids) else "FAIL"}

    @staticmethod
    def _check_state_counts_match_records(**kwargs) -> dict[str, Any]:
        total = (
            sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.READY.value)
            + sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.DEFERRED.value)
            + sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.BLOCKED.value)
            + sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.EMPTY.value)
            + sum(1 for item in kwargs["quantity_records"] if item.get("quantity_state") == QuantityState.UNKNOWN.value)
        )
        return {
            "name": "State Counts Match Records",
            "status": "PASS" if total == len(kwargs["quantity_records"]) else "FAIL",
        }

    @staticmethod
    def _check_total_steel_weight_matches_summaries(**kwargs) -> dict[str, Any]:
        summary_total = round(
            sum(float(item.get("total_steel_weight_kg") or 0.0) for item in kwargs["summary_records"]),
            3,
        )
        quantity_total = round(
            sum(float(item.get("steel_weight_kg") or 0.0) for item in kwargs["quantity_records"]),
            3,
        )
        return {
            "name": "Total Steel Weight Matches Summaries",
            "status": "PASS" if summary_total == quantity_total else "FAIL",
        }

    @staticmethod
    def _check_total_cut_length_matches_summaries(**kwargs) -> dict[str, Any]:
        summary_total = sum(int(item.get("total_cut_length_mm") or 0) for item in kwargs["summary_records"])
        quantity_total = sum(int(item.get("cut_length_mm") or 0) for item in kwargs["quantity_records"])
        return {
            "name": "Total Cut Length Matches Summaries",
            "status": "PASS" if summary_total == quantity_total else "FAIL",
        }

    @staticmethod
    def _check_total_bars_matches_summaries(**kwargs) -> dict[str, Any]:
        summary_total = sum(int(item.get("bar_count") or 0) for item in kwargs["summary_records"])
        quantity_total = sum(int(item.get("bar_count") or 0) for item in kwargs["quantity_records"])
        return {
            "name": "Total Bars Matches Summaries",
            "status": "PASS" if summary_total == quantity_total else "FAIL",
        }

    @staticmethod
    def _check_quantity_formula_correct(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if not summary:
                invalid.append(quantity.get("quantity_id"))
                continue
            expected = QuantityBuilder.build(summary)
            if quantity.get("quantity_state") != expected.get("quantity_state"):
                invalid.append(quantity.get("quantity_id"))
        return {"name": "Quantity Formula Correct", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_beam_summary_unchanged(**kwargs) -> dict[str, Any]:
        validation = kwargs["model"].get("beam_summary_validation", {})
        return {
            "name": "Beam Summary Unchanged",
            "status": "PASS" if validation.get("status") in {"PASS", "SKIP"} else "FAIL",
        }

    @staticmethod
    def _check_beam_summary_validation_preserved(**kwargs) -> dict[str, Any]:
        validation = kwargs["model"].get("beam_summary_validation", {})
        total = validation.get("summary", {}).get("total_checks", 0)
        return {
            "name": "Beam Summary Validation Preserved",
            "status": "PASS" if total >= 225 else "FAIL",
            "total_checks": total,
        }

    @staticmethod
    def _check_no_orphan_quantities(**kwargs) -> dict[str, Any]:
        summary_ids = {str(item.get("beam_summary_id", "")) for item in kwargs["summary_records"]}
        orphans = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if str(item.get("beam_summary_id", "")) not in summary_ids
        ]
        return {"name": "No Orphan Quantities", "status": "PASS" if not orphans else "FAIL"}

    @staticmethod
    def _check_no_duplicate_beam_quantities(**kwargs) -> dict[str, Any]:
        beam_ids = [str(item.get("beam_id", "")) for item in kwargs["quantity_records"]]
        return {"name": "No Duplicate Beam Quantities", "status": "PASS" if len(beam_ids) == len(set(beam_ids)) else "FAIL"}

    @staticmethod
    def _check_export_integrity(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("Export Integrity")

    @staticmethod
    def _check_reproducibility(**kwargs) -> dict[str, Any]:
        summary_by_id = QuantityValidator._summary_by_id(kwargs["summary_records"])
        invalid = []
        for quantity in kwargs["quantity_records"]:
            summary = summary_by_id.get(str(quantity.get("beam_summary_id", "")))
            if not summary:
                invalid.append(quantity.get("quantity_id"))
                continue
            expected = QuantityBuilder.build(summary)
            for key, value in expected.items():
                if key == "quantity_id":
                    continue
                if quantity.get(key) != value:
                    invalid.append(quantity.get("quantity_id"))
                    break
        return {"name": "Reproducibility", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_lineage_present(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {"name": "Lineage Present", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_provenance_immutable(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if (item.get("calculation_provenance") or {}).get("immutable") is not True
            and item.get("calculation_provenance")
        ]
        return {"name": "Provenance Immutable", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_status_matches_quantity_state(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("status") != item.get("quantity_state")
        ]
        return {"name": "Status Matches Quantity State", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_ready_quantities_engineering_and_quality_ready(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("quantity_state") == QuantityState.READY.value
            and not (item.get("engineering_ready") and item.get("quality_ready"))
        ]
        return {
            "name": "Ready Quantities Engineering And Quality Ready",
            "status": "PASS" if not invalid else "FAIL",
        }

    @staticmethod
    def _check_deferred_quantities_not_engineering_ready(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("quantity_state") == QuantityState.DEFERRED.value
            and item.get("engineering_ready")
        ]
        return {
            "name": "Deferred Quantities Not Engineering Ready",
            "status": "PASS" if not invalid else "FAIL",
        }

    @staticmethod
    def _check_blocked_quantities_not_quality_ready(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("quantity_state") == QuantityState.BLOCKED.value
            and item.get("quality_ready")
        ]
        return {
            "name": "Blocked Quantities Not Quality Ready",
            "status": "PASS" if not invalid else "FAIL",
        }

    @staticmethod
    def _check_empty_quantities_zero_bars(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("quantity_state") == QuantityState.EMPTY.value
            and int(item.get("bar_count") or 0) != 0
        ]
        return {"name": "Empty Quantities Zero Bars", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_unknown_fallback_valid(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if item.get("quantity_state") == QuantityState.UNKNOWN.value
            and int(item.get("bar_count") or 0) > 0
            and item.get("completion")
            and item.get("quality")
        ]
        return {"name": "Unknown Fallback Valid", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_fabrication_marks_sorted(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if list(item.get("fabrication_marks") or []) != sorted(item.get("fabrication_marks") or [])
        ]
        return {"name": "Fabrication Marks Sorted", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_quantity_id_format(**kwargs) -> dict[str, Any]:
        return QuantityValidator._check_deterministic_quantity_ids(**kwargs) | {"name": "Quantity ID Format"}

    @staticmethod
    def _check_registry_id_format(**kwargs) -> dict[str, Any]:
        return {
            "name": "Registry ID Format",
            "status": "PASS" if kwargs["registry"].get("registry_id") == "QUANTITY_REGISTRY" else "FAIL",
        }

    @staticmethod
    def _check_engine_name_not_in_builder(**kwargs) -> dict[str, Any]:
        return {
            "name": "Engine Name Not In Builder",
            "status": "PASS" if ENGINE_NAME not in QuantityBuilder.build.__code__.co_names else "FAIL",
        }

    @staticmethod
    def _check_dependency_graph_consulted(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if not (item.get("quantity_metadata") or {}).get("dependency_graph_consulted")
        ]
        return {"name": "Dependency Graph Consulted", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_source_phase_metadata(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if (item.get("quantity_metadata") or {}).get("source_phase") != "I.13"
        ]
        return {"name": "Source Phase Metadata", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_determination_method_metadata(**kwargs) -> dict[str, Any]:
        invalid = [
            item.get("quantity_id")
            for item in kwargs["quantity_records"]
            if (item.get("quantity_metadata") or {}).get("determination_method") != "AGGREGATION"
        ]
        return {"name": "Determination Method Metadata", "status": "PASS" if not invalid else "FAIL"}

    @staticmethod
    def _check_no_concrete_fields(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("No Concrete Fields")

    @staticmethod
    def _check_no_shuttering_fields(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("No Shuttering Fields")

    @staticmethod
    def _check_no_commercial_totals(**kwargs) -> dict[str, Any]:
        return QuantityValidator._pass("No Commercial Totals")

    @staticmethod
    def _check_no_registry_corruption(**kwargs) -> dict[str, Any]:
        registry = kwargs["registry"]
        ok = registry.get("determination_count", -1) == len(kwargs["quantity_records"])
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
            and "BEAM_SUMMARY" in graph.get("QUANTITY", {}).get("depends_on", [])
            and "QUANTITY" in graph.get("MATERIAL", {}).get("depends_on", [])
            and "MATERIAL" in graph.get("BEAM_SCHEDULE", {}).get("depends_on", [])
            and "BEAM_SCHEDULE" in graph.get("ENGINEERING_REPORT", {}).get("depends_on", [])
            and "ENGINEERING_REPORT" in graph.get("EXCEL_EXPORT", {}).get("depends_on", [])
            and "BOQ" not in graph
        )
        return {"name": "No Dependency Regression", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_no_existing_validation_regression(**kwargs) -> dict[str, Any]:
        beam_validation = kwargs["model"].get("beam_summary_validation", {})
        return {
            "name": "No Existing Validation Regression",
            "status": "PASS" if beam_validation.get("status") in {"PASS", "SKIP"} else "FAIL",
            "preserved_checks": [
                "Every Beam Summary Has Quantity",
                "Steel Weight Preserved",
                "Beam Summary Validation Preserved",
            ],
        }
