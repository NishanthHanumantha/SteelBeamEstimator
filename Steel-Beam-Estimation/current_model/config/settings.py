"""
Central application settings (Phase D.3).

All runtime configuration is loaded from environment + model_info.yaml.
No secrets or machine-specific paths are hardcoded.
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

from config.paths import (
    CONFIG_DIR,
    CURRENT_MODEL_ROOT,
    INPUTS_DIR,
    LOGS_DIR,
    OUTPUTS_DIR,
    TEMP_DIR,
    UPLOADS_DIR,
    ensure_runtime_dirs,
    resolve_engine_root,
)

load_dotenv(CURRENT_MODEL_ROOT / ".env", override=False)

_log = logging.getLogger("steel_beam.config")


def _load_model_info() -> Dict[str, Any]:
    path = CONFIG_DIR / "model_info.yaml"
    if not path.exists():
        return {
            "project_name": "Steel Beam Reinforcement Estimation",
            "model_name": "Steel Beam Estimation Engine",
            "model_version": "unknown",
            "release_date": "",
            "author": "",
            "description": "",
        }
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def _resolve_secret_key(flask_env: str) -> str:
    key = (os.environ.get("SECRET_KEY") or os.environ.get("STEEL_WEB_SECRET_KEY") or "").strip()
    if key:
        return key
    if flask_env == "production":
        raise RuntimeError(
            "SECRET_KEY must be set in the environment for production. "
            "Copy .env.example to .env and set a strong SECRET_KEY."
        )
    # Development-only ephemeral key (not for production)
    return secrets.token_hex(32)


MODEL_INFO = _load_model_info()
MODEL_VERSION = str(MODEL_INFO.get("model_version") or "unknown")

# ── Folders (absolute; under current_model/) ─────────────────────────────────
# Upload audit copies live under uploads/ (parity with Version8/webapp/uploads).
# VROOT1 staging lives under ENGINE_ROOT/data/web_runs — never current_model/data.
UPLOAD_FOLDER = UPLOADS_DIR
OUTPUT_FOLDER = OUTPUTS_DIR
TEMP_FOLDER = TEMP_DIR
LOG_FOLDER = LOGS_DIR
INPUTS_FOLDER = INPUTS_DIR

# ── Flask / security ─────────────────────────────────────────────────────────
FLASK_ENV = (os.environ.get("FLASK_ENV") or "development").strip().lower()
SECRET_KEY = _resolve_secret_key(FLASK_ENV)
HOST = os.environ.get("STEEL_BEAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("STEEL_BEAM_PORT", "5000"))

MAX_UPLOAD_MB = int(
    os.environ.get("MAX_UPLOAD_MB")
    or os.environ.get("STEEL_WEB_MAX_UPLOAD_MB", "256")
)
MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".dxf"}

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Engine (version-agnostic) ────────────────────────────────────────────────
ENGINE_ROOT = resolve_engine_root()
WEB_RUNS_ROOT = ENGINE_ROOT / "data" / "web_runs"
KEEP_WEB_RUNS = (os.environ.get("STEEL_KEEP_WEB_RUNS") or "").strip().lower() in {
    "1",
    "true",
    "yes",
}
PRODUCTION_EXCEL = (
    ENGINE_ROOT / "data" / "output" / "Production_Output" / "Estimation_Output.xlsx"
)

# Same layout as Version8/webapp/config.py:
#   V8_ROOT.parent / "Version7"  (monorepo sibling of the engine)
V7_ROOT = ENGINE_ROOT.parent / "Version7"

_seed = (os.environ.get("STEEL_ARTEFACT_SEED_ROOT") or "").strip()
ARTEFACT_SEED_ROOT: Optional[Path] = (
    Path(_seed).expanduser().resolve() if _seed else None
)

R2A_GN_POINTER = (
    ENGINE_ROOT
    / "src"
    / "PhaseVROOT.1_dynamic_pipeline_initialization"
    / "beam_registry.json"
)

# D.5.1–D.5.3 success artefacts (per-run tree under web_runs/<run_id>/)
R21C_FACTS_REL = (
    "data/output/PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json"
)
R21D_FACTS_REL = (
    "data/output/PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json"
)
L22_REGISTRY_REL = (
    "data/output/PhaseL.2.2_geometry_recovery/geometry_registry.json"
)

# D.5.3 production pipeline — stops after Geometry Registry (L.2.2).
# R.3 / Excel deferred.
PRODUCTION_STAGES: List[Dict[str, Any]] = [
    {
        "id": "VROOT1",
        "label": "Preparing estimation...",
        "script": "Run_PY/run_phase_vroot1_dynamic_pipeline_initialization.py",
        "uses_input_folder": True,
        "timeout_s": 300,
    },
    {
        "id": "R1",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r1_generalized_reinforcement_discovery.py",
        "uses_input_folder": False,
        "timeout_s": 900,
    },
    {
        "id": "R2A",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r2a_engineering_context.py",
        "uses_input_folder": False,
        "timeout_s": 300,
    },
    {
        "id": "R21B",
        "label": "Running engineering semantic engine...",
        "script": "Run_PY/run_phase_r21b_semantic_interpreter.py",
        "uses_input_folder": False,
        "timeout_s": 900,
    },
    {
        "id": "R21C",
        "label": "Normalizing engineering facts...",
        "script": "Run_PY/run_phase_r21c_engineering_fact_normalization.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "R21D",
        "label": "Building evidence and hypotheses...",
        "script": "Run_PY/run_phase_r21d_evidence_hypothesis_engine.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "L22",
        "label": "Building geometry registry...",
        "script": "Run_PY/run_phase_l2_2_geometry_recovery.py",
        "uses_input_folder": False,
        "timeout_s": 300,
    },
]


def engine_is_ready() -> bool:
    return (ENGINE_ROOT / "Run_PY").is_dir()


def ezdxf_is_available() -> bool:
    try:
        import ezdxf  # noqa: F401

        return True
    except ImportError:
        return False


def apply_flask_config(app) -> None:
    """Push settings into a Flask app instance."""
    ensure_runtime_dirs()
    WEB_RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["MODEL_VERSION"] = MODEL_VERSION
    app.config["MODEL_INFO"] = MODEL_INFO
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER.resolve())
    app.config["OUTPUT_FOLDER"] = str(OUTPUT_FOLDER.resolve())
    app.config["TEMP_FOLDER"] = str(TEMP_FOLDER.resolve())
    app.config["LOG_FOLDER"] = str(LOG_FOLDER.resolve())
    app.config["ENGINE_ROOT"] = str(ENGINE_ROOT.resolve())
    app.config["WEB_RUNS_ROOT"] = str(WEB_RUNS_ROOT.resolve())
    app.config["FLASK_ENV"] = FLASK_ENV
    app.config["ENGINE_READY"] = engine_is_ready()
    app.config["EZDXF_AVAILABLE"] = ezdxf_is_available()
    if engine_is_ready() and not ezdxf_is_available():
        _log.warning(
            "Engine is ready at %s but ezdxf is not installed in this venv. "
            "VROOT1 will report 0 text entities / 0 beams. "
            "Install Version8/requirements.txt into the application virtualenv.",
            ENGINE_ROOT,
        )
