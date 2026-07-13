"""
Load all inputs for Phase L.2.1 Engineering Feature Extraction Engine.
Read-only. Does not modify any existing pipeline output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PHASE_FOLDER = "PhaseL.2.1 - engineering_feature_extraction"
L2_FOLDER = "PhaseL.2 - engineering_reinforcement_interpretation"
OUTPUT_REL = Path("data/output") / PHASE_FOLDER
CONFIG_REL = Path("config/engineering_feature_extraction.yaml")


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists() or path.stat().st_size < 3:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class FeatureCollector:
    """Collect all read-only inputs needed for feature extraction."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        v6_out = project_root / "data/output"
        v5_out = project_root.parent / "Version5/data/output"
        v5_i = v5_out / "phase_i"
        self._paths = {
            "output_dir": v6_out / PHASE_FOLDER,
            "config": project_root / CONFIG_REL,
            "l2_beam_models": v6_out / L2_FOLDER / "beam_reinforcement_models.json",
            "l2_bar_classification": v6_out / L2_FOLDER / "bar_role_classification.json",
            "l2_support_zones": v6_out / L2_FOLDER / "support_zone_analysis.json",
            "l2_continuity": v6_out / L2_FOLDER / "continuity_analysis.json",
            "l2_reinforcement_regions": v6_out / L2_FOLDER / "reinforcement_regions.json",
            "v5_engineering_objects": v5_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
            "v5_reinforcement_objects": v5_i / "i_2_reinforcement_engine/reinforcement_objects.json",
            "v5_beam_schedule": v5_i / "i_15_beam_schedule/beam_schedule_results.json",
            "v5_recovery": v5_out / "engineering_recovery/recovered_engineering_objects.json",
            "v5_general_notes": v5_out / "phase_e/general_notes.json",
            "v5_steel_weight": v5_i / "i_11_steel_weight/steel_weight_results.json",
        }

    def collect(self) -> Dict[str, Any]:
        config = self._load_config()
        payloads: Dict[str, Any] = {}
        load_status: Dict[str, bool] = {}
        skip = {"output_dir", "config"}
        for key, path in self._paths.items():
            if key in skip:
                continue
            val = _load_json(path)
            payloads[key] = val
            load_status[key] = val is not None

        l2_models = payloads.get("l2_beam_models") or {}
        return {
            "config": config,
            "load_status": load_status,
            "output_dir": self._paths["output_dir"],
            "project_root": str(self._root),
            "l2_beam_models": l2_models,
            "l2_bar_classification": payloads.get("l2_bar_classification"),
            "l2_support_zones": payloads.get("l2_support_zones"),
            "l2_continuity": payloads.get("l2_continuity"),
            "l2_reinforcement_regions": payloads.get("l2_reinforcement_regions"),
            "v5_engineering_objects": payloads.get("v5_engineering_objects"),
            "v5_reinforcement_objects": payloads.get("v5_reinforcement_objects"),
            "v5_beam_schedule": payloads.get("v5_beam_schedule"),
            "v5_recovery": payloads.get("v5_recovery"),
            "v5_general_notes": payloads.get("v5_general_notes"),
            "beam_models_list": l2_models.get("models") or [],
        }

    def _load_config(self) -> Dict[str, Any]:
        defaults: Dict[str, Any] = {
            "enable": True,
            "generate_excel_report": True,
            "strict_validation": True,
            "extract_all_beams": True,
            "top_cover_mm": 25.0,
            "bottom_cover_mm": 25.0,
            "side_cover_mm": 25.0,
            "support_zone_fraction": 0.25,
            "continuity_threshold": 0.80,
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
