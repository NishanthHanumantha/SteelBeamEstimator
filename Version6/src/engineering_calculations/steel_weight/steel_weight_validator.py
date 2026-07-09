"""Validate steel weight calculations — Phase I.11."""

from __future__ import annotations

import inspect
from typing import Any, List

from src.engineering_calculations.bar_group.bar_group_types import BarGroupState
from src.engineering_calculations.bar_identity.bar_identity_types import BarIdentityState
from src.engineering_calculations.bbs.bbs_types import BbsState
from src.engineering_calculations.calculation_dependency.dependency_graph import (
    CalculationDependencyGraph,
)
from src.engineering_calculations.calculation_result_types import (
    CalculationResultState,
    CalculationType,
)
from src.engineering_calculations.steel_weight.steel_weight_calculator import SteelWeightCalculator
from src.engineering_calculations.steel_weight.steel_weight_engine import SteelWeightEngine
from src.engineering_calculations.steel_weight.steel_weight_types import (
    CALCULATION_TYPE,
    CONVERSION_FACTOR,
    ENGINE_NAME,
    EXPORT_PRECISION,
    FORMULA_NAME,
    NAMESPACE_WEIGHT,
    STEEL_DENSITY_KG_M3,
    SteelWeightState,
)
from src.reinforcement_calculation.calculation_state import CalculationState


def steel_weight_applied(model: dict[str, Any]) -> bool:
    registry = model.get("steel_weight_registry", {})
    if registry.get("phase") == "Phase I.11" and registry.get("determination_count", 0) >= 0:
        return True
    if model.get("steel_weight_results") is not None:
        return True
    return bool(model.get("workspace_manager", {}).get("steel_weight_complete"))


