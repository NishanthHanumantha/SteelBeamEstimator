"""Load all inputs for Phase L.2 Engineering Reinforcement Interpretation Engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PHASE_FOLDER = "PhaseL.2 - engineering_reinforcement_interpretation"
OUTPUT_REL = Path("data/output") / PHASE_FOLDER
CONFIG_REL = Path("config/engineering_reinforcement_interpretation.yaml")
REFERENCE_IMAGES_FOLDER = "BeamReinforcement_Bars_Identification"


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists() or path.stat().st_size < 3:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _best(v6_path: Path, v5_path: Path) -> Optional[Any]:
    v6 = _load_json(v6_path)
    return v6 if v6 is not None else _load_json(v5_path)


class InterpretationCollector:
    """Collect all available inputs. Strictly read-only."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        v6_out = project_root / "data/output"
        v5_out = project_root.parent / "Version5/data/output"
        v5_i = v5_out / "phase_i"
        self._paths = {
            "output_dir": v6_out / PHASE_FOLDER,
            "config": project_root / CONFIG_REL,
            "reference_images": project_root.parent / REFERENCE_IMAGES_FOLDER,
            "v5_engineering_objects": v5_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
            "v5_reinforcement_objects": v5_i / "i_2_reinforcement_engine/reinforcement_objects.json",
            "v5_beam_schedule": v5_i / "i_15_beam_schedule/beam_schedule_results.json",
            "v5_recovery": v5_out / "engineering_recovery/recovered_engineering_objects.json",
            "v5_general_notes": v5_out / "phase_e/general_notes.json",
            "v5_steel_weight": v5_i / "i_11_steel_weight/steel_weight_results.json",
            "v5_beam_geometry": v5_out / "phase_f/beam_geometry_model.json",
            "v5_engineering_gap": v5_out / "engineering_analysis/engineering_gap_analysis.json",
            "l1_role_gap": v6_out / "PhaseL.1 - accuracy_sprint_1_estimator_gap_closure/reinforcement_role_gap_analysis.json",
            "l2_audit": v6_out / "PhaseL.2 - engineering_rule_audit/role_audit.json",
        }

    def collect(self) -> Dict[str, Any]:
        config = self._load_config()
        payloads: Dict[str, Any] = {}
        load_status: Dict[str, bool] = {}
        skip = {"output_dir", "config", "reference_images"}
        for key, path in self._paths.items():
            if key in skip:
                continue
            val = _load_json(path)
            payloads[key] = val
            load_status[key] = val is not None

        return {
            "config": config,
            "load_status": load_status,
            "paths": {k: str(v) for k, v in self._paths.items()},
            "project_root": str(self._root),
            "output_dir": self._paths["output_dir"],
            "reference_images_path": str(self._paths["reference_images"]),
            "reference_images_exist": self._paths["reference_images"].exists(),
            "payloads": payloads,
            "engineering_objects": payloads.get("v5_engineering_objects"),
            "reinforcement_objects": payloads.get("v5_reinforcement_objects"),
            "beam_schedule": payloads.get("v5_beam_schedule"),
            "recovery": payloads.get("v5_recovery"),
            "general_notes": payloads.get("v5_general_notes"),
            "steel_weight": payloads.get("v5_steel_weight"),
            "beam_geometry": payloads.get("v5_beam_geometry"),
        }

    def _load_config(self) -> Dict[str, Any]:
        defaults: Dict[str, Any] = {
            "enable": True,
            "use_reference_dataset": True,
            "benchmark_beams": ["B1", "B2", "B8", "B9", "B10"],
            "generate_excel_report": True,
            "strict_validation": True,
            "interpret_all_beams": True,
        }
        cfg_path = self._paths["config"]
        if cfg_path.exists():
            try:
                import yaml  # type: ignore
                data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    defaults.update(data)
            except Exception:
                pass
        return defaults
