"""Load recovery, expansion, production, and dashboard artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase J.2.1"
MODEL_VERSION = "5.28.1"
ENGINE_VERSION = "1.0.0"
OUTPUT_DIR_REL = Path("data/output/recovery_statistics_validation")


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_g = root / Path("data/output/phase_g")
    phase_h = root / Path("data/output/phase_h")
    phase_i = root / Path("data/output/phase_i")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "recovery_dir": root / Path("data/output/engineering_recovery"),
        "expansion_dir": root / Path("data/output/engineering_recovery_expansion"),
        "recovery_validation_dir": root / Path("data/output/engineering_recovery_validation"),
        "quantity_validation_dir": root / Path("data/output/engineering_quantity_validation"),
        "calc_integration_dir": root / Path("data/output/engineering_calculation_integration"),
        "accuracy_dashboard_dir": root / Path("data/output/accuracy_dashboard"),
        "discovery_dir": root / Path("data/output/reinforcement_discovery_analysis"),
        "recovery_registry": root / Path("data/output/engineering_recovery/recovery_registry.json"),
        "recovery_statistics": root / Path("data/output/engineering_recovery/recovery_statistics.json"),
        "recovery_summary": root / Path("data/output/engineering_recovery/recovery_summary.json"),
        "recovery_validation": root / Path("data/output/engineering_recovery/recovery_validation.json"),
        "recovery_health": root / Path("data/output/engineering_recovery/recovery_health.json"),
        "expansion_registry": root / Path("data/output/engineering_recovery_expansion/expansion_registry.json"),
        "expansion_statistics": root / Path("data/output/engineering_recovery_expansion/expansion_statistics.json"),
        "expansion_summary": root / Path("data/output/engineering_recovery_expansion/expansion_summary.json"),
        "expansion_validation": root / Path("data/output/engineering_recovery_expansion/expansion_validation.json"),
        "recovery_impact_summary": root
        / Path("data/output/engineering_recovery_validation/recovery_impact_summary.json"),
        "engineering_objects": phase_g / "g_5_1_engineering_objects/engineering_objects.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "steel_weight_results": phase_i / "i_11_steel_weight/steel_weight_results.json",
        "bbs_results": phase_i / "i_10_bbs/bbs_results.json",
        "beam_schedule_results": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
        "excel_export_registry": phase_i / "i_17_excel_export/excel_export_registry.json",
        "excel_export_statistics": phase_i / "i_17_excel_export/excel_export_statistics.json",
        "engineering_reports": phase_i / "i_16_engineering_report/engineering_reports.json",
        "reinforcement_inventory": root
        / Path("data/output/reinforcement_discovery_analysis/reinforcement_inventory.json"),
        "accuracy_statistics": root / Path("data/output/accuracy_dashboard/accuracy_statistics.json"),
        "accuracy_report": root / Path("data/output/accuracy_dashboard/accuracy_report.json"),
        "management_summary": root / Path("data/output/accuracy_dashboard/management_summary.json"),
    }


def _load_list(payload: dict[str, Any] | None, *keys: str) -> List[dict[str, Any]]:
    if payload is None:
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


class StatisticsCollector:
    """Collect read-only artifacts for statistics reconciliation."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        skip_keys = {
            "output_dir",
            "recovery_dir",
            "expansion_dir",
            "recovery_validation_dir",
            "quantity_validation_dir",
            "calc_integration_dir",
            "accuracy_dashboard_dir",
            "discovery_dir",
        }
        for key, path in self.paths.items():
            if key in skip_keys:
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        bars = _load_list(payloads.get("reinforcement_objects"), "bars")
        groups = _load_list(payloads.get("reinforcement_objects"), "groups")
        inventory = _load_list(payloads.get("reinforcement_inventory"), "inventory")
        j1_entries = (payloads.get("recovery_registry") or {}).get("entries") or []
        j2_entries = (payloads.get("expansion_registry") or {}).get("entries") or []
        objects = _load_list(payloads.get("engineering_objects"), "objects")

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "payloads": payloads,
            "bars": bars,
            "groups": groups,
            "inventory": inventory,
            "engineering_objects": objects,
            "j1_registry_entries": j1_entries,
            "j2_registry_entries": j2_entries,
            "recovery_statistics": payloads.get("recovery_statistics") or {},
            "recovery_summary": payloads.get("recovery_summary") or {},
            "recovery_validation": payloads.get("recovery_validation") or {},
            "recovery_health": payloads.get("recovery_health") or {},
            "expansion_statistics": payloads.get("expansion_statistics") or {},
            "expansion_summary": payloads.get("expansion_summary") or {},
            "expansion_validation": payloads.get("expansion_validation") or {},
            "recovery_impact_summary": payloads.get("recovery_impact_summary") or {},
            "accuracy_statistics": payloads.get("accuracy_statistics") or {},
            "accuracy_report": payloads.get("accuracy_report") or {},
            "management_summary": payloads.get("management_summary") or {},
            "steel_weight_results": _load_list(payloads.get("steel_weight_results"), "results"),
            "bbs_results": _load_list(payloads.get("bbs_results"), "results"),
            "beam_schedule_results": _load_list(payloads.get("beam_schedule_results"), "results"),
            "excel_export_registry": payloads.get("excel_export_registry") or {},
            "excel_export_statistics": payloads.get("excel_export_statistics") or {},
        }