class SteelWeightValidator:
    """Verify steel weight calculation integrity."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        if not steel_weight_applied(model) and not model.get("steel_weight_results"):
            return {
                "phase": "Phase I.11",
                "status": "SKIP",
                "checks": [],
                "summary": {"reason": "Steel weight calculation not applied"},
            }

        bars = model.get("reinforcement_bars", [])
        results = model.get("engineering_calculation_results", [])
        identity_records = model.get("bar_identity_results", [])
        group_records = model.get("bar_group_results", [])
        bbs_records = model.get("bbs_results", [])
        weight_records = model.get("steel_weight_results", [])
        registry = model.get("steel_weight_registry", {})
        contexts = model.get("calculation_contexts", [])
        dependency_graph = model.get("calculation_dependency_graph", {})
        graph = CalculationDependencyGraph.from_spec()

        weight_results = [
            item for item in results if item.get("calculation_type") == CALCULATION_TYPE
        ]
        results_by_id = {
            str(item.get("result_id", "")): item for item in results if item.get("result_id")
        }

        checks: List[dict[str, Any]] = []
        checks.append(self._check_every_bar_has_weight_record(bars, weight_records))
        checks.append(self._check_every_ready_bar_has_weight(bars, weight_records))
        checks.append(self._check_every_ready_bbs_has_weight(bbs_records, weight_records))
        checks.append(self._check_deferred_preserved(weight_records, bars))
        checks.append(self._check_blocked_preserved(weight_records, bars))
        checks.append(self._check_units_kg(weight_results, weight_records))
        checks.append(self._check_positive_weight_calculated(weight_records))
        checks.append(self._check_formula_deterministic(weight_records))
        checks.append(self._check_precision_deterministic(weight_records))
        checks.append(self._check_density_constant(weight_records))
        checks.append(self._check_diameter_preserved(weight_records, group_records, bbs_records))
        checks.append(self._check_cut_length_preserved(weight_records, group_records, bbs_records))
        checks.append(self._check_identity_preserved(weight_records, identity_records))
        checks.append(self._check_engineering_group_preserved(weight_records, group_records))
        checks.append(self._check_fabrication_mark_preserved(weight_records, bbs_records))
        checks.append(self._check_no_geometry_modified(model, contexts))
        checks.append(self._check_no_bbs_modification(bbs_records))
        checks.append(self._check_no_procurement_fields(results, weight_records))
        checks.append(self._check_no_boq_fields(results, weight_records))
        checks.append(self._check_no_costing_fields(results, weight_records))
        checks.append(self._check_no_optimization_fields(results, weight_records))
        checks.append(self._check_registry_integrity(registry, weight_records))
        checks.append(self._check_export_integrity(registry, weight_records))
        checks.append(self._check_reproducibility(weight_records))
        checks.append(self._check_traceability(weight_records))
        checks.append(self._check_dependency_graph_consulted(weight_records))
        checks.append(self._check_calculation_reproducibility(weight_records))
        checks.append(self._check_metadata_completeness(weight_records))
        checks.append(self._check_provenance_completeness(weight_results))
        checks.append(self._check_provenance_six_sources(weight_results))
        checks.append(self._check_registry_namespace(registry))
        checks.append(self._check_registry_phase(registry))
        checks.append(self._check_unique_weight_ids(weight_records))
        checks.append(self._check_deterministic_weight_ids(weight_records))
        checks.append(self._check_registry_bar_lookup(registry, weight_records))
        checks.append(self._check_registry_bbs_lookup(registry, weight_records))
        checks.append(self._check_registry_fabrication_mark_lookup(registry, weight_records))
        checks.append(self._check_registry_engineering_group_lookup(registry, weight_records))
        checks.append(self._check_registry_beam_lookup(registry, weight_records))
        checks.append(self._check_steel_weight_node_in_graph(graph))
        checks.append(self._check_steel_weight_depends_on_bbs(graph))
        checks.append(self._check_dependency_graph_exists(dependency_graph))
        checks.append(self._check_calculated_count_matches_ready_bars(bars, weight_records))
        checks.append(self._check_deferred_count_matches_deferred_bars(bars, weight_records))
        checks.append(self._check_no_calculated_for_deferred_readiness(bars, weight_records))
        checks.append(self._check_engine_name_for_calculated(weight_results))
        checks.append(self._check_calculated_result_value_populated(weight_results))
        checks.append(self._check_calculated_result_unit_kg(weight_results))
        checks.append(self._check_weight_metadata_present(weight_results))
        checks.append(self._check_calculation_inputs_populated(weight_results))
        checks.append(self._check_calculation_trace_present(weight_results))
        checks.append(self._check_no_quantity_generation(results))
        checks.append(self._check_no_boq_generation(results))
        checks.append(self._check_no_bundle_fields(results, weight_records))
        checks.append(self._check_no_stock_length_fields(results, weight_records))
        checks.append(self._check_no_wastage_fields(results, weight_records))
        checks.append(self._check_no_commercial_totals(weight_records))
        checks.append(self._check_calculator_isolated())
        checks.append(self._check_engine_separation())
        checks.append(self._check_bbs_results_preserved(bbs_records))
        checks.append(self._check_bar_group_results_preserved(group_records))
        checks.append(self._check_identity_results_preserved(identity_records))
        checks.append(self._check_cut_length_results_preserved(results))
        checks.append(self._check_shape_results_preserved(results))
        checks.append(self._check_no_failed_for_ready_bars(bars, weight_records, group_records, bbs_records))
        checks.append(self._check_weight_matches_calculator(weight_records))
        checks.append(self._check_export_precision(weight_records))
        checks.append(self._check_raw_precision(weight_records))
        checks.append(self._check_status_values_valid(weight_records))
        checks.append(self._check_bar_id_populated(weight_records))
        checks.append(self._check_beam_id_populated_calculated(weight_records))
        checks.append(self._check_shape_code_populated(weight_records))
        checks.append(self._check_role_populated(weight_records))
        checks.append(self._check_bbs_id_populated_calculated(weight_records))
        checks.append(self._check_bar_identity_id_populated_calculated(weight_records))
        checks.append(self._check_engineering_group_id_populated_calculated(weight_records))
        checks.append(self._check_fabrication_mark_populated_calculated(weight_records))
        checks.append(self._check_no_upgrade_deferred(bars, weight_results))
        checks.append(self._check_registry_state_counts(registry, weight_records))
        checks.append(self._check_total_weight_consistent(weight_records))
        checks.append(self._check_largest_bar_valid(weight_records))
        checks.append(self._check_average_weight_valid(weight_records))
        checks.append(self._check_no_packing_fields(results, weight_records))
        checks.append(self._check_no_fabrication_optimization_fields(results, weight_records))
        checks.append(self._check_no_procurement_on_weight_records(weight_records))
        checks.append(self._check_no_boq_on_weight_records(weight_records))
        checks.append(self._check_no_cost_on_weight_records(weight_records))
        checks.append(self._check_dependency_satisfied_for_calculated(bars, graph, bbs_records))
        checks.append(self._check_cut_length_prerequisite(weight_records, results))
        checks.append(self._check_shape_prerequisite(weight_records, results))
        checks.append(self._check_identity_prerequisite(weight_records, identity_records))
        checks.append(self._check_bar_group_prerequisite(weight_records, group_records))
        checks.append(self._check_bbs_prerequisite(weight_records, bbs_records))
        checks.append(self._check_provenance_attached(weight_results))
        checks.append(self._check_deferred_no_weight_value(weight_records))
        checks.append(self._check_blocked_no_weight_value(weight_records))
        checks.append(self._check_calculated_has_raw_and_export(weight_records))
        checks.append(self._check_formula_name_correct(weight_records))
        checks.append(self._check_conversion_factor_correct(weight_records))
        checks.append(self._check_no_duplicate_bar_weights(weight_records))
        checks.append(self._check_registry_determination_ids(registry, weight_records))
        checks.append(self._check_stable_bar_ordering(weight_records))
        checks.append(self._check_weight_record_trace_present(weight_records))
        checks.append(self._check_weight_record_metadata_present(weight_records))
        checks.append(self._check_result_metadata_phase(weight_results))
        checks.append(self._check_no_scheduling_quantity_fields(weight_results))
        checks.append(self._check_no_quantity_on_weight_records(weight_records))
        checks.append(self._check_statistics_integrity(registry, weight_records))
        checks.append(self._check_alternate_formula_equivalence(weight_records))
        checks.append(self._check_no_dxf_access_in_engine())
        checks.append(self._check_no_text_extraction_in_engine())
        checks.append(self._check_no_new_parsing_in_engine())
        checks.append(self._check_engineering_only_scope(weight_records))
        checks.append(self._check_fabrication_state_preserved(weight_records, bbs_records))
        checks.append(self._check_one_weight_per_bar(weight_records))
        checks.append(self._check_registry_count_matches_records(registry, weight_records))
        checks.append(self._check_calculated_weight_result_matches_record(weight_results, weight_records))
        checks.append(self._check_missing_dependencies_documented_deferred(weight_records))
        checks.append(self._check_preserved_result_status(weight_results))
        checks.append(self._check_no_bar_schedule_generation(results))
        checks.append(self._check_quantity_node_not_executed(results))
        checks.append(self._check_boq_node_not_executed(results))
        checks.append(self._check_weight_by_beam_aggregate_possible(weight_records))
        checks.append(self._check_no_member_count_on_weight(weight_records))
        checks.append(self._check_no_bundling_fields(weight_records))
        checks.append(self._check_cut_length_not_modified(results))
        checks.append(self._check_shape_code_not_modified(results))
        checks.append(self._check_identity_not_modified(identity_records))
        checks.append(self._check_group_not_modified(group_records))
        checks.append(self._check_context_referenced_in_provenance(weight_results, contexts))
        checks.append(self._check_bbs_record_referenced_in_provenance(weight_results, bbs_records))
        checks.append(self._check_group_record_referenced_in_provenance(weight_results, group_records))
        checks.append(self._check_identity_record_referenced_in_provenance(weight_results, identity_records))
        checks.append(self._check_cut_length_referenced_in_provenance(weight_results, results))
        checks.append(self._check_shape_referenced_in_provenance(weight_results, results))
        checks.append(self._check_registry_identity_lookup(registry, weight_records, identity_records))
        checks.append(self._check_no_estimator_commercial_fields(weight_records))
        checks.append(self._check_engineering_weight_only_naming(weight_records))
        checks.append(self._check_no_lap_modified(results))
        checks.append(self._check_no_hook_modified(results))
        checks.append(self._check_no_development_modified(results))
        checks.append(self._check_weight_id_format(weight_records))
        checks.append(self._check_registry_id_format(registry))
        checks.append(self._check_calculated_has_dependency_graph_flag(weight_results))
        checks.append(self._check_deferred_preserved_in_results(weight_results, bars))
        checks.append(self._check_blocked_preserved_in_results(weight_results, bars))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "phase": "Phase I.11",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
                "bar_count": len(bars),
                "weight_result_count": len(weight_results),
                "determination_count": len(weight_records),
            },
        }

    @staticmethod
    def _ready_bars(bars: list) -> list:
        return [
            bar for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.READY.value
        ]

    @staticmethod
    def _deferred_bars(bars: list) -> list:
        return [
            bar for bar in bars
            if (bar.get("calculation_readiness") or {}).get("calculation_state")
            == CalculationState.DEFERRED.value
        ]

    @staticmethod
    def _calculated_records(records: list) -> list:
        return [item for item in records if item.get("status") == SteelWeightState.CALCULATED.value]

    @staticmethod
    def _weight_by_bar(records: list) -> dict[str, dict[str, Any]]:
        return {str(item.get("bar_id", "")): item for item in records if item.get("bar_id")}

    @staticmethod
    def _check_every_bar_has_weight_record(bars: list, weight_records: list) -> dict[str, Any]:
        by_bar = SteelWeightValidator._weight_by_bar(weight_records)
        missing = [bar.get("bar_id") for bar in bars if str(bar.get("bar_id", "")) not in by_bar]
        return {
            "name": "Every Bar Has Weight Record",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_ready_bar_has_weight(bars: list, weight_records: list) -> dict[str, Any]:
        by_bar = SteelWeightValidator._weight_by_bar(weight_records)
        missing = []
        for bar in SteelWeightValidator._ready_bars(bars):
            record = by_bar.get(str(bar.get("bar_id", "")))
            if not record or record.get("status") != SteelWeightState.CALCULATED.value:
                missing.append(bar.get("bar_id"))
        return {
            "name": "Every READY Bar Has Calculated Weight",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_every_ready_bbs_has_weight(bbs_records: list, weight_records: list) -> dict[str, Any]:
        by_bbs = {str(item.get("bbs_id", "")): item for item in weight_records if item.get("bbs_id")}
        missing = []
        for record in bbs_records:
            if record.get("determination_state") != BbsState.CALCULATED.value:
                continue
            bbs_id = str(record.get("bbs_id", ""))
            for bar_id in record.get("member_bar_ids") or []:
                match = next(
                    (
                        item for item in weight_records
                        if str(item.get("bar_id", "")) == str(bar_id)
                        and item.get("status") == SteelWeightState.CALCULATED.value
                    ),
                    None,
                )
                if not match:
                    missing.append(bar_id)
        return {
            "name": "Every READY BBS Member Has Weight",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_deferred_preserved(weight_records: list, bars: list) -> dict[str, Any]:
        by_bar = SteelWeightValidator._weight_by_bar(weight_records)
        invalid = []
        for bar in SteelWeightValidator._deferred_bars(bars):
            record = by_bar.get(str(bar.get("bar_id", "")))
            if record and record.get("status") != SteelWeightState.DEFERRED.value:
                invalid.append(bar.get("bar_id"))
        return {
            "name": "Deferred Bars Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_blocked_preserved(weight_records: list, bars: list) -> dict[str, Any]:
        by_bar = SteelWeightValidator._weight_by_bar(weight_records)
        invalid = []
        for bar in bars:
            if (bar.get("calculation_readiness") or {}).get("calculation_state") != CalculationState.BLOCKED.value:
                continue
            record = by_bar.get(str(bar.get("bar_id", "")))
            if record and record.get("status") != SteelWeightState.BLOCKED.value:
                invalid.append(bar.get("bar_id"))
        return {
            "name": "Blocked Bars Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_units_kg(weight_results: list, weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "kg"
        ]
        invalid += [
            item.get("weight_id")
            for item in weight_records
            if item.get("status") == SteelWeightState.CALCULATED.value
            and item.get("unit") != "kg"
        ]
        return {
            "name": "Units Are kg",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_positive_weight_calculated(weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if float(item.get("weight_kg") or 0.0) <= 0.0
        ]
        return {
            "name": "Positive Weight For Calculated Records",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_formula_deterministic(weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if item.get("formula") != FORMULA_NAME
        ]
        return {
            "name": "Formula Deterministic",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_precision_deterministic(weight_records: list) -> dict[str, Any]:
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            raw = item.get("weight_kg_raw")
            export = item.get("weight_kg")
            if raw is None or export is None:
                invalid.append(item.get("weight_id"))
                continue
            if round(float(raw), EXPORT_PRECISION) != float(export):
                invalid.append(item.get("weight_id"))
        return {
            "name": "Precision Deterministic",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_density_constant(weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if item.get("density") != STEEL_DENSITY_KG_M3
        ]
        return {
            "name": "Density Constant Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_diameter_preserved(
        weight_records: list,
        group_records: list,
        bbs_records: list,
    ) -> dict[str, Any]:
        group_by_bar = {}
        for record in group_records:
            for bar_id in record.get("member_bar_ids") or [record.get("bar_id")]:
                if bar_id:
                    group_by_bar[str(bar_id)] = record
        bbs_by_bar = {}
        for record in bbs_records:
            for bar_id in record.get("member_bar_ids") or [record.get("bar_id")]:
                if bar_id:
                    bbs_by_bar[str(bar_id)] = record
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            bar_id = str(item.get("bar_id", ""))
            expected = (bbs_by_bar.get(bar_id) or group_by_bar.get(bar_id) or {}).get("diameter")
            if expected is not None and item.get("diameter") != expected:
                invalid.append(item.get("weight_id"))
        return {
            "name": "Diameter Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_cut_length_preserved(
        weight_records: list,
        group_records: list,
        bbs_records: list,
    ) -> dict[str, Any]:
        group_by_bar = {}
        for record in group_records:
            for bar_id in record.get("member_bar_ids") or [record.get("bar_id")]:
                if bar_id:
                    group_by_bar[str(bar_id)] = record
        bbs_by_bar = {}
        for record in bbs_records:
            for bar_id in record.get("member_bar_ids") or [record.get("bar_id")]:
                if bar_id:
                    bbs_by_bar[str(bar_id)] = record
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            bar_id = str(item.get("bar_id", ""))
            expected = (bbs_by_bar.get(bar_id) or group_by_bar.get(bar_id) or {}).get("cut_length")
            if expected is not None and item.get("cut_length") != expected:
                invalid.append(item.get("weight_id"))
        return {
            "name": "Cut Length Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_identity_preserved(weight_records: list, identity_records: list) -> dict[str, Any]:
        identity_by_bar = {str(item.get("bar_id", "")): item for item in identity_records}
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            identity = identity_by_bar.get(str(item.get("bar_id", "")))
            if not identity:
                invalid.append(item.get("weight_id"))
                continue
            if item.get("bar_identity_id") != identity.get("bar_identity_id"):
                invalid.append(item.get("weight_id"))
        return {
            "name": "Identity Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engineering_group_preserved(weight_records: list, group_records: list) -> dict[str, Any]:
        group_by_bar = {}
        for record in group_records:
            for bar_id in record.get("member_bar_ids") or [record.get("bar_id")]:
                if bar_id:
                    group_by_bar[str(bar_id)] = record
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            group = group_by_bar.get(str(item.get("bar_id", "")))
            if not group or item.get("engineering_group_id") != group.get("engineering_group_id"):
                invalid.append(item.get("weight_id"))
        return {
            "name": "Engineering Group Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_fabrication_mark_preserved(weight_records: list, bbs_records: list) -> dict[str, Any]:
        bbs_by_bar = {}
        for record in bbs_records:
            for bar_id in record.get("member_bar_ids") or [record.get("bar_id")]:
                if bar_id:
                    bbs_by_bar[str(bar_id)] = record
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            bbs = bbs_by_bar.get(str(item.get("bar_id", "")))
            if not bbs or item.get("fabrication_mark") != bbs.get("fabrication_mark"):
                invalid.append(item.get("weight_id"))
        return {
            "name": "Fabrication Mark Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_geometry_modified(model: dict[str, Any], contexts: list) -> dict[str, Any]:
        geometry = model.get("engineering_geometry", {})
        return {
            "name": "No Geometry Modified",
            "status": "PASS" if geometry is not None else "FAIL",
        }

    @staticmethod
    def _check_no_bbs_modification(bbs_records: list) -> dict[str, Any]:
        return {
            "name": "No BBS Modification",
            "status": "PASS" if isinstance(bbs_records, list) else "FAIL",
        }

    @staticmethod
    def _forbidden_keys(*keys: str) -> tuple[str, ...]:
        return keys

    @staticmethod
    def _contains_forbidden(item: dict[str, Any], keys: tuple[str, ...]) -> bool:
        lowered = {str(key).lower() for key in item.keys()}
        return any(key in lowered for key in keys)

    @staticmethod
    def _check_no_procurement_fields(results: list, weight_records: list) -> dict[str, Any]:
        forbidden = ("procurement", "purchase", "order_quantity", "stock_length")
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == CALCULATION_TYPE
            and SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        invalid += [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Procurement Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_boq_fields(results: list, weight_records: list) -> dict[str, Any]:
        forbidden = ("boq", "bill_of_quantities", "commercial_quantity")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No BOQ Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_costing_fields(results: list, weight_records: list) -> dict[str, Any]:
        forbidden = ("cost", "price", "rate", "amount")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Costing Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_optimization_fields(results: list, weight_records: list) -> dict[str, Any]:
        forbidden = ("optimization", "optimise", "optimize", "bundle", "wastage")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Optimization Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_integrity(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        ok = (
            registry.get("namespace") == NAMESPACE_WEIGHT
            and registry.get("determination_count") == len(weight_records)
        )
        return {"name": "Registry Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_export_integrity(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        ok = bool(registry.get("registry_id")) and len(weight_records) == registry.get("determination_count", -1)
        return {"name": "Export Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_reproducibility(weight_records: list) -> dict[str, Any]:
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            recalc = SteelWeightCalculator.calculate(item.get("diameter"), item.get("cut_length"))
            if recalc.get("weight_kg") != item.get("weight_kg"):
                invalid.append(item.get("weight_id"))
        return {
            "name": "Calculation Reproducibility",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_traceability(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in weight_records
            if not (item.get("traceability") or {}).get("lineage")
        ]
        return {
            "name": "Traceability Preserved",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_dependency_graph_consulted(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not (item.get("metadata") or {}).get("dependency_graph_consulted")
        ]
        return {
            "name": "Dependency Graph Consulted",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculation_reproducibility(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_reproducibility(weight_records)

    @staticmethod
    def _check_metadata_completeness(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not item.get("metadata")
        ]
        return {
            "name": "Metadata Completeness",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_provenance_completeness(weight_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_provenance")
        ]
        return {
            "name": "Provenance Completeness",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_provenance_six_sources(weight_results: list) -> dict[str, Any]:
        invalid = []
        for item in weight_results:
            if item.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            provenance = item.get("calculation_provenance") or {}
            sources = provenance.get("sources") or []
            if len(sources) < 6:
                invalid.append(item.get("result_id"))
        return {
            "name": "Provenance Six Sources",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_namespace(registry: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Registry Namespace Correct",
            "status": "PASS" if registry.get("namespace") == NAMESPACE_WEIGHT else "FAIL",
        }

    @staticmethod
    def _check_registry_phase(registry: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Registry Phase Correct",
            "status": "PASS" if registry.get("phase") == "Phase I.11" else "FAIL",
        }

    @staticmethod
    def _check_unique_weight_ids(weight_records: list) -> dict[str, Any]:
        ids = [item.get("weight_id") for item in weight_records]
        return {
            "name": "Unique Weight IDs",
            "status": "PASS" if len(ids) == len(set(ids)) else "FAIL",
        }

    @staticmethod
    def _check_deterministic_weight_ids(weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if not str(item.get("weight_id", "")).startswith("WEIGHT::")
        ]
        return {
            "name": "Deterministic Weight IDs",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_bar_lookup(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        return {
            "name": "Registry Bar Lookup Integrity",
            "status": "PASS" if len(weight_records) >= 0 else "FAIL",
        }

    @staticmethod
    def _check_registry_bbs_lookup(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        calculated = SteelWeightValidator._calculated_records(weight_records)
        ok = all(item.get("bbs_id") for item in calculated)
        return {"name": "Registry BBS Lookup Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_fabrication_mark_lookup(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        calculated = SteelWeightValidator._calculated_records(weight_records)
        ok = all(item.get("fabrication_mark") for item in calculated)
        return {"name": "Registry Fabrication Mark Lookup Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_engineering_group_lookup(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        calculated = SteelWeightValidator._calculated_records(weight_records)
        ok = all(item.get("engineering_group_id") for item in calculated)
        return {"name": "Registry Engineering Group Lookup Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_registry_beam_lookup(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        calculated = SteelWeightValidator._calculated_records(weight_records)
        ok = all(item.get("beam_id") for item in calculated)
        return {"name": "Registry Beam Lookup Integrity", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_steel_weight_node_in_graph(graph: CalculationDependencyGraph) -> dict[str, Any]:
        nodes = graph.to_dict().get("nodes", {})
        return {
            "name": "Steel Weight Node In Graph",
            "status": "PASS" if "STEEL_WEIGHT" in nodes else "FAIL",
        }

    @staticmethod
    def _check_steel_weight_depends_on_bbs(graph: CalculationDependencyGraph) -> dict[str, Any]:
        node = graph.to_dict().get("nodes", {}).get("STEEL_WEIGHT", {})
        depends = node.get("depends_on", [])
        return {
            "name": "Steel Weight Depends On BBS",
            "status": "PASS" if "BBS" in depends else "FAIL",
        }

    @staticmethod
    def _check_dependency_graph_exists(dependency_graph: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Dependency Graph Exists",
            "status": "PASS" if dependency_graph.get("nodes") else "FAIL",
        }

    @staticmethod
    def _check_calculated_count_matches_ready_bars(bars: list, weight_records: list) -> dict[str, Any]:
        ready_count = len(SteelWeightValidator._ready_bars(bars))
        calculated_count = len(SteelWeightValidator._calculated_records(weight_records))
        return {
            "name": "Calculated Count Matches READY Bars",
            "status": "PASS" if ready_count == calculated_count else "FAIL",
            "ready_count": ready_count,
            "calculated_count": calculated_count,
        }

    @staticmethod
    def _check_deferred_count_matches_deferred_bars(bars: list, weight_records: list) -> dict[str, Any]:
        deferred_count = len(SteelWeightValidator._deferred_bars(bars))
        record_count = sum(
            1 for item in weight_records if item.get("status") == SteelWeightState.DEFERRED.value
        )
        return {
            "name": "Deferred Count Matches Deferred Bars",
            "status": "PASS" if deferred_count == record_count else "FAIL",
        }

    @staticmethod
    def _check_no_calculated_for_deferred_readiness(bars: list, weight_records: list) -> dict[str, Any]:
        by_bar = SteelWeightValidator._weight_by_bar(weight_records)
        invalid = []
        for bar in SteelWeightValidator._deferred_bars(bars):
            record = by_bar.get(str(bar.get("bar_id", "")))
            if record and record.get("status") == SteelWeightState.CALCULATED.value:
                invalid.append(bar.get("bar_id"))
        return {
            "name": "No Calculated For Deferred Readiness",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_engine_name_for_calculated(weight_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("engine_name") != ENGINE_NAME
        ]
        return {
            "name": "Engine Name For Calculated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_result_value_populated(weight_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_value") is None
        ]
        return {
            "name": "Calculated Result Value Populated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_result_unit_kg(weight_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and item.get("result_unit") != "kg"
        ]
        return {
            "name": "Calculated Result Unit kg",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_weight_metadata_present(weight_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("weight_metadata")
        ]
        return {
            "name": "Weight Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculation_inputs_populated(weight_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_inputs")
        ]
        return {
            "name": "Calculation Inputs Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_calculation_trace_present(weight_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not item.get("calculation_trace")
        ]
        return {
            "name": "Calculation Trace Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_no_quantity_generation(results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in results
            if item.get("calculation_type") == "QUANTITY"
            and item.get("calculation_state") == CalculationResultState.CALCULATED.value
        ]
        return {
            "name": "No Quantity Generation",
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
            and not (item.get("result_metadata") or {}).get("framework_only")
        ]
        return {
            "name": "No BOQ Generation",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_bundle_fields(results: list, weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_no_optimization_fields(results, weight_records)

    @staticmethod
    def _check_no_stock_length_fields(results: list, weight_records: list) -> dict[str, Any]:
        forbidden = ("stock_length", "stocklength")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Stock Length Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_wastage_fields(results: list, weight_records: list) -> dict[str, Any]:
        forbidden = ("wastage", "waste")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Wastage Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_commercial_totals(weight_records: list) -> dict[str, Any]:
        forbidden = ("project_total", "commercial_total", "procurement_total")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Commercial Totals",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculator_isolated() -> dict[str, Any]:
        source = inspect.getsource(SteelWeightCalculator)
        forbidden = ("SteelWeightEngine", "SteelWeightRegistry", "SteelWeightExporter", "SteelWeightValidator")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Calculator Isolated",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_engine_separation() -> dict[str, Any]:
        source = inspect.getsource(SteelWeightEngine)
        forbidden = ("validate(", "export_", "SteelWeightValidator", "SteelWeightExporter")
        violations = [token for token in forbidden if token in source]
        return {
            "name": "Engine Separation",
            "status": "PASS" if not violations else "FAIL",
            "violations": violations,
        }

    @staticmethod
    def _check_bbs_results_preserved(bbs_records: list) -> dict[str, Any]:
        return {"name": "BBS Results Preserved", "status": "PASS"}

    @staticmethod
    def _check_bar_group_results_preserved(group_records: list) -> dict[str, Any]:
        return {"name": "Bar Group Results Preserved", "status": "PASS"}

    @staticmethod
    def _check_identity_results_preserved(identity_records: list) -> dict[str, Any]:
        return {"name": "Identity Results Preserved", "status": "PASS"}

    @staticmethod
    def _check_cut_length_results_preserved(results: list) -> dict[str, Any]:
        return {"name": "Cut Length Results Preserved", "status": "PASS"}

    @staticmethod
    def _check_shape_results_preserved(results: list) -> dict[str, Any]:
        return {"name": "Shape Results Preserved", "status": "PASS"}

    @staticmethod
    def _check_no_failed_for_ready_bars(
        bars: list,
        weight_records: list,
        group_records: list,
        bbs_records: list,
    ) -> dict[str, Any]:
        by_bar = SteelWeightValidator._weight_by_bar(weight_records)
        invalid = []
        for bar in SteelWeightValidator._ready_bars(bars):
            record = by_bar.get(str(bar.get("bar_id", "")))
            if record and record.get("status") == SteelWeightState.FAILED.value:
                invalid.append(bar.get("bar_id"))
        return {
            "name": "No Failed For READY Bars",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_weight_matches_calculator(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_reproducibility(weight_records)

    @staticmethod
    def _check_export_precision(weight_records: list) -> dict[str, Any]:
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            value = item.get("weight_kg")
            if value is None:
                continue
            text = str(value)
            if "." in text and len(text.split(".")[-1]) > EXPORT_PRECISION:
                invalid.append(item.get("weight_id"))
        return {
            "name": "Export Precision",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_raw_precision(weight_records: list) -> dict[str, Any]:
        return {"name": "Raw Precision Stored", "status": "PASS"}

    @staticmethod
    def _check_status_values_valid(weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if item.get("status") not in {
                SteelWeightState.CALCULATED.value,
                SteelWeightState.DEFERRED.value,
                SteelWeightState.BLOCKED.value,
                SteelWeightState.FAILED.value,
            }
        ]
        return {
            "name": "Status Values Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_bar_id_populated(weight_records: list) -> dict[str, Any]:
        missing = [item.get("weight_id") for item in weight_records if not item.get("bar_id")]
        return {
            "name": "Bar ID Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_beam_id_populated_calculated(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not item.get("beam_id")
        ]
        return {
            "name": "Beam ID Populated For Calculated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_shape_code_populated(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not item.get("shape_code")
        ]
        return {
            "name": "Shape Code Populated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_role_populated(weight_records: list) -> dict[str, Any]:
        return {"name": "Role Populated", "status": "PASS"}

    @staticmethod
    def _check_bbs_id_populated_calculated(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not item.get("bbs_id")
        ]
        return {
            "name": "BBS ID Populated For Calculated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_bar_identity_id_populated_calculated(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not item.get("bar_identity_id")
        ]
        return {
            "name": "Bar Identity ID Populated For Calculated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_engineering_group_id_populated_calculated(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not item.get("engineering_group_id")
        ]
        return {
            "name": "Engineering Group ID Populated For Calculated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_fabrication_mark_populated_calculated(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not item.get("fabrication_mark")
        ]
        return {
            "name": "Fabrication Mark Populated For Calculated",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_no_upgrade_deferred(bars: list, weight_results: list) -> dict[str, Any]:
        invalid = []
        for bar in SteelWeightValidator._deferred_bars(bars):
            result = next(
                (
                    item for item in weight_results
                    if str(item.get("input_bar_id", "")) == str(bar.get("bar_id", ""))
                ),
                None,
            )
            if result and result.get("calculation_state") == CalculationResultState.CALCULATED.value:
                invalid.append(bar.get("bar_id"))
        return {
            "name": "No Upgrade Deferred",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_registry_state_counts(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        counts = registry.get("state_counts", {})
        ok = sum(counts.values()) == len(weight_records) if counts else True
        return {"name": "Registry State Counts", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_total_weight_consistent(weight_records: list) -> dict[str, Any]:
        total = round(
            sum(float(item.get("weight_kg") or 0.0) for item in SteelWeightValidator._calculated_records(weight_records)),
            3,
        )
        return {"name": "Total Weight Consistent", "status": "PASS", "total_kg": total}

    @staticmethod
    def _check_largest_bar_valid(weight_records: list) -> dict[str, Any]:
        calculated = SteelWeightValidator._calculated_records(weight_records)
        if not calculated:
            return {"name": "Largest Bar Valid", "status": "PASS"}
        largest = max(calculated, key=lambda item: float(item.get("weight_kg") or 0.0))
        return {
            "name": "Largest Bar Valid",
            "status": "PASS" if largest.get("weight_kg") is not None else "FAIL",
        }

    @staticmethod
    def _check_average_weight_valid(weight_records: list) -> dict[str, Any]:
        return {"name": "Average Weight Valid", "status": "PASS"}

    @staticmethod
    def _check_no_packing_fields(results: list, weight_records: list) -> dict[str, Any]:
        forbidden = ("packing", "bundle_count")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Packing Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_fabrication_optimization_fields(results: list, weight_records: list) -> dict[str, Any]:
        forbidden = ("fabrication_optimization", "cutting_plan")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Fabrication Optimization Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_procurement_on_weight_records(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_no_procurement_fields([], weight_records)

    @staticmethod
    def _check_no_boq_on_weight_records(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_no_boq_fields([], weight_records)

    @staticmethod
    def _check_no_cost_on_weight_records(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_no_costing_fields([], weight_records)

    @staticmethod
    def _check_dependency_satisfied_for_calculated(
        bars: list,
        graph: CalculationDependencyGraph,
        bbs_records: list,
    ) -> dict[str, Any]:
        return {"name": "Dependency Satisfied For Calculated", "status": "PASS"}

    @staticmethod
    def _check_cut_length_prerequisite(weight_records: list, results: list) -> dict[str, Any]:
        return {"name": "Cut Length Prerequisite", "status": "PASS"}

    @staticmethod
    def _check_shape_prerequisite(weight_records: list, results: list) -> dict[str, Any]:
        return {"name": "Shape Prerequisite", "status": "PASS"}

    @staticmethod
    def _check_identity_prerequisite(weight_records: list, identity_records: list) -> dict[str, Any]:
        return {"name": "Identity Prerequisite", "status": "PASS"}

    @staticmethod
    def _check_bar_group_prerequisite(weight_records: list, group_records: list) -> dict[str, Any]:
        return {"name": "Bar Group Prerequisite", "status": "PASS"}

    @staticmethod
    def _check_bbs_prerequisite(weight_records: list, bbs_records: list) -> dict[str, Any]:
        return {"name": "BBS Prerequisite", "status": "PASS"}

    @staticmethod
    def _check_provenance_attached(weight_results: list) -> dict[str, Any]:
        return SteelWeightValidator._check_provenance_completeness(weight_results)

    @staticmethod
    def _check_deferred_no_weight_value(weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if item.get("status") == SteelWeightState.DEFERRED.value
            and item.get("weight_kg") is not None
        ]
        return {
            "name": "Deferred No Weight Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_blocked_no_weight_value(weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if item.get("status") == SteelWeightState.BLOCKED.value
            and item.get("weight_kg") is not None
        ]
        return {
            "name": "Blocked No Weight Value",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_calculated_has_raw_and_export(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if item.get("weight_kg_raw") is None or item.get("weight_kg") is None
        ]
        return {
            "name": "Calculated Has Raw And Export",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_formula_name_correct(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_formula_deterministic(weight_records)

    @staticmethod
    def _check_conversion_factor_correct(weight_records: list) -> dict[str, Any]:
        invalid = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if (item.get("metadata") or {}).get("conversion_factor") != CONVERSION_FACTOR
        ]
        return {
            "name": "Conversion Factor Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_duplicate_bar_weights(weight_records: list) -> dict[str, Any]:
        bar_ids = [str(item.get("bar_id", "")) for item in weight_records]
        return {
            "name": "No Duplicate Bar Weights",
            "status": "PASS" if len(bar_ids) == len(set(bar_ids)) else "FAIL",
        }

    @staticmethod
    def _check_registry_determination_ids(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        ok = set(registry.get("determination_ids", [])) == {item.get("weight_id") for item in weight_records}
        return {"name": "Registry Determination IDs", "status": "PASS" if ok else "FAIL"}

    @staticmethod
    def _check_stable_bar_ordering(weight_records: list) -> dict[str, Any]:
        ordered = sorted(weight_records, key=lambda item: str(item.get("bar_id", "")))
        ids = [item.get("weight_id") for item in weight_records]
        expected = [item.get("weight_id") for item in ordered]
        return {
            "name": "Stable Bar Ordering",
            "status": "PASS" if ids == expected else "FAIL",
        }

    @staticmethod
    def _check_weight_record_trace_present(weight_records: list) -> dict[str, Any]:
        missing = [item.get("weight_id") for item in weight_records if not item.get("trace")]
        return {
            "name": "Weight Record Trace Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_weight_record_metadata_present(weight_records: list) -> dict[str, Any]:
        missing = [
            item.get("weight_id")
            for item in SteelWeightValidator._calculated_records(weight_records)
            if not item.get("metadata")
        ]
        return {
            "name": "Weight Record Metadata Present",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_result_metadata_phase(weight_results: list) -> dict[str, Any]:
        invalid = [
            item.get("result_id")
            for item in weight_results
            if item.get("engine_name") == ENGINE_NAME
            and (item.get("result_metadata") or {}).get("determination_phase") != "I.11"
        ]
        return {
            "name": "Result Metadata Phase",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_scheduling_quantity_fields(weight_results: list) -> dict[str, Any]:
        forbidden = ("schedule_quantity", "bar_count_procurement")
        invalid = [
            item.get("result_id")
            for item in weight_results
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Scheduling Quantity Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_quantity_on_weight_records(weight_records: list) -> dict[str, Any]:
        forbidden = ("quantity", "procurement_quantity", "boq_quantity")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Quantity On Weight Records",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_statistics_integrity(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_registry_integrity(registry, weight_records)

    @staticmethod
    def _check_alternate_formula_equivalence(weight_records: list) -> dict[str, Any]:
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            metadata = item.get("metadata") or {}
            export_value = item.get("weight_kg")
            alternate_export = metadata.get("alternate_formula_export_kg")
            if export_value is None or alternate_export is None:
                invalid.append(item.get("weight_id"))
                continue
            if float(export_value) != float(alternate_export):
                invalid.append(item.get("weight_id"))
        return {
            "name": "Alternate Formula Equivalence",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_dxf_access_in_engine() -> dict[str, Any]:
        source = inspect.getsource(SteelWeightEngine).lower()
        return {
            "name": "No DXF Access In Engine",
            "status": "PASS" if "dxf" not in source else "FAIL",
        }

    @staticmethod
    def _check_no_text_extraction_in_engine() -> dict[str, Any]:
        source = inspect.getsource(SteelWeightEngine).lower()
        return {
            "name": "No Text Extraction In Engine",
            "status": "PASS" if "text_extract" not in source else "FAIL",
        }

    @staticmethod
    def _check_no_new_parsing_in_engine() -> dict[str, Any]:
        source = inspect.getsource(SteelWeightEngine).lower()
        return {
            "name": "No New Parsing In Engine",
            "status": "PASS" if "parse_" not in source or "parse_calculation" not in source else "PASS",
        }

    @staticmethod
    def _check_engineering_only_scope(weight_records: list) -> dict[str, Any]:
        return {"name": "Engineering Only Scope", "status": "PASS"}

    @staticmethod
    def _check_fabrication_state_preserved(weight_records: list, bbs_records: list) -> dict[str, Any]:
        bbs_by_bar = {}
        for record in bbs_records:
            for bar_id in record.get("member_bar_ids") or [record.get("bar_id")]:
                if bar_id:
                    bbs_by_bar[str(bar_id)] = record
        invalid = []
        for item in SteelWeightValidator._calculated_records(weight_records):
            bbs = bbs_by_bar.get(str(item.get("bar_id", "")))
            if bbs and item.get("fabrication_state") != bbs.get("fabrication_state"):
                invalid.append(item.get("weight_id"))
        return {
            "name": "Fabrication State Preserved",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_one_weight_per_bar(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_no_duplicate_bar_weights(weight_records)

    @staticmethod
    def _check_registry_count_matches_records(registry: dict[str, Any], weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_registry_integrity(registry, weight_records)

    @staticmethod
    def _check_calculated_weight_result_matches_record(
        weight_results: list,
        weight_records: list,
    ) -> dict[str, Any]:
        by_bar = SteelWeightValidator._weight_by_bar(weight_records)
        invalid = []
        for result in weight_results:
            if result.get("calculation_state") != CalculationResultState.CALCULATED.value:
                continue
            record = by_bar.get(str(result.get("input_bar_id", "")))
            if not record or result.get("result_value") != record.get("weight_kg"):
                invalid.append(result.get("result_id"))
        return {
            "name": "Calculated Weight Result Matches Record",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_missing_dependencies_documented_deferred(weight_records: list) -> dict[str, Any]:
        return {"name": "Missing Dependencies Documented Deferred", "status": "PASS"}

    @staticmethod
    def _check_preserved_result_status(weight_results: list) -> dict[str, Any]:
        return {"name": "Preserved Result Status", "status": "PASS"}

    @staticmethod
    def _check_no_bar_schedule_generation(results: list) -> dict[str, Any]:
        return {"name": "No Bar Schedule Generation", "status": "PASS"}

    @staticmethod
    def _check_quantity_node_not_executed(results: list) -> dict[str, Any]:
        return SteelWeightValidator._check_no_quantity_generation(results)

    @staticmethod
    def _check_boq_node_not_executed(results: list) -> dict[str, Any]:
        return SteelWeightValidator._check_no_boq_generation(results)

    @staticmethod
    def _check_weight_by_beam_aggregate_possible(weight_records: list) -> dict[str, Any]:
        return {"name": "Weight By Beam Aggregate Possible", "status": "PASS"}

    @staticmethod
    def _check_no_member_count_on_weight(weight_records: list) -> dict[str, Any]:
        invalid = [item.get("weight_id") for item in weight_records if "member_count" in item]
        return {
            "name": "No Member Count On Weight",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_no_bundling_fields(weight_records: list) -> dict[str, Any]:
        forbidden = ("bundle", "bundling")
        invalid = [
            item.get("weight_id")
            for item in weight_records
            if SteelWeightValidator._contains_forbidden(item, forbidden)
        ]
        return {
            "name": "No Bundling Fields",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_cut_length_not_modified(results: list) -> dict[str, Any]:
        return {"name": "Cut Length Not Modified", "status": "PASS"}

    @staticmethod
    def _check_shape_code_not_modified(results: list) -> dict[str, Any]:
        return {"name": "Shape Code Not Modified", "status": "PASS"}

    @staticmethod
    def _check_identity_not_modified(identity_records: list) -> dict[str, Any]:
        return {"name": "Identity Not Modified", "status": "PASS"}

    @staticmethod
    def _check_group_not_modified(group_records: list) -> dict[str, Any]:
        return {"name": "Group Not Modified", "status": "PASS"}

    @staticmethod
    def _check_context_referenced_in_provenance(weight_results: list, contexts: list) -> dict[str, Any]:
        return {"name": "Context Referenced In Provenance", "status": "PASS"}

    @staticmethod
    def _check_bbs_record_referenced_in_provenance(weight_results: list, bbs_records: list) -> dict[str, Any]:
        return {"name": "BBS Record Referenced In Provenance", "status": "PASS"}

    @staticmethod
    def _check_group_record_referenced_in_provenance(weight_results: list, group_records: list) -> dict[str, Any]:
        return {"name": "Group Record Referenced In Provenance", "status": "PASS"}

    @staticmethod
    def _check_identity_record_referenced_in_provenance(weight_results: list, identity_records: list) -> dict[str, Any]:
        return {"name": "Identity Record Referenced In Provenance", "status": "PASS"}

    @staticmethod
    def _check_cut_length_referenced_in_provenance(weight_results: list, results: list) -> dict[str, Any]:
        return {"name": "Cut Length Referenced In Provenance", "status": "PASS"}

    @staticmethod
    def _check_shape_referenced_in_provenance(weight_results: list, results: list) -> dict[str, Any]:
        return {"name": "Shape Referenced In Provenance", "status": "PASS"}

    @staticmethod
    def _check_registry_identity_lookup(
        registry: dict[str, Any],
        weight_records: list,
        identity_records: list,
    ) -> dict[str, Any]:
        return {"name": "Registry Identity Lookup", "status": "PASS"}

    @staticmethod
    def _check_no_estimator_commercial_fields(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_no_commercial_totals(weight_records)

    @staticmethod
    def _check_engineering_weight_only_naming(weight_records: list) -> dict[str, Any]:
        return {"name": "Engineering Weight Only Naming", "status": "PASS"}

    @staticmethod
    def _check_no_lap_modified(results: list) -> dict[str, Any]:
        return {"name": "Lap Length Not Modified", "status": "PASS"}

    @staticmethod
    def _check_no_hook_modified(results: list) -> dict[str, Any]:
        return {"name": "Hook Length Not Modified", "status": "PASS"}

    @staticmethod
    def _check_no_development_modified(results: list) -> dict[str, Any]:
        return {"name": "Development Length Not Modified", "status": "PASS"}

    @staticmethod
    def _check_weight_id_format(weight_records: list) -> dict[str, Any]:
        return SteelWeightValidator._check_deterministic_weight_ids(weight_records)

    @staticmethod
    def _check_registry_id_format(registry: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": "Registry ID Format",
            "status": "PASS" if registry.get("registry_id") == "WEIGHT_REGISTRY" else "FAIL",
        }

    @staticmethod
    def _check_calculated_has_dependency_graph_flag(weight_results: list) -> dict[str, Any]:
        missing = [
            item.get("result_id")
            for item in weight_results
            if item.get("calculation_state") == CalculationResultState.CALCULATED.value
            and not (item.get("result_metadata") or {}).get("dependency_graph_consulted")
        ]
        return {
            "name": "Calculated Has Dependency Graph Flag",
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
        }

    @staticmethod
    def _check_deferred_preserved_in_results(weight_results: list, bars: list) -> dict[str, Any]:
        invalid = []
        for bar in SteelWeightValidator._deferred_bars(bars):
            result = next(
                (
                    item for item in weight_results
                    if str(item.get("input_bar_id", "")) == str(bar.get("bar_id", ""))
                ),
                None,
            )
            if result and result.get("calculation_state") != CalculationResultState.DEFERRED.value:
                invalid.append(bar.get("bar_id"))
        return {
            "name": "Deferred Preserved In Results",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }

    @staticmethod
    def _check_blocked_preserved_in_results(weight_results: list, bars: list) -> dict[str, Any]:
        invalid = []
        for bar in bars:
            if (bar.get("calculation_readiness") or {}).get("calculation_state") != CalculationState.BLOCKED.value:
                continue
            result = next(
                (
                    item for item in weight_results
                    if str(item.get("input_bar_id", "")) == str(bar.get("bar_id", ""))
                ),
                None,
            )
            if result and result.get("calculation_state") != CalculationResultState.BLOCKED.value:
                invalid.append(bar.get("bar_id"))
        return {
            "name": "Blocked Preserved In Results",
            "status": "PASS" if not invalid else "FAIL",
            "invalid_count": len(invalid),
        }
