"""Load recovery and production artifacts for read-only impact validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase J.1.1"
MODEL_VERSION = "5.26.1"
ENGINE_VERSION = "1.0.0"
RECOVERY_PHASE = "Phase J.1"
RECOVERY_MODEL_VERSION = "5.26.0"
OUTPUT_DIR_REL = Path("data/output/engineering_recovery_validation")
RECOVERY_OUTPUT_DIR_REL = Path("data/output/engineering_recovery")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_g = root / Path("data/output/phase_g")
    phase_h = root / Path("data/output/phase_h")
    phase_i = root / Path("data/output/phase_i")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "recovery_dir": root / RECOVERY_OUTPUT_DIR_REL,
        "accuracy_dashboard_dir": root / Path("data/output/accuracy_dashboard"),
        "engineering_analysis_dir": root / Path("data/output/engineering_analysis"),
        "discovery_dir": root / Path("data/output/reinforcement_discovery_analysis"),
        "recovery_registry": root / RECOVERY_OUTPUT_DIR_REL / "recovery_registry.json",
        "recovery_statistics": root / RECOVERY_OUTPUT_DIR_REL / "recovery_statistics.json",
        "recovery_health": root / RECOVERY_OUTPUT_DIR_REL / "recovery_health.json",
        "recovery_summary": root / RECOVERY_OUTPUT_DIR_REL / "recovery_summary.json",
        "recovered_engineering_objects": root
        / RECOVERY_OUTPUT_DIR_REL
        / "recovered_engineering_objects.json",
        "recovery_decisions": root / RECOVERY_OUTPUT_DIR_REL / "recovery_decisions.json",
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "engineering_specifications": phase_h / "h_1_engineering_specifications/engineering_specifications.json",
        "calculation_contexts": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "engineering_calculation_results": phase_i
        / "i_2_2_calculation_result_framework/engineering_calculation_results.json",
        "reinforcement_readiness": phase_i / "i_2_1_calculation_readiness/reinforcement_readiness.json",
        "bbs_results": phase_i / "i_10_bbs/bbs_results.json",
        "steel_weight_results": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "beam_schedule_results": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "engineering_reports": phase_i / "i_16_engineering_report/engineering_reports.json",
        "excel_export_statistics": phase_i / "i_17_excel_export/excel_export_statistics.json",
        "excel_export_validation": phase_i / "i_17_excel_export/excel_export_validation.json",
        "accuracy_report": root / Path("data/output/accuracy_dashboard/accuracy_report.json"),
        "reinforcement_inventory": root
        / Path("data/output/reinforcement_discovery_analysis/reinforcement_inventory.json"),
        "reinforcement_traceability_matrix": root
        / Path("data/output/reinforcement_discovery_analysis/reinforcement_traceability_matrix.json"),
    }


def _load_list(payload: dict[str, Any] | None, *keys: str) -> List[dict[str, Any]]:
    if payload is None:
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


class ValidationCollector:
    """Collect recovery outputs and current production artifacts."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip_keys = {"output_dir", "recovery_dir", "accuracy_dashboard_dir", "engineering_analysis_dir", "discovery_dir"}
        for key, path in self.paths.items():
            if key in skip_keys:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        registry = payloads.get("recovery_registry") or {}
        registry_entries = registry.get("entries") or []

        bars = (payloads.get("reinforcement_objects") or {}).get("bars") or []
        groups = (payloads.get("reinforcement_objects") or {}).get("groups") or []
        objects = (payloads.get("engineering_objects") or {}).get("objects") or []
        specs = (payloads.get("engineering_specifications") or {}).get("specifications") or []
        contexts = (payloads.get("calculation_contexts") or {}).get("contexts") or []
        calc_results = _load_list(payloads.get("engineering_calculation_results"), "results", "engineering_calculation_results")
        bbs_records = _load_list(payloads.get("bbs_results"), "results")
        steel_weights = _load_list(payloads.get("steel_weight_results"), "results")
        beam_schedules = _load_list(payloads.get("beam_schedule_results"), "results")
        engineering_reports = _load_list(payloads.get("engineering_reports"), "results")
        inventory = (payloads.get("reinforcement_inventory") or {}).get("inventory") or []
        recovered_objects = (payloads.get("recovered_engineering_objects") or {}).get("objects") or []

        recovery_index = self._build_recovery_index(registry_entries, bars, recovered_objects)

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "payloads": payloads,
            "registry_entries": registry_entries,
            "recovery_index": recovery_index,
            "inventory": inventory,
            "inventory_count": len(inventory),
            "bars": bars,
            "groups": groups,
            "objects": objects,
            "specifications": specs,
            "contexts": contexts,
            "calculation_results": calc_results,
            "bbs_records": bbs_records,
            "steel_weights": steel_weights,
            "beam_schedules": beam_schedules,
            "engineering_reports": engineering_reports,
            "recovery_statistics": payloads.get("recovery_statistics") or {},
            "recovery_health": payloads.get("recovery_health") or {},
            "recovery_summary": payloads.get("recovery_summary") or {},
            "recovery_decisions": (payloads.get("recovery_decisions") or {}).get("decisions") or [],
            "recovered_objects": recovered_objects,
            "accuracy_report": payloads.get("accuracy_report") or {},
            "traceability_matrix": payloads.get("reinforcement_traceability_matrix") or {},
            "excel_statistics": payloads.get("excel_export_statistics") or {},
            "excel_validation": payloads.get("excel_export_validation") or {},
        }

    @staticmethod
    def _build_recovery_index(
        registry_entries: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        recovered_objects: List[dict[str, Any]],
    ) -> dict[str, Any]:
        recovered_bar_ids: set[str] = set()
        recovered_object_ids: set[str] = set()
        recovered_spec_ids: set[str] = set()
        recovered_context_ids: set[str] = set()
        recovered_discovery_ids: set[str] = set()
        recovered_recovery_ids: set[str] = set()
        registry_by_discovery: Dict[str, dict[str, Any]] = {}
        registry_by_recovery: Dict[str, dict[str, Any]] = {}
        registry_by_bar: Dict[str, dict[str, Any]] = {}

        for entry in registry_entries:
            discovery_id = str(entry.get("discovery_id") or "")
            recovery_id = str(entry.get("recovery_id") or "")
            bar_id = str(entry.get("normalized_bar_id") or "")
            if discovery_id:
                recovered_discovery_ids.add(discovery_id)
                registry_by_discovery[discovery_id] = entry
            if recovery_id:
                recovered_recovery_ids.add(recovery_id)
                registry_by_recovery[recovery_id] = entry
            if bar_id:
                recovered_bar_ids.add(bar_id)
                registry_by_bar[bar_id] = entry
            if entry.get("recovered_object_id"):
                recovered_object_ids.add(str(entry["recovered_object_id"]))
            if entry.get("specification_id"):
                recovered_spec_ids.add(str(entry["specification_id"]))
            if entry.get("context_id"):
                recovered_context_ids.add(str(entry["context_id"]))

        for bar in bars:
            trace = bar.get("traceability") or {}
            if not trace.get("recovery_source"):
                continue
            bar_id = str(bar.get("bar_id") or "")
            if bar_id:
                recovered_bar_ids.add(bar_id)
            discovery_id = str(trace.get("discovery_id") or "")
            if discovery_id:
                recovered_discovery_ids.add(discovery_id)

        for obj in recovered_objects:
            discovery_id = str(obj.get("source_discovery_id") or obj.get("discovery_id") or "")
            if discovery_id:
                recovered_discovery_ids.add(discovery_id)
            if obj.get("recovered_object_id"):
                recovered_object_ids.add(str(obj["recovered_object_id"]))
            if obj.get("specification_id"):
                recovered_spec_ids.add(str(obj["specification_id"]))
            if obj.get("context_id"):
                recovered_context_ids.add(str(obj["context_id"]))

        return {
            "recovered_bar_ids": sorted(recovered_bar_ids),
            "recovered_object_ids": sorted(recovered_object_ids),
            "recovered_spec_ids": sorted(recovered_spec_ids),
            "recovered_context_ids": sorted(recovered_context_ids),
            "recovered_discovery_ids": sorted(recovered_discovery_ids),
            "recovered_recovery_ids": sorted(recovered_recovery_ids),
            "registry_by_discovery": registry_by_discovery,
            "registry_by_recovery": registry_by_recovery,
            "registry_by_bar": registry_by_bar,
            "recovered_count": len(recovered_discovery_ids),
        }
