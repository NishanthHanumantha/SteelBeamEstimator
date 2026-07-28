"""
Phase UI.1 / D.5.2 — Flask web application configuration.
MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

import os
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parent
V8_ROOT = WEBAPP_ROOT.parent
REPO_ROOT = V8_ROOT.parent

# Uploads / outputs / logs live under webapp (not engineering data/output)
UPLOAD_ROOT = WEBAPP_ROOT / "uploads"
OUTPUT_ROOT = WEBAPP_ROOT / "outputs"
LOG_ROOT = WEBAPP_ROOT / "logs"

# Per-run staging + artefacts (Phase D.5.1+)
WEB_RUNS_ROOT = V8_ROOT / "data" / "web_runs"

MAX_CONTENT_LENGTH = int(os.environ.get("STEEL_WEB_MAX_UPLOAD_MB", "256")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".dxf"}
SECRET_KEY = os.environ.get("STEEL_WEB_SECRET_KEY", "steel-beam-estimation-ui1-dev")

# D.5.2 production pipeline — Evidence & Hypothesis Engine (stops after R.2.1D).
# L.2.2 / R.3 / Excel deferred to later milestones.
PRODUCTION_STAGES = [
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
]

# Excel deferred until later phases re-enable VB.1
PRODUCTION_EXCEL = V8_ROOT / "data" / "output" / "Production_Output" / "Estimation_Output.xlsx"

R21C_FACTS_REL = (
    "data/output/PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json"
)
R21D_FACTS_REL = (
    "data/output/PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json"
)

# Path used by existing R.2A factory discovery (do not change engineering code).
R2A_GN_POINTER = (
    V8_ROOT / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
)
