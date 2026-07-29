"""
Flask web application configuration — Version9 accuracy branch.
MODEL_VERSION: 8.9.5 (baseline from Version8 freeze)
"""
from __future__ import annotations

import os
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parent
# Engine root (historically named V8_ROOT; parent is Version9/)
V8_ROOT = WEBAPP_ROOT.parent
ENGINE_ROOT = V8_ROOT
REPO_ROOT = V8_ROOT.parent

# Uploads / outputs / logs live under webapp (not engineering data/output)
UPLOAD_ROOT = WEBAPP_ROOT / "uploads"
OUTPUT_ROOT = WEBAPP_ROOT / "outputs"
LOG_ROOT = WEBAPP_ROOT / "logs"

# Per-run staging + artefacts
WEB_RUNS_ROOT = V8_ROOT / "data" / "web_runs"

MAX_CONTENT_LENGTH = int(os.environ.get("STEEL_WEB_MAX_UPLOAD_MB", "256")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".dxf"}
SECRET_KEY = os.environ.get("STEEL_WEB_SECRET_KEY", "steel-beam-estimation-ui1-dev")

# Production pipeline — upload through Excel (VB.1).
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
    {
        "id": "L22",
        "label": "Building geometry registry...",
        "script": "Run_PY/run_phase_l2_2_geometry_recovery.py",
        "uses_input_folder": False,
        "timeout_s": 300,
    },
    {
        "id": "R3",
        "label": "Building geometry context...",
        "script": "Run_PY/run_phase_r3_geometry_context_engine.py",
        "uses_input_folder": False,
        "timeout_s": 900,
    },
    {
        "id": "R31",
        "label": "Building drawing relationships...",
        "script": "Run_PY/run_phase_r31_engineering_relationship_engine.py",
        "uses_input_folder": False,
        "timeout_s": 900,
    },
    {
        "id": "R12A",
        "label": "Resolving beam geometry...",
        "script": "Run_PY/run_phase_r12a_geometry_accuracy.py",
        "uses_input_folder": False,
        "timeout_s": 600,
    },
    {
        "id": "R13",
        "label": "Integrating reinforcement models...",
        "script": "Run_PY/run_phase_r13_pipeline_integration.py",
        "uses_input_folder": False,
        "timeout_s": 1200,
    },
    {
        "id": "VB1",
        "label": "Generating estimation workbook...",
        "script": "Run_PY/run_phase_vb1_production_output_completion.py",
        "uses_input_folder": False,
        "timeout_s": 900,
    },
]

# Offline/shared Excel path only — web uses VB1_EXCEL_REL under the run tree.
PRODUCTION_EXCEL = V8_ROOT / "data" / "output" / "Production_Output" / "Estimation_Output.xlsx"

R21C_FACTS_REL = (
    "data/output/PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json"
)
R21D_FACTS_REL = (
    "data/output/PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json"
)
L22_REGISTRY_REL = (
    "data/output/PhaseL.2.2_geometry_recovery/geometry_registry.json"
)
R3_CONTEXTS_REL = (
    "data/output/PhaseR3_geometry_context_engine/GeometryContexts.json"
)
R31_RELS_REL = (
    "data/output/PhaseR3.1_engineering_relationship_engine/"
    "EngineeringDrawingRelationships.json"
)
R12A_CATALOG_REL = (
    "data/output/PhaseR1_2A_geometry_accuracy/validated_beam_geometry.json"
)
R13_MODELS_REL = (
    "data/output/PhaseR1.3_pipeline_integration/"
    "beam_reinforcement_models_production.json"
)
VB1_EXCEL_REL = "data/output/Production_Output/Estimation_Output.xlsx"

# Path used by existing R.2A factory discovery (do not change engineering code).
R2A_GN_POINTER = (
    V8_ROOT / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
)
