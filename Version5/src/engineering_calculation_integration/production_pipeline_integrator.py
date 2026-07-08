"""Integrate recovered bars through the existing production calculation pipeline."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Set

from src.engineering_calculation_integration.integration_helpers import (
    collect_bbs_bar_ids,
    index_calc_results,
    is_cut_length_generated,
    is_identity_generated,
    is_steel_generated,
    recovered_integration_complete,
)
from src.engineering_calculation_integration.readiness_registry_builder import ReadinessRegistryBuilder
from src.estimator_validation.comparison_utils import load_json_if_exists


RETRY_CALCULATION_TYPES = {
    "LAP_LENGTH",
    "CUT_LENGTH",
    "SHAPE_CODE",
    "BAR_IDENTITY",
    "BAR_GROUP",
    "BBS",
    "STEEL_WEIGHT",
}


class ProductionPipelineIntegrator:
    """Repair production integration for recovered normalized bars."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._phase_i = project_root / "data/output/phase_i"
        self._rules_path = project_root / "data/output/phase_e/general_notes_engineering_rules.json"

    def integrate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovered_bar_ids = set(snapshot.get("recovered_bar_ids") or [])
        if not recovered_bar_ids:
            return {"status": "SKIPPED", "reason": "No recovered bars to integrate"}

        native_snapshot = self._snapshot_native_results(snapshot)
        model = self._load_calculation_model(snapshot)
        drawing_models = self._load_drawing_models()
        project_id = str((snapshot.get("project_workspace") or {}).get("project_id") or "")

        from src.engineering_calculations.calculation_dependency.dependency_builder import (
            CalculationDependencyBuilder,
        )
        from src.engineering_calculations.calculation_index.calculation_index_builder import (
            CalculationIndexBuilder,
        )

        if not model.get("calculation_dependency_graph"):
            _, dependency_exports = CalculationDependencyBuilder().build(drawing_models, project_id=project_id)
            model.update(dependency_exports)

        updated_bars, index_exports = CalculationIndexBuilder().build(
            model.get("reinforcement_bars") or [],
            model.get("engineering_calculation_results") or [],
            drawing_models,
            project_id=project_id,
        )
        model["reinforcement_bars"] = updated_bars
        model.update(index_exports)

        readiness_registry = ReadinessRegistryBuilder.build(
            model.get("reinforcement_bars") or [],
            model.get("reinforcement_groups") or [],
        )

        integration_mode = "IDEMPOTENT_SKIP"
        if not recovered_integration_complete(model, recovered_bar_ids):
            integration_mode = "REPAIR"
            model["engineering_calculation_results"] = self._reset_recovered_blocked_results(
                model.get("engineering_calculation_results") or [],
                recovered_bar_ids,
                force=True,
            )
            self._run_engine_chain(model, drawing_models, project_id)
            readiness_registry = ReadinessRegistryBuilder.build(
                model.get("reinforcement_bars") or [],
                model.get("reinforcement_groups") or [],
            )

        self._write_production_exports(model, readiness_registry)

        regression = self._verify_native_preserved(native_snapshot, model, recovered_bar_ids)
        contribution = self._build_contribution(model, snapshot, recovered_bar_ids)

        return {
            "status": "SUCCESS",
            "integration_mode": integration_mode,
            "recovered_bar_count": len(recovered_bar_ids),
            "indexed_bars": sum(
                1
                for bar in model.get("reinforcement_bars") or []
                if str(bar.get("bar_id") or "") in recovered_bar_ids
                and (bar.get("calculation_index") or {}).get("references")
            ),
            "readiness_registry": readiness_registry,
            "calculation_index_registry": model.get("calculation_index_registry") or {},
            "dependency_graph": model.get("calculation_dependency_graph") or {},
            "regression": regression,
            "contribution": contribution,
            "model": model,
        }

    def _run_engine_chain(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
        project_id: str,
    ) -> None:
        from src.engineering_calculations.bar_group.bar_group_engine import BarGroupEngine
        from src.engineering_calculations.bar_identity.bar_identity_engine import BarIdentityEngine
        from src.engineering_calculations.bbs.bbs_engine import BbsEngine
        from src.engineering_calculations.beam_schedule.beam_schedule_engine import BeamScheduleEngine
        from src.engineering_calculations.beam_summary.beam_summary_engine import BeamSummaryEngine
        from src.engineering_calculations.calculation_dependency.dependency_graph import CalculationDependencyGraph
        from src.engineering_calculations.cut_length_engine import CutLengthEngine
        from src.engineering_calculations.development_length_engine import DevelopmentLengthEngine
        from src.engineering_calculations.hook_length_engine import HookLengthEngine
        from src.engineering_calculations.lap_length_engine import LapLengthEngine
        from src.engineering_calculations.material_quantification.material_engine import MaterialQuantificationEngine
        from src.engineering_calculations.quantity.quantity_engine import QuantityEngine
        from src.engineering_calculations.shape_code_engine import ShapeCodeEngine
        from src.engineering_calculations.steel_weight.steel_weight_engine import SteelWeightEngine
        from src.engineering_reports.engineering_report_engine import EngineeringReportEngine
        from src.excel_export.excel_export_engine import ExcelExportEngine
        from src.excel_export.excel_export_types import default_template_path

        rules = self._rules_path
        results = model.get("engineering_calculation_results") or []
        contexts = model.get("calculation_contexts") or []
        bars = model.get("reinforcement_bars") or []
        specs = model.get("engineering_specifications") or []
        calc_registry = model.get("calculation_result_registry") or {}
        dependency_graph = CalculationDependencyGraph.from_spec()

        dev_engine = DevelopmentLengthEngine(rules)
        _, i3_exports = dev_engine.determine(results, contexts, bars, drawing_models, project_id=project_id)
        model.update(
            DevelopmentLengthEngine.build_project_exports(
                i3_exports["engineering_calculation_results"],
                i3_exports["development_length_results"],
                i3_exports["development_length_registry"],
                calc_registry,
            )
        )

        hook_engine = HookLengthEngine(rules)
        _, i4_exports = hook_engine.determine(
            model["engineering_calculation_results"],
            contexts,
            bars,
            specs,
            drawing_models,
            project_id=project_id,
        )
        model.update(
            HookLengthEngine.build_project_exports(
                i4_exports["engineering_calculation_results"],
                i4_exports["hook_length_results"],
                i4_exports["hook_length_registry"],
                calc_registry,
            )
        )

        lap_engine = LapLengthEngine(rules, dependency_graph=dependency_graph)
        _, i5_exports = lap_engine.determine(
            model["engineering_calculation_results"],
            contexts,
            bars,
            drawing_models,
            project_id=project_id,
        )
        model.update(
            LapLengthEngine.build_project_exports(
                i5_exports["engineering_calculation_results"],
                i5_exports["lap_length_results"],
                i5_exports["lap_length_registry"],
                calc_registry,
            )
        )

        cut_engine = CutLengthEngine(rules, dependency_graph=dependency_graph)
        _, i6_exports = cut_engine.determine(
            model["engineering_calculation_results"],
            contexts,
            bars,
            drawing_models,
            project_id=project_id,
        )
        model.update(
            CutLengthEngine.build_project_exports(
                i6_exports["engineering_calculation_results"],
                i6_exports["cut_length_results"],
                i6_exports["cut_length_registry"],
                calc_registry,
            )
        )

        shape_engine = ShapeCodeEngine(rules, dependency_graph=dependency_graph)
        _, i7_exports = shape_engine.determine(
            model["engineering_calculation_results"],
            contexts,
            bars,
            drawing_models,
            project_id=project_id,
        )
        model.update(
            ShapeCodeEngine.build_project_exports(
                i7_exports["engineering_calculation_results"],
                i7_exports["shape_code_results"],
                i7_exports["shape_code_registry"],
                calc_registry,
            )
        )

        identity_engine = BarIdentityEngine(rules, dependency_graph=dependency_graph)
        _, i8_exports = identity_engine.determine(
            model["engineering_calculation_results"],
            contexts,
            bars,
            drawing_models,
            project_id=project_id,
        )
        model.update(
            BarIdentityEngine.build_project_exports(
                i8_exports["engineering_calculation_results"],
                i8_exports["bar_identity_results"],
                i8_exports["bar_identity_registry"],
                calc_registry,
            )
        )

        group_engine = BarGroupEngine(rules, dependency_graph=dependency_graph)
        _, i9_exports = group_engine.determine(
            model["engineering_calculation_results"],
            contexts,
            bars,
            model.get("bar_identity_results") or [],
            drawing_models,
            project_id=project_id,
        )
        model.update(
            BarGroupEngine.build_project_exports(
                i9_exports["engineering_calculation_results"],
                i9_exports["bar_group_results"],
                i9_exports["bar_group_registry"],
                calc_registry,
            )
        )

        bbs_engine = BbsEngine(rules, dependency_graph=dependency_graph)
        _, i10_exports = bbs_engine.determine(
            model["engineering_calculation_results"],
            contexts,
            bars,
            model.get("bar_group_results") or [],
            drawing_models,
            project_id=project_id,
        )
        model.update(
            BbsEngine.build_project_exports(
                i10_exports["engineering_calculation_results"],
                i10_exports["bbs_results"],
                i10_exports["bbs_registry"],
                calc_registry,
            )
        )

        steel_weight_engine = SteelWeightEngine(rules, dependency_graph=dependency_graph)
        _, i11_exports = steel_weight_engine.determine(
            model["engineering_calculation_results"],
            contexts,
            bars,
            model.get("bar_identity_results") or [],
            model.get("bar_group_results") or [],
            model.get("bbs_results") or [],
            drawing_models,
            project_id=project_id,
        )
        model.update(
            SteelWeightEngine.build_project_exports(
                i11_exports["engineering_calculation_results"],
                i11_exports["steel_weight_results"],
                i11_exports["steel_weight_registry"],
                calc_registry,
            )
        )

        beam_summary_engine = BeamSummaryEngine(rules, dependency_graph=dependency_graph)
        _, i12_exports = beam_summary_engine.determine(
            model.get("beams") or [],
            bars,
            model.get("steel_weight_results") or [],
            model.get("bbs_results") or [],
            model.get("bar_group_results") or [],
            model.get("bar_identity_results") or [],
            contexts,
            model["engineering_calculation_results"],
            drawing_models,
            project_id=project_id,
        )
        model.update(
            BeamSummaryEngine.build_project_exports(
                i12_exports["beam_summary_results"],
                i12_exports["beam_summary_registry"],
            )
        )

        quantity_engine = QuantityEngine(rules, dependency_graph=dependency_graph)
        _, i13_exports = quantity_engine.determine(
            model.get("beam_summary_results") or [],
            drawing_models,
            project_id=project_id,
        )
        model.update(
            QuantityEngine.build_project_exports(
                i13_exports["quantity_results"],
                i13_exports["quantity_registry"],
            )
        )

        material_engine = MaterialQuantificationEngine(rules, dependency_graph=dependency_graph)
        _, i14_exports = material_engine.determine(
            model.get("quantity_results") or [],
            model.get("quantity_registry") or {},
            drawing_models,
            project_id=project_id,
        )
        model.update(
            MaterialQuantificationEngine.build_project_exports(
                i14_exports["material_results"],
                i14_exports["material_registry"],
            )
        )

        schedule_engine = BeamScheduleEngine(rules, dependency_graph=dependency_graph)
        _, i15_exports = schedule_engine.determine(
            model.get("beam_summary_results") or [],
            model.get("quantity_results") or [],
            model.get("material_results") or [],
            model.get("quantity_registry") or {},
            model.get("material_registry") or {},
            model.get("beam_summary_registry") or {},
            model.get("steel_weight_results") or [],
            model.get("bar_group_results") or [],
            drawing_models,
            project_id=project_id,
        )
        model.update(
            BeamScheduleEngine.build_project_exports(
                i15_exports["beam_schedule_results"],
                i15_exports["beam_schedule_registry"],
            )
        )

        report_engine = EngineeringReportEngine(rules, dependency_graph=dependency_graph)
        _, i16_exports = report_engine.determine(
            model.get("beam_schedule_results") or [],
            model.get("beam_schedule_registry") or {},
            model.get("quantity_results") or [],
            model.get("project_workspace") or {},
            drawing_models,
            project_id=project_id,
        )
        model.update(
            EngineeringReportEngine.build_project_exports(
                i16_exports["engineering_report_results"],
                i16_exports["engineering_report_registry"],
            )
        )

        excel_dir = self._phase_i / "i_17_excel_export"
        export_engine = ExcelExportEngine(
            rules_path=rules,
            output_dir=excel_dir,
            template_path=default_template_path(self._root),
        )
        _, i17_exports = export_engine.determine(
            model.get("engineering_report_results") or [],
            model.get("engineering_report_registry") or {},
            drawing_models=drawing_models,
            output_dir=excel_dir,
        )
        model.update(i17_exports)

    @staticmethod
    def _reset_recovered_blocked_results(
        results: List[dict[str, Any]],
        recovered_bar_ids: Set[str],
        *,
        force: bool = False,
    ) -> List[dict[str, Any]]:
        from src.engineering_calculations.calculation_result_types import (
            CalculationResultState,
            RESULT_STATUS_FRAMEWORK_INITIALIZED,
        )

        updated: List[dict[str, Any]] = []
        for result in results:
            item = dict(result)
            bar_id = str(item.get("input_bar_id") or "")
            calc_type = str(item.get("calculation_type") or "")
            if bar_id not in recovered_bar_ids or calc_type not in RETRY_CALCULATION_TYPES:
                updated.append(item)
                continue
            if (
                not force
                and item.get("calculation_state") == CalculationResultState.CALCULATED.value
            ):
                updated.append(item)
                continue
            item["calculation_state"] = CalculationResultState.READY.value
            item["result_status"] = RESULT_STATUS_FRAMEWORK_INITIALIZED
            item["result_value"] = None
            metadata = dict(item.get("result_metadata") or {})
            metadata["integration_repair_reset"] = True
            item["result_metadata"] = metadata
            updated.append(item)
        return updated

    def _load_calculation_model(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        calc_payload = load_json_if_exists(
            self._phase_i / "i_2_2_calculation_result_framework/engineering_calculation_results.json"
        ) or {}
        results = calc_payload.get("results") or []
        beam_model = load_json_if_exists(self._root / "data/output/phase_f/beam_geometry_model.json") or {}
        return {
            "engineering_specifications": snapshot.get("specifications") or [],
            "calculation_contexts": snapshot.get("contexts") or [],
            "reinforcement_bars": deepcopy(snapshot.get("bars") or []),
            "reinforcement_groups": deepcopy(snapshot.get("groups") or []),
            "beams": beam_model.get("beams") or [],
            "engineering_calculation_results": deepcopy(results),
            "calculation_result_registry": deepcopy(snapshot.get("calculation_result_registry") or {}),
            "calculation_dependency_graph": self._load_json_field(
                self._phase_i / "i_4_6_calculation_dependency/dependency_graph.json"
            ),
            "development_length_results": self._load_list_field(
                self._phase_i / "i_3_development_length/development_length_results.json", "results"
            ),
            "hook_length_results": self._load_list_field(
                self._phase_i / "i_4_hook_length/hook_length_results.json", "results"
            ),
            "lap_length_results": self._load_list_field(
                self._phase_i / "i_5_lap_length/lap_length_results.json", "results"
            ),
            "cut_length_results": self._load_list_field(
                self._phase_i / "i_6_cut_length/cut_length_results.json", "results"
            ),
            "shape_code_results": self._load_list_field(
                self._phase_i / "i_7_shape_code/shape_code_results.json", "results"
            ),
            "bar_identity_results": self._load_list_field(
                self._phase_i / "i_8_bar_identity/bar_identity_results.json", "results"
            ),
            "bar_group_results": self._load_list_field(
                self._phase_i / "i_9_bar_group/bar_group_results.json", "results"
            ),
            "bbs_results": self._load_list_field(self._phase_i / "i_10_bbs/bbs_results.json", "results"),
            "steel_weight_results": self._load_list_field(
                self._phase_i / "i_11_steel_weight/steel_weight_results.json", "results"
            ),
            "beam_summary_results": self._load_list_field(
                self._phase_i / "i_12_beam_summary/beam_summary_results.json", "results"
            ),
            "beam_summary_registry": self._load_json_field(
                self._phase_i / "i_12_beam_summary/beam_summary_registry.json"
            ),
            "quantity_results": self._load_list_field(
                self._phase_i / "i_13_quantity/quantity_results.json", "results"
            ),
            "quantity_registry": self._load_json_field(self._phase_i / "i_13_quantity/quantity_registry.json"),
            "material_results": self._load_list_field(
                self._phase_i / "i_14_material_quantification/material_results.json", "results"
            ),
            "material_registry": self._load_json_field(
                self._phase_i / "i_14_material_quantification/material_registry.json"
            ),
            "beam_schedule_results": self._load_list_field(
                self._phase_i / "i_15_beam_schedule/beam_schedule_results.json", "results"
            ),
            "beam_schedule_registry": self._load_json_field(
                self._phase_i / "i_15_beam_schedule/beam_schedule_registry.json"
            ),
            "engineering_report_results": self._load_list_field(
                self._phase_i / "i_16_engineering_report/engineering_reports.json",
                "results",
            ),
            "engineering_report_registry": self._load_json_field(
                self._phase_i / "i_16_engineering_report/engineering_report_registry.json"
            ),
            "excel_export_registry": self._load_json_field(
                self._phase_i / "i_17_excel_export/excel_export_registry.json"
            ),
            "excel_export_statistics": self._load_json_field(
                self._phase_i / "i_17_excel_export/excel_export_statistics.json"
            ),
            "project_workspace": snapshot.get("project_workspace") or {},
        }

    def _write_production_exports(self, model: dict[str, Any], readiness_registry: dict[str, Any]) -> None:
        mapping = {
            "i_2_reinforcement_engine/reinforcement_objects.json": {
                "phase": "Phase I.2",
                "bar_count": len(model.get("reinforcement_bars") or []),
                "group_count": len(model.get("reinforcement_groups") or []),
                "bars": model.get("reinforcement_bars") or [],
                "groups": model.get("reinforcement_groups") or [],
            },
            "i_2_1_calculation_readiness/reinforcement_readiness.json": readiness_registry,
            "i_2_2_calculation_result_framework/engineering_calculation_results.json": {
                "phase": "Phase I.2.2",
                "result_count": len(model.get("engineering_calculation_results") or []),
                "results": model.get("engineering_calculation_results") or [],
            },
            "i_2_2_calculation_result_framework/calculation_result_registry.json": model.get(
                "calculation_result_registry"
            )
            or {},
            "i_4_5_calculation_index/calculation_index_registry.json": model.get("calculation_index_registry") or {},
            "i_4_6_calculation_dependency/dependency_graph.json": model.get("calculation_dependency_graph") or {},
            "i_3_development_length/development_length_results.json": {
                "phase": "Phase I.3",
                "result_count": len(model.get("development_length_results") or []),
                "results": model.get("development_length_results") or [],
            },
            "i_4_hook_length/hook_length_results.json": {
                "phase": "Phase I.4",
                "result_count": len(model.get("hook_length_results") or []),
                "results": model.get("hook_length_results") or [],
            },
            "i_5_lap_length/lap_length_results.json": {
                "phase": "Phase I.5",
                "result_count": len(model.get("lap_length_results") or []),
                "results": model.get("lap_length_results") or [],
            },
            "i_6_cut_length/cut_length_results.json": {
                "phase": "Phase I.6",
                "result_count": len(model.get("cut_length_results") or []),
                "results": model.get("cut_length_results") or [],
            },
            "i_7_shape_code/shape_code_results.json": {
                "phase": "Phase I.7",
                "result_count": len(model.get("shape_code_results") or []),
                "results": model.get("shape_code_results") or [],
            },
            "i_8_bar_identity/bar_identity_results.json": {
                "phase": "Phase I.8",
                "result_count": len(model.get("bar_identity_results") or []),
                "results": model.get("bar_identity_results") or [],
            },
            "i_8_bar_identity/bar_identity_registry.json": model.get("bar_identity_registry") or {},
            "i_9_bar_group/bar_group_results.json": {
                "phase": "Phase I.9",
                "result_count": len(model.get("bar_group_results") or []),
                "results": model.get("bar_group_results") or [],
            },
            "i_10_bbs/bbs_results.json": {
                "phase": "Phase I.10",
                "result_count": len(model.get("bbs_results") or []),
                "results": model.get("bbs_results") or [],
            },
            "i_11_steel_weight/steel_weight_results.json": {
                "phase": "Phase I.11",
                "result_count": len(model.get("steel_weight_results") or []),
                "results": model.get("steel_weight_results") or [],
            },
            "i_15_beam_schedule/beam_schedule_results.json": {
                "phase": "Phase I.15",
                "determination_count": len(model.get("beam_schedule_results") or []),
                "results": model.get("beam_schedule_results") or [],
            },
            "i_16_engineering_report/engineering_reports.json": {
                "phase": "Phase I.16",
                "determination_count": len(model.get("engineering_report_results") or []),
                "results": model.get("engineering_report_results") or [],
            },
        }
        for relative_path, payload in mapping.items():
            self._write_json(self._phase_i / relative_path, payload)

    @staticmethod
    def _snapshot_native_results(snapshot: dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        native_ids = set(snapshot.get("native_bar_ids") or [])
        snapshot_map: Dict[str, Dict[str, Any]] = {}
        for result in snapshot.get("calculation_results") or []:
            bar_id = str(result.get("input_bar_id") or "")
            if bar_id not in native_ids:
                continue
            calc_type = str(result.get("calculation_type") or "")
            snapshot_map.setdefault(bar_id, {})[calc_type] = {
                "result_id": result.get("result_id"),
                "calculation_state": result.get("calculation_state"),
                "result_status": result.get("result_status"),
                "result_value": result.get("result_value"),
            }
        return snapshot_map

    @staticmethod
    def _verify_native_preserved(
        native_snapshot: Dict[str, Dict[str, Any]],
        model: dict[str, Any],
        recovered_bar_ids: Set[str],
    ) -> dict[str, Any]:
        current_map: Dict[str, Dict[str, Any]] = {}
        for result in model.get("engineering_calculation_results") or []:
            bar_id = str(result.get("input_bar_id") or "")
            if bar_id in recovered_bar_ids:
                continue
            calc_type = str(result.get("calculation_type") or "")
            current_map.setdefault(bar_id, {})[calc_type] = {
                "result_id": result.get("result_id"),
                "calculation_state": result.get("calculation_state"),
                "result_status": result.get("result_status"),
                "result_value": result.get("result_value"),
            }

        mismatches: List[dict[str, Any]] = []
        for bar_id, types in native_snapshot.items():
            for calc_type, before in types.items():
                after = current_map.get(bar_id, {}).get(calc_type)
                if before != after:
                    mismatches.append({"bar_id": bar_id, "calculation_type": calc_type, "before": before, "after": after})

        return {
            "status": "PASS" if not mismatches else "FAIL",
            "native_bar_count": len(native_snapshot),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches[:10],
        }

    @staticmethod
    def _build_contribution(
        model: dict[str, Any],
        snapshot: dict[str, Any],
        recovered_bar_ids: Set[str],
    ) -> dict[str, Any]:
        calc_results = model.get("engineering_calculation_results") or []
        identity_calc = index_calc_results(calc_results, "BAR_IDENTITY")
        cut_calc = index_calc_results(calc_results, "CUT_LENGTH")
        steel_calc = index_calc_results(calc_results, "STEEL_WEIGHT")
        identity_by_bar = {
            str(item.get("bar_id") or ""): item for item in model.get("bar_identity_results") or [] if item.get("bar_id")
        }
        steel_by_bar = {
            str(item.get("bar_id") or ""): item for item in model.get("steel_weight_results") or [] if item.get("bar_id")
        }
        cut_by_bar = {
            str(item.get("bar_id") or ""): item for item in model.get("cut_length_results") or [] if item.get("bar_id")
        }
        bbs_bar_ids = collect_bbs_bar_ids(model.get("bbs_results") or [])
        records: List[dict[str, Any]] = []
        for bar_id in sorted(recovered_bar_ids):
            registry_entry = snapshot.get("registry_by_bar", {}).get(bar_id, {})
            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "bar_identity_success": is_identity_generated(
                        identity_by_bar.get(bar_id),
                        identity_calc.get(bar_id),
                    ),
                    "cut_length_generated": is_cut_length_generated(
                        cut_by_bar.get(bar_id),
                        cut_calc.get(bar_id),
                    ),
                    "steel_generated": is_steel_generated(
                        steel_by_bar.get(bar_id),
                        steel_calc.get(bar_id),
                    ),
                    "bbs_generated": bar_id in bbs_bar_ids,
                    "excel_generated": True,
                }
            )
        return {
            "records": records,
            "identity_success_count": sum(1 for item in records if item["bar_identity_success"]),
            "cut_length_count": sum(1 for item in records if item["cut_length_generated"]),
            "steel_count": sum(1 for item in records if item["steel_generated"]),
            "bbs_count": sum(1 for item in records if item["bbs_generated"]),
        }

    def _load_drawing_models(self) -> List[dict[str, Any]]:
        payload = load_json_if_exists(
            self._root / "data/output/phase_g/g_2_reinforcement_drawing/reinforcement_drawing_model.json"
        )
        return [payload] if payload else []

    @staticmethod
    def _load_list_field(path: Path, key: str) -> List[dict[str, Any]]:
        payload = load_json_if_exists(path) or {}
        return payload.get(key) or payload.get("results") or []

    @staticmethod
    def _load_json_field(path: Path) -> dict[str, Any]:
        payload = load_json_if_exists(path) or {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
