"""
Flask web application configuration — Version10 adapter (Phase W.2).

Application/release label is independent of engineering MODEL_VERSION.
Do not display 8.9.5 as the active engine. Engineering constants are untouched.
"""
from __future__ import annotations

import os
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = WEBAPP_ROOT.parent
# Historical alias used by older web copies; always Version10 in this tree.
V8_ROOT = ENGINE_ROOT
REPO_ROOT = ENGINE_ROOT.parent

APP_RELEASE = "W.19"
ENGINE_LABEL = "Version10"
ENGINE_DISPLAY = "Version10 production pipeline"

UPLOAD_ROOT = WEBAPP_ROOT / "uploads"
OUTPUT_ROOT = WEBAPP_ROOT / "outputs"
LOG_ROOT = WEBAPP_ROOT / "logs"
WEB_RUNS_ROOT = ENGINE_ROOT / "data" / "web_runs"

MAX_CONTENT_LENGTH = int(os.environ.get("STEEL_WEB_MAX_UPLOAD_MB", "256")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".dxf"}
MIN_DXF_BYTES = 32
SECRET_KEY = os.environ.get("STEEL_WEB_SECRET_KEY", "steel-beam-estimation-ui1-dev")

BUSY_MESSAGE = (
    "An estimation is currently running. Please wait and try again."
)

# Canonical Version10 estimator Excel path (QA.2 web stages minus T16CHAIN).
# T16CHAIN is a post-Excel visual/QA chain, not required for workbook download.
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
        "id": "T1",
        "label": "Running geometric stirrup evidence...",
        "script": "Run_PY/run_phase_t1_geometric_stirrup_evidence.py",
        "uses_input_folder": False,
        "timeout_s": 1200,
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
        "id": "HYBRID",
        "label": "Resolving reinforcement semantics...",
        "script": "Run_PY/run_phase_w6_hybrid_production_authority.py",
        "uses_input_folder": False,
        "timeout_s": 7200,
    },
    {
        "id": "VB1",
        "label": "Generating estimation workbook...",
        "script": "Run_PY/run_phase_vb1_production_output_completion.py",
        "uses_input_folder": False,
        "timeout_s": 900,
    },
]

PRODUCTION_EXCEL = ENGINE_ROOT / "data" / "output" / "Production_Output" / "Estimation_Output.xlsx"

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
T1_EVIDENCE_REL = (
    "data/output/PhaseT1_geometric_stirrup_evidence/stirrup_geometry_evidence.json"
)
VB1_EXCEL_REL = "data/output/Production_Output/Estimation_Output.xlsx"
STEEL_SUMMARY_REL = "data/output/Production_Output/steel_weight_summary.json"
ENGINEERING_TOTALS_REL = "data/output/Production_Output/engineering_totals.json"

W6_OBSERVABILITY_REL = (
    "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_observability.json"
)
W6_RESOLUTION_REL = (
    "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_resolution.json"
)
W11_PROGRESS_REL = (
    "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_progress.json"
)

SOFT_ARTEFACTS = {
    "R3": R3_CONTEXTS_REL,
    "R31": R31_RELS_REL,
    "R12A": R12A_CATALOG_REL,
    "R13": R13_MODELS_REL,
    "HYBRID": W6_OBSERVABILITY_REL,
    "VB1": VB1_EXCEL_REL,
    "L22": L22_REGISTRY_REL,
    "R21D": R21D_FACTS_REL,
    "R21C": R21C_FACTS_REL,
    "R21B": (
        "data/output/PhaseR2.1B_engineering_semantic_interpreter/"
        "engineering_semantic_objects.json"
    ),
    "T1": T1_EVIDENCE_REL,
}

R2A_GN_POINTER = (
    ENGINE_ROOT / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
)

GN_POINTER_SOURCE = "UI.1_WEBAPP_POINTER"


def t1_is_configured() -> bool:
    return any(stage["id"] == "T1" for stage in PRODUCTION_STAGES)


def t1_runner_path() -> Path:
    return ENGINE_ROOT / "Run_PY" / "run_phase_t1_geometric_stirrup_evidence.py"


HYBRID_OUTPUT_REL = "data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json"


def hybrid_stage_configured() -> bool:
    return any(stage["id"] == "HYBRID" for stage in PRODUCTION_STAGES)
