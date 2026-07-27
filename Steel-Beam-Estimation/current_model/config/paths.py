"""
Path resolution for current_model (Phase D.2).

Deployment and app code must reference these helpers — never hardcode
model version directory names.
"""
from __future__ import annotations

import os
from pathlib import Path


def _current_model_root() -> Path:
    # config/paths.py → config/ → current_model/
    return Path(__file__).resolve().parents[1]


CURRENT_MODEL_ROOT = _current_model_root()
PACKAGE_ROOT = CURRENT_MODEL_ROOT.parent  # Steel-Beam-Estimation/


def resolve_engine_root() -> Path:
    """
    Active estimation engine root (contains Run_PY/, src/, data/).

    Resolution order:
      1. STEEL_ENGINE_ROOT environment variable
      2. current_model itself (packaged layout with Run_PY present)
      3. optional config/engine_root.path (one absolute/relative path line)
      4. fallback to current_model (framework-only until packaging phase)
    """
    env = (os.environ.get("STEEL_ENGINE_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()

    if (CURRENT_MODEL_ROOT / "Run_PY").is_dir():
        return CURRENT_MODEL_ROOT.resolve()

    marker = CURRENT_MODEL_ROOT / "config" / "engine_root.path"
    if marker.exists():
        line = marker.read_text(encoding="utf-8").strip().splitlines()
        if line and line[0].strip() and not line[0].strip().startswith("#"):
            p = Path(line[0].strip())
            if not p.is_absolute():
                p = (CURRENT_MODEL_ROOT / p).resolve()
            return p.resolve()

    return CURRENT_MODEL_ROOT.resolve()


# Runtime directories under current_model/
INPUTS_DIR = CURRENT_MODEL_ROOT / "inputs"
OUTPUTS_DIR = CURRENT_MODEL_ROOT / "outputs"
LOGS_DIR = CURRENT_MODEL_ROOT / "logs"
TEMP_DIR = CURRENT_MODEL_ROOT / "temp"
CONFIG_DIR = CURRENT_MODEL_ROOT / "config"
TEMPLATES_DIR = CURRENT_MODEL_ROOT / "templates"
STATIC_DIR = CURRENT_MODEL_ROOT / "static"
WEBAPP_DIR = CURRENT_MODEL_ROOT / "webapp"

RUNTIME_DIRS = (INPUTS_DIR, OUTPUTS_DIR, LOGS_DIR, TEMP_DIR)


def ensure_runtime_dirs() -> None:
    for d in RUNTIME_DIRS:
        d.mkdir(parents=True, exist_ok=True)
