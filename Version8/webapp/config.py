"""
Phase UI.1 — Flask web application configuration.
MODEL_VERSION: 8.8.3
"""
from __future__ import annotations

import os
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parent
V8_ROOT = WEBAPP_ROOT.parent
REPO_ROOT = V8_ROOT.parent
V7_ROOT = REPO_ROOT / "Version7"

# Uploads / outputs / logs live under webapp (not engineering data/output)
UPLOAD_ROOT = WEBAPP_ROOT / "uploads"
OUTPUT_ROOT = WEBAPP_ROOT / "outputs"
LOG_ROOT = WEBAPP_ROOT / "logs"

# Staging folders consumed by V.ROOT.1 (standard Benchmark_Set layout)
WEB_RUNS_ROOT = V8_ROOT / "data" / "web_runs"

MAX_CONTENT_LENGTH = int(os.environ.get("STEEL_WEB_MAX_UPLOAD_MB", "256")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".dxf"}
SECRET_KEY = os.environ.get("STEEL_WEB_SECRET_KEY", "steel-beam-estimation-ui1-dev")

# Production pipeline through V.B.1 Excel.
# R.1 must run before R.3 (annotations are an R.3 input).
# R.2.0–R.2.1D are not invoked here yet: those runners still hardcode legacy
# Benchmark_Set_2 paths. EngineeringFacts + geometry_registry are ensured by
# the webapp from prior Version7/Version8 artefacts when missing.
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
        "id": "R3",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r3_geometry_context_engine.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "R31",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r31_engineering_relationship_engine.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "R12A",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r12a_geometry_accuracy.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "R12C",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r12c_engineering_intent_resolution.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "R12D",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r12d_reinforcement_detailing.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "R13",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r13_reinforcement_piece_generation.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "R13PI",
        "label": "Running engineering pipeline...",
        "script": "Run_PY/run_phase_r13_pipeline_integration.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "VB1",
        "label": "Generating workbook...",
        "script": "Run_PY/run_phase_vb1_production_output_completion.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
]

PRODUCTION_EXCEL = V8_ROOT / "data" / "output" / "Production_Output" / "Estimation_Output.xlsx"

# Path used by existing R.2A factory discovery (do not change engineering code).
R2A_GN_POINTER = (
    V8_ROOT / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
)

# R.3 prerequisite artefacts (seeded from Version7 when absent in Version8).
R3_PREREQUISITES = [
    {
        "rel": "data/output/PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json",
        "label": "EngineeringFacts.json (R.2.1D)",
    },
    {
        "rel": "data/output/PhaseL.2.2_geometry_recovery/geometry_registry.json",
        "label": "geometry_registry.json (L.2.2)",
    },
]
