"""Read-only data loader for Phase L.2 Engineering Rule Audit."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

PHASE = "Phase L.2"
MODEL_VERSION = "6.4.0"
ENGINE_VERSION = "1.0.0"
PHASE_FOLDER = "PhaseL.2 - engineering_rule_audit"
OUTPUT_DIR_REL = Path("data/output") / PHASE_FOLDER
CONFIG_REL = Path("config/engineering_rule_audit.yaml")


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists() or path.stat().st_size < 3:
        return None
    import json
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def default_paths(project_root: Path) -> Dict[str, Path]:
    root = project_root
    v6_out = root / "data/output"
    v5_out = root.parent / "Version5/data/output"
    v5_i = v5_out / "phase_i"
    return {
        "output_dir": v6_out / PHASE_FOLDER,
        "config": root / CONFIG_REL,
        "src_root": root / "src",
        # Estimator ground truth
        "estimator_excel": _find_estimator_excel(root),
        # V6 engineering pipeline outputs (may be absent)
        "v6_engineering_objects": v6_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
        "v6_reinforcement_objects": v6_out / "phase_i/i_2_reinforcement_engine/reinforcement_objects.json",
        "v6_calculation_contexts": v6_out / "phase_i/i_1_calculation_context/calculation_contexts.json",
        "v6_readiness": v6_out / "phase_i/i_2_1_calculation_readiness/reinforcement_readiness.json",
        "v6_cut_length": v6_out / "phase_i/i_6_cut_length/cut_length_results.json",
        "v6_development_length": v6_out / "phase_i/i_3_development_length/development_length_results.json",
        "v6_hook_results": v6_out / "phase_i/i_4_hook_length/hook_results.json",
        "v6_lap_results": v6_out / "phase_i/i_5_lap_length/lap_length_results.json",
        "v6_steel_weight": v6_out / "phase_i/i_11_steel_weight/steel_weight_results.json",
        "v6_bbs_results": v6_out / "phase_i/i_10_bbs/bbs_results.json",
        "v6_beam_schedule": v6_out / "phase_i/i_15_beam_schedule/beam_schedule_results.json",
        "v6_engineering_reports": v6_out / "phase_i/i_16_engineering_report/engineering_reports.json",
        "v6_decisions": v6_out / "engineering_intent_resolution/engineering_decision_objects.json",
        "v6_intents": v6_out / "engineering_intent/engineering_intent_objects.json",
        "v6_recovery": v6_out / "engineering_recovery/recovery_registry.json",
        # V5 reference pipeline outputs (for baseline evidence)
        "v5_engineering_objects": v5_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
        "v5_reinforcement_objects": v5_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "v5_calculation_contexts": v5_i / "i_1_calculation_context/calculation_contexts.json",
        "v5_readiness": v5_i / "i_2_1_calculation_readiness/reinforcement_readiness.json",
        "v5_cut_length": v5_i / "i_6_cut_length/cut_length_results.json",
        "v5_development_length": v5_i / "i_3_development_length/development_length_results.json",
        "v5_hook_results": v5_i / "i_4_hook_length/hook_results.json",
        "v5_lap_results": v5_i / "i_5_lap_length/lap_length_results.json",
        "v5_steel_weight": v5_i / "i_11_steel_weight/steel_weight_results.json",
        "v5_bbs_results": v5_i / "i_10_bbs/bbs_results.json",
        "v5_beam_schedule": v5_i / "i_15_beam_schedule/beam_schedule_results.json",
        "v5_engineering_reports": v5_i / "i_16_engineering_report/engineering_reports.json",
        "v5_engineering_gap": v5_out / "engineering_analysis/engineering_gap_analysis.json",
        "v5_accuracy_stats": v5_out / "accuracy_dashboard/accuracy_statistics.json",
        # L.1 outputs as input to L.2
        "l1_gap_report": v6_out / "PhaseL.1 - accuracy_sprint_1_estimator_gap_closure/engineering_gap_report.json",
        "l1_improvement_tracker": v6_out / "PhaseL.1 - accuracy_sprint_1_estimator_gap_closure/improvement_tracker.json",
        "l1_role_gap": v6_out / "PhaseL.1 - accuracy_sprint_1_estimator_gap_closure/reinforcement_role_gap_analysis.json",
        "l1_rule_gap": v6_out / "PhaseL.1 - accuracy_sprint_1_estimator_gap_closure/engineering_rule_gap_analysis.json",
    }


def _find_estimator_excel(root: Path) -> Path:
    folder = root / "data/Estimator_Validated_Output"
    candidates = sorted(folder.glob("*.xlsx")) if folder.exists() else []
    return candidates[0] if candidates else folder / "missing.xlsx"


class AuditLoader:
    """Load all available Phase L.2 audit inputs. Strictly read-only."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def load(self) -> Dict[str, Any]:
        skip = {"output_dir", "config", "estimator_excel", "src_root"}
        payloads: Dict[str, Any] = {}
        for key, path in self.paths.items():
            if key in skip:
                continue
            val = _load_json(path)
            payloads[key] = val
            self.load_status[key] = val is not None
        return {
            "payloads": payloads,
            "load_status": dict(self.load_status),
            "paths": {k: str(v) for k, v in self.paths.items()},
            "project_root": str(self.project_root),
            "src_root": str(self.paths["src_root"]),
        }


def load_config(config_path: Path) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "enable": True,
        "scan_source_code": True,
        "use_v5_reference": True,
        "generate_excel_report": True,
        "strict_validation": True,
        "trace_all_roles": True,
        "detect_dead_code": True,
        "generate_dependency_graph": True,
        "generate_implementation_matrix": True,
    }
    if not config_path.exists():
        return defaults
    try:
        import yaml  # type: ignore
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            defaults.update(payload)
    except Exception:
        pass
    return defaults
