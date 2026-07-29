"""
Path resolution for current_model (production baseline).

Deployment and app code must reference these helpers — never hardcode
model version directory names.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _current_model_root() -> Path:
    # config/paths.py → config/ → current_model/
    return Path(__file__).resolve().parents[1]


CURRENT_MODEL_ROOT = _current_model_root()
PACKAGE_ROOT = CURRENT_MODEL_ROOT.parent  # Steel-Beam-Estimation/


def _looks_like_engine(root: Path) -> bool:
    return (root / "Run_PY").is_dir()


def _discover_monorepo_engine() -> Optional[Path]:
    """
    Mode B layout (Lightsail monorepo checkout):

      …/SteelBeamEstimator/
        Version8/                         ← engine
        Steel-Beam-Estimation/current_model/

    Walk parents of current_model looking for a sibling Version8 with Run_PY.
    """
    for parent in CURRENT_MODEL_ROOT.parents:
        candidate = parent / "Version8"
        if _looks_like_engine(candidate):
            return candidate.resolve()
    return None


def resolve_engine_root() -> Path:
    """
    Active estimation engine root (contains Run_PY/, src/, data/).

    Resolution order:
      1. STEEL_ENGINE_ROOT environment variable
      2. current_model itself (packaged layout with Run_PY present)
      3. optional config/engine_root.path (one absolute/relative path line)
      4. monorepo sibling Version8 (Mode B auto-detect)
      5. fallback to current_model (framework-only until packaging phase)
    """
    env = (os.environ.get("STEEL_ENGINE_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()

    if _looks_like_engine(CURRENT_MODEL_ROOT):
        return CURRENT_MODEL_ROOT.resolve()

    marker = CURRENT_MODEL_ROOT / "config" / "engine_root.path"
    if marker.exists():
        line = marker.read_text(encoding="utf-8").strip().splitlines()
        if line and line[0].strip() and not line[0].strip().startswith("#"):
            p = Path(line[0].strip()).expanduser()
            if not p.is_absolute():
                p = (CURRENT_MODEL_ROOT / p).resolve()
            else:
                p = p.resolve()
            return p

    discovered = _discover_monorepo_engine()
    if discovered is not None:
        return discovered

    return CURRENT_MODEL_ROOT.resolve()


# Runtime directories under current_model/
INPUTS_DIR = CURRENT_MODEL_ROOT / "inputs"
OUTPUTS_DIR = CURRENT_MODEL_ROOT / "outputs"
LOGS_DIR = CURRENT_MODEL_ROOT / "logs"
TEMP_DIR = CURRENT_MODEL_ROOT / "temp"
UPLOADS_DIR = CURRENT_MODEL_ROOT / "uploads"
CONFIG_DIR = CURRENT_MODEL_ROOT / "config"
TEMPLATES_DIR = CURRENT_MODEL_ROOT / "templates"
STATIC_DIR = CURRENT_MODEL_ROOT / "static"
WEBAPP_DIR = CURRENT_MODEL_ROOT / "webapp"

RUNTIME_DIRS = (INPUTS_DIR, OUTPUTS_DIR, LOGS_DIR, TEMP_DIR, UPLOADS_DIR)


def ensure_runtime_dirs() -> None:
    for d in RUNTIME_DIRS:
        d.mkdir(parents=True, exist_ok=True)
