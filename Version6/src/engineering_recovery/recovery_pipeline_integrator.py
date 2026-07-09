"""Integrate recovered objects into production calculation pipeline."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists


class RecoveryPipelineIntegrator:
    """Merge recovered artifacts and rerun downstream production engines."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._rules_path = project_root / "data/output/phase_e/general_notes_engineering_rules.json"
        self._phase_i = project_root / "data/output/phase_i"
        self._phase_h = project_root / "data/output/phase_h"
        self._phase_g = project_root / "data/output/phase_g"

    def integrate(
        self,
        snapshot: dict[str, Any],
        built: dict[str, Any],
        recovered_bars: List[dict[str, Any]],
        recovered_groups: List[dict[str, Any]],
    ) -> dict[str, Any]:
        from src.engineering_calculations.calculation_dependency.dependency_graph import CalculationDependencyGraph
        from src.engineering_calculations.calculation_result_factory import CalculationResultFactory
        from src.reinforcement_calculation.reinforcement_builder import ReinforcementBuilder

        if not recovered_bars:
            return {"status": "SKIPPED", "reason": "No recovered bars to integrate"}

        existing_objects = deepcopy(snapshot.get("existing_objects") or [])
        existing_specs = deepcopy(snapshot.get("existing_specs") or [])
        existing_contexts = deepcopy(snapshot.get("existing_contexts") or [])
        existing_bars = deepcopy(snapshot.get("existing_bars") or [])
        existing_groups = deepcopy(snapshot.get("existing_groups") or [])

        merged_objects = existing_objects + built.get("engineering_objects", [])
        merged_specs = existing_specs + built.get("specifications", [])
        merged_contexts = existing_contexts + built.get("contexts", [])
        merged_bars = existing_bars + [bar for bar in recovered_bars if bar.get("bar_id") not in {item.get("bar_id") for item in existing_bars}]
        merged_groups = existing_groups + [group for group in recovered_groups if group.get("group_id") not in {item.get("group_id") for item in existing_groups}]

        self._write_json(
            self._phase_g / "g_5_1_engineering_objects/engineering_objects.json",
            {
                "phase": "Phase G.5.1",
                "object_count": len(merged_objects),
                "objects": merged_objects,
            },
        )
        self._write_json(
            self._phase_h / "h_1_engineering_specifications/engineering_specifications.json",
            {
                "phase": "Phase H.1",
                "specification_count": len(merged_specs),
                "specifications": merged_specs,
            },
        )
        self._write_json(
            self._phase_i / "i_1_calculation_context/calculation_contexts.json",
            {
                "phase": "Phase I.1",
                "context_count": len(merged_contexts),
                "contexts": merged_contexts,
            },
        )

        project_id = str((snapshot.get("project_workspace") or {}).get("project_id") or "")
        drawing_models = self._load_drawing_models()
        i2_exports = ReinforcementBuilder.build_project_exports(
            merged_bars,
            merged_groups,
            built.get("registry"),
            merged_contexts,
            drawing_models,
            project_id=project_id,
        )
        self._write_json(
            self._phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
            {
                "phase": "Phase I.2",
                "bar_count": len(merged_bars),
                "group_count": len(merged_groups),
                "bars": merged_bars,
                "groups": merged_groups,
            },
        )
        self._write_json(
            self._phase_i / "i_2_reinforcement_engine/reinforcement_registry.json",
            i2_exports.get("reinforcement_registry", {}),
        )

        model = self._load_calculation_model(snapshot, merged_specs, merged_contexts, merged_bars, merged_groups)
        factory = CalculationResultFactory()
        new_results, i22_exports = factory.initialize_framework(
            recovered_bars,
            recovered_groups,
            built.get("contexts", []),
            drawing_models,
            project_id=project_id,
        )
        existing_results = model.get("engineering_calculation_results") or []
        model["engineering_calculation_results"] = existing_results + new_results
        model.update(
            {
                "engineering_specifications": merged_specs,
                "calculation_contexts": merged_contexts,
                "reinforcement_bars": merged_bars,
                "reinforcement_groups": merged_groups,
            }
        )
        self._write_json(
            self._phase_i / "i_2_2_calculation_result_framework/engineering_calculation_results.json",
            {
                "phase": "Phase I.2.2",
                "result_count": len(model["engineering_calculation_results"]),
                "results": model["engineering_calculation_results"],
            },
        )

        dependency_graph = CalculationDependencyGraph.from_spec()
        if not model.get("calculation_dependency_graph"):
            model["calculation_dependency_graph"] = dependency_graph.to_dict()

        self._run_engine_chain(model, drawing_models, project_id)
        self._write_downstream_exports(model)
        return {
            "status": "SUCCESS",
            "merged_bar_count": len(merged_bars),
            "recovered_bar_count": len(recovered_bars),
            "existing_bar_count": len(existing_bars),
            "merged_spec_count": len(merged_specs),
            "merged_context_count": len(merged_contexts),
        }

    def complete_pipeline(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Run downstream engines on current production artifacts without remerging bars."""
        existing_specs = (snapshot.get("existing_specs") or [])
        existing_contexts = (snapshot.get("existing_contexts") or [])
        existing_bars = (snapshot.get("existing_bars") or [])
        existing_groups = (snapshot.get("existing_groups") or [])
        project_id = str((snapshot.get("project_workspace") or {}).get("project_id") or "")
        drawing_models = self._load_drawing_models()
        model = self._load_calculation_model(
            snapshot,
            existing_specs,
            existing_contexts,
            existing_bars,
            existing_groups,
        )
        self._run_engine_chain(model, drawing_models, project_id)
        self._write_downstream_exports(model)
        return {
            "status": "SUCCESS",
            "mode": "PIPELINE_COMPLETION",
            "merged_bar_count": len(existing_bars),
            "recovered_bar_count": len(
                [bar for bar in existing_bars if (bar.get("traceability") or {}).get("recovery_source")]
            ),
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

    def _load_calculation_model(
        self,
        snapshot: dict[str, Any],
        specs: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        groups: List[dict[str, Any]],
    ) -> dict[str, Any]:
        calc_payload = load_json_if_exists(
            self._phase_i / "i_2_2_calculation_result_framework/engineering_calculation_results.json"
        ) or {}
        results = calc_payload.get("results") or calc_payload.get("engineering_calculation_results") or []
        beam_model = load_json_if_exists(self._root / "data/output/phase_f/beam_geometry_model.json") or {}
        return {
            "engineering_specifications": specs,
            "calculation_contexts": contexts,
            "reinforcement_bars": bars,
            "reinforcement_groups": groups,
            "beams": beam_model.get("beams") or [],
            "engineering_calculation_results": deepcopy(results),
            "calculation_result_registry": snapshot.get("calculation_result_registry") or {},
            "calculation_dependency_graph": self._load_json_field(
                self._phase_i / "i_4_6_calculation_dependency/dependency_graph.json"
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
            "quantity_registry": self._load_json_field(
                self._phase_i / "i_13_quantity/quantity_registry.json"
            ),
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
                self._phase_i / "i_16_engineering_report/engineering_report_results.json",
                "results",
            ),
            "engineering_report_registry": self._load_json_field(
                self._phase_i / "i_16_engineering_report/engineering_report_registry.json"
            ),
            "project_workspace": snapshot.get("project_workspace") or {},
        }

    def _write_downstream_exports(self, model: dict[str, Any]) -> None:
        mapping = {
            "i_2_2_calculation_result_framework/engineering_calculation_results.json": {
                "phase": "Phase I.2.2",
                "result_count": len(model.get("engineering_calculation_results") or []),
                "results": model.get("engineering_calculation_results") or [],
            },
            "i_8_bar_identity/bar_identity_results.json": {
                "phase": "Phase I.8",
                "result_count": len(model.get("bar_identity_results") or []),
                "results": model.get("bar_identity_results") or [],
            },
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
            "i_16_engineering_report/engineering_report_results.json": {
                "phase": "Phase I.16",
                "result_count": len(model.get("engineering_report_results") or []),
                "results": model.get("engineering_report_results") or [],
            },
        }
        for relative_path, payload in mapping.items():
            self._write_json(self._phase_i / relative_path, payload)

    def _load_drawing_models(self) -> List[dict[str, Any]]:
        payload = load_json_if_exists(
            self._root / "data/output/phase_g/g_2_reinforcement_drawing/reinforcement_drawing_model.json"
        )
        if payload:
            return [payload]
        return []

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
