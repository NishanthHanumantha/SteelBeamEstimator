"""Load geometric_stirrup_evidence.yaml. MODEL_VERSION: 9.3.0"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

MODEL_VERSION = "9.3.0"

_DEFAULTS: Dict[str, Any] = {
    "enable_geometry_stirrup_evidence": True,
    "detection": {
        "min_tick_count": 3,
        "pitch_min_mm": 50,
        "pitch_max_mm": 400,
        "pitch_cv_max": 0.35,
        "text_spacing_tolerance_mm": 15,
        "prefer_vector": True,
        "enable_opencv_fallback": True,
    },
    "fusion": {
        "synthesize_geometry_only": True,
        "synthesized_confidence": "WARN",
        "agree_confidence": "HIGH",
        "conflict_flag": "GEOMETRY_TEXT_CONFLICT",
    },
    "zone_refinement": {
        "enable": True,
        "prefer_pitch_change": True,
        "prefer_support_locations": True,
    },
    "residual_targets_path": "data/output/Track1_geometric_evidence/residual_target_beams.json",
}


def load_config(engine_root: Path) -> Dict[str, Any]:
    path = Path(engine_root) / "config" / "geometric_stirrup_evidence.yaml"
    cfg = dict(_DEFAULTS)
    if path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for k, v in raw.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                merged = dict(cfg[k])
                merged.update(v)
                cfg[k] = merged
            else:
                cfg[k] = v
    return cfg


def is_enabled(engine_root: Path) -> bool:
    return bool(load_config(engine_root).get("enable_geometry_stirrup_evidence", True))
