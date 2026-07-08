"""Load recovery registry and production calculation artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase J.1.3"
MODEL_VERSION = "5.27.0"
ENGINE_VERSION = "1.0.0"
OUTPUT_DIR_REL = Path("data/output/engineering_calculation_integration")
RECOVERY_DIR_REL = Path("data/output/engineering_recovery")
QUANTITY_VALIDATION_DIR_REL = Path("data/output/engineering_quantity_validation")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_g = root / Path("data/output/phase_g")
    phase_h = root / Path("data/output/phase_h")
    phase_i = root / Path("data/output/phase_i")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "recovery_dir": root / RECOVERY_DIR_REL,
        "quantity_validation_dir": root / QUANTITY_VALIDATION_DIR_REL,
        "recovery_registry": root / RECOVERY_DIR_REL / "recovery_registry.json",
        "quantity_traceability": root / QUANTITY_VALIDATION_DIR_REL / "quantity_traceability.json",
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
        "calculation_index_registry": phase_i / "i_4_5_calculation_index/calculation_index_registry.json",
        "dependency_graph": phase_i / "i_4_6_calculation_dependency/dependency_graph.json",
        "cut_length_results": phase_i / "i_6_cut_length/cut_length_results.json",
        "bar_identity_results": phase_i / "i_8_bar_identity/bar_identity_results.json",
        "steel_weight_results": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "bbs_results": phase_i / "i_10_bbs/bbs_results.json",
        "beam_schedule_results": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "engineering_reports": phase_i / "i_16_engineering_report/engineering_reports.json",
        "excel_export_statistics": phase_i / "i_17_excel_export/excel_export_statistics.json",
        "project_workspace": root / Path("data/output/phase_f/project_workspace.json"),
        "beam_geometry_model": root / Path("data/output/phase_f/beam_geometry_model.json"),
        "engineering_rules": root / Path("data/output/phase_e/general_notes_engineering_rules.json"),
    }


def _load_list(payload: dict[str, Any] | None, *keys: str) -> List[dict[str, Any]]:
    if payload is None:
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


class IntegrationCollector:
    """Collect production artifacts required for calculation integration repair."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip_keys = {"output_dir", "recovery_dir", "quantity_validation_dir"}
        for key, path in self.paths.items():
            if key in skip_keys:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        registry = payloads.get("recovery_registry") or {}
        registry_entries = registry.get("entries") or []
        bars = (payloads.get("reinforcement_objects") or {}).get("bars") or []
        groups = (payloads.get("reinforcement_objects") or {}).get("groups") or []
        contexts = (payloads.get("calculation_contexts") or {}).get("contexts") or []
        specs = (payloads.get("engineering_specifications") or {}).get("specifications") or []
        calc_results = _load_list(payloads.get("engineering_calculation_results"), "results")

        recovered_bar_ids = sorted(
            {
                str(entry.get("normalized_bar_id") or "")
                for entry in registry_entries
                if entry.get("normalized_bar_id")
            }
            | {
                str(bar.get("bar_id") or "")
                for bar in bars
                if (bar.get("traceability") or {}).get("recovery_source") and bar.get("bar_id")
            }
        )
        native_bar_ids = sorted(
            str(bar.get("bar_id") or "")
            for bar in bars
            if str(bar.get("bar_id") or "") not in set(recovered_bar_ids) and bar.get("bar_id")
        )

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "payloads": payloads,
            "registry_entries": registry_entries,
            "registry_by_bar": {
                str(entry.get("normalized_bar_id") or ""): entry
                for entry in registry_entries
                if entry.get("normalized_bar_id")
            },
            "recovered_bar_ids": recovered_bar_ids,
            "native_bar_ids": native_bar_ids,
            "bars": bars,
            "groups": groups,
            "contexts": contexts,
            "specifications": specs,
            "calculation_results": calc_results,
            "calculation_result_registry": payloads.get("calculation_result_registry") or {},
            "project_workspace": payloads.get("project_workspace") or {},
            "quantity_traceability": payloads.get("quantity_traceability") or {},
        }
