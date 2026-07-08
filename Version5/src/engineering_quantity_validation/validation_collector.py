"""Load recovery and quantity pipeline artifacts for read-only integration validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase J.1.2"
MODEL_VERSION = "5.26.2"
ENGINE_VERSION = "1.0.0"
RECOVERY_PHASE = "Phase J.1"
OUTPUT_DIR_REL = Path("data/output/engineering_quantity_validation")
RECOVERY_OUTPUT_DIR_REL = Path("data/output/engineering_recovery")
RECOVERY_VALIDATION_DIR_REL = Path("data/output/engineering_recovery_validation")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_g = root / Path("data/output/phase_g")
    phase_h = root / Path("data/output/phase_h")
    phase_i = root / Path("data/output/phase_i")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "recovery_dir": root / RECOVERY_OUTPUT_DIR_REL,
        "recovery_validation_dir": root / RECOVERY_VALIDATION_DIR_REL,
        "accuracy_dashboard_dir": root / Path("data/output/accuracy_dashboard"),
        "recovery_registry": root / RECOVERY_OUTPUT_DIR_REL / "recovery_registry.json",
        "recovered_engineering_objects": root
        / RECOVERY_OUTPUT_DIR_REL
        / "recovered_engineering_objects.json",
        "recovery_impact_summary": root
        / RECOVERY_VALIDATION_DIR_REL
        / "recovery_impact_summary.json",
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "engineering_specifications": phase_h / "h_1_engineering_specifications/engineering_specifications.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "calculation_context_registry": phase_i / "i_1_calculation_context/calculation_context_registry.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "reinforcement_registry": phase_i / "i_2_reinforcement_engine/reinforcement_registry.json",
        "reinforcement_readiness": phase_i / "i_2_1_calculation_readiness/reinforcement_readiness.json",
        "engineering_calculation_results": phase_i
        / "i_2_2_calculation_result_framework/engineering_calculation_results.json",
        "calculation_result_registry": phase_i
        / "i_2_2_calculation_result_framework/calculation_result_registry.json",
        "development_length_results": phase_i / "i_3_development_length/development_length_results.json",
        "hook_length_results": phase_i / "i_4_hook_length/hook_length_results.json",
        "cut_length_results": phase_i / "i_6_cut_length/cut_length_results.json",
        "shape_code_results": phase_i / "i_7_shape_code/shape_code_results.json",
        "bar_identity_results": phase_i / "i_8_bar_identity/bar_identity_results.json",
        "bar_group_results": phase_i / "i_9_bar_group/bar_group_results.json",
        "bbs_results": phase_i / "i_10_bbs/bbs_results.json",
        "bbs_registry": phase_i / "i_10_bbs/bbs_registry.json",
        "steel_weight_results": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "steel_weight_registry": phase_i / "i_11_steel_weight/steel_weight_registry.json",
        "beam_schedule_results": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "beam_schedule_registry": phase_i / "i_15_beam_schedule/beam_schedule_registry.json",
        "engineering_reports": phase_i / "i_16_engineering_report/engineering_reports.json",
        "engineering_report_registry": phase_i / "i_16_engineering_report/engineering_report_registry.json",
        "excel_export_statistics": phase_i / "i_17_excel_export/excel_export_statistics.json",
        "excel_export_validation": phase_i / "i_17_excel_export/excel_export_validation.json",
        "excel_export_registry": phase_i / "i_17_excel_export/excel_export_registry.json",
        "accuracy_report": root / Path("data/output/accuracy_dashboard/accuracy_report.json"),
    }


def _load_list(payload: dict[str, Any] | None, *keys: str) -> List[dict[str, Any]]:
    if payload is None:
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


class QuantityValidationCollector:
    """Collect recovery outputs and quantity pipeline artifacts."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip_keys = {
            "output_dir",
            "recovery_dir",
            "recovery_validation_dir",
            "accuracy_dashboard_dir",
        }
        for key, path in self.paths.items():
            if key in skip_keys:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        registry = payloads.get("recovery_registry") or {}
        registry_entries = registry.get("entries") or []
        bars = (payloads.get("reinforcement_objects") or {}).get("bars") or []
        objects = (payloads.get("engineering_objects") or {}).get("objects") or []
        specs = (payloads.get("engineering_specifications") or {}).get("specifications") or []
        contexts = (payloads.get("calculation_contexts") or {}).get("contexts") or []
        recovered_objects = (payloads.get("recovered_engineering_objects") or {}).get("objects") or []
        calc_results = _load_list(payloads.get("engineering_calculation_results"), "results")
        readiness_bars = (payloads.get("reinforcement_readiness") or {}).get("bars") or []

        recovery_index = self._build_recovery_index(registry_entries, bars, recovered_objects)
        bar_by_id = {str(bar.get("bar_id")): bar for bar in bars if bar.get("bar_id")}
        context_by_id = {str(ctx.get("context_id")): ctx for ctx in contexts if ctx.get("context_id")}
        spec_by_id = {str(spec.get("specification_id")): spec for spec in specs if spec.get("specification_id")}
        calc_by_bar = self._index_calc_results(calc_results)

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "payloads": payloads,
            "registry_entries": registry_entries,
            "recovery_index": recovery_index,
            "recovered_objects": recovered_objects,
            "bars": bars,
            "bar_by_id": bar_by_id,
            "objects": objects,
            "specifications": specs,
            "spec_by_id": spec_by_id,
            "contexts": contexts,
            "context_by_id": context_by_id,
            "calculation_results": calc_results,
            "calc_by_bar": calc_by_bar,
            "readiness_by_bar": {
                str(item.get("bar_id")): item for item in readiness_bars if item.get("bar_id")
            },
            "cut_length_by_bar": self._index_stage_results(payloads.get("cut_length_results"), "bar_id"),
            "development_length_by_bar": self._index_stage_results(payloads.get("development_length_results"), "bar_id"),
            "hook_length_by_bar": self._index_stage_results(payloads.get("hook_length_results"), "bar_id"),
            "shape_code_by_bar": self._index_stage_results(payloads.get("shape_code_results"), "bar_id"),
            "bar_identity_by_bar": self._index_stage_results(payloads.get("bar_identity_results"), "bar_id"),
            "bar_group_by_bar": self._index_stage_results(payloads.get("bar_group_results"), "bar_id"),
            "steel_weight_by_bar": self._index_stage_results(payloads.get("steel_weight_results"), "bar_id"),
            "bbs_by_bar": self._index_bbs(payloads.get("bbs_results")),
            "beam_schedules": _load_list(payloads.get("beam_schedule_results"), "results"),
            "engineering_reports": _load_list(payloads.get("engineering_reports"), "results"),
            "excel_statistics": payloads.get("excel_export_statistics") or {},
            "excel_validation": payloads.get("excel_export_validation") or {},
            "accuracy_report": payloads.get("accuracy_report") or {},
            "recovery_impact_summary": payloads.get("recovery_impact_summary") or {},
            "registries": {
                "steel_weight": payloads.get("steel_weight_registry") or {},
                "bbs": payloads.get("bbs_registry") or {},
                "beam_schedule": payloads.get("beam_schedule_registry") or {},
                "engineering_report": payloads.get("engineering_report_registry") or {},
                "excel_export": payloads.get("excel_export_registry") or {},
                "calculation_context": payloads.get("calculation_context_registry") or {},
                "calculation_result": payloads.get("calculation_result_registry") or {},
                "reinforcement": payloads.get("reinforcement_registry") or {},
            },
        }

    @staticmethod
    def _index_calc_results(calc_results: List[dict[str, Any]]) -> Dict[str, List[dict[str, Any]]]:
        index: Dict[str, List[dict[str, Any]]] = {}
        for result in calc_results:
            bar_id = str(result.get("input_bar_id") or "")
            if not bar_id:
                continue
            index.setdefault(bar_id, []).append(result)
        return index

    @staticmethod
    def _index_stage_results(payload: dict[str, Any] | None, key: str) -> Dict[str, dict[str, Any]]:
        index: Dict[str, dict[str, Any]] = {}
        for item in _load_list(payload, "results"):
            item_id = str(item.get(key) or "")
            if item_id:
                index[item_id] = item
        return index

    @staticmethod
    def _index_bbs(payload: dict[str, Any] | None) -> Dict[str, dict[str, Any]]:
        index: Dict[str, dict[str, Any]] = {}
        for item in _load_list(payload, "results"):
            bar_id = str(item.get("bar_id") or "")
            if bar_id:
                index[bar_id] = item
            for member_id in item.get("member_bar_ids") or []:
                index[str(member_id)] = item
        return index

    @staticmethod
    def _build_recovery_index(
        registry_entries: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        recovered_objects: List[dict[str, Any]],
    ) -> dict[str, Any]:
        recovered_bar_ids: set[str] = set()
        recovered_object_ids: set[str] = set()
        recovered_discovery_ids: set[str] = set()
        registry_by_bar: Dict[str, dict[str, Any]] = {}
        registry_by_recovery: Dict[str, dict[str, Any]] = {}

        for entry in registry_entries:
            bar_id = str(entry.get("normalized_bar_id") or "")
            if bar_id:
                recovered_bar_ids.add(bar_id)
                registry_by_bar[bar_id] = entry
            if entry.get("recovered_object_id"):
                recovered_object_ids.add(str(entry["recovered_object_id"]))
            if entry.get("discovery_id"):
                recovered_discovery_ids.add(str(entry["discovery_id"]))
            if entry.get("recovery_id"):
                registry_by_recovery[str(entry["recovery_id"])] = entry

        for bar in bars:
            trace = bar.get("traceability") or {}
            if not trace.get("recovery_source"):
                continue
            bar_id = str(bar.get("bar_id") or "")
            if bar_id:
                recovered_bar_ids.add(bar_id)

        return {
            "recovered_bar_ids": sorted(recovered_bar_ids),
            "recovered_object_ids": sorted(recovered_object_ids),
            "recovered_discovery_ids": sorted(recovered_discovery_ids),
            "registry_by_bar": registry_by_bar,
            "registry_by_recovery": registry_by_recovery,
            "recovered_count": len(recovered_bar_ids),
        }
