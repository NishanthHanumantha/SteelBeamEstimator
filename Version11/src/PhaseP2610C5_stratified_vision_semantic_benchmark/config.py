"""
P2.6.10-C.5 — Stratified Vision Semantic Benchmark.
MODEL_VERSION: 10.11.18

SHADOW ONLY. Fourth Set. Max 10 selected beams. No production. No DXF rerender.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.18"
PHASE_ID = "P2.6.10-C.5"
PHASE_NAME = "Stratified Vision Semantic Benchmark"
OUTPUT_DIRNAME = "PhaseP2610C5_stratified_vision_semantic_benchmark"
GATE_VERSION = "P2610C5_STRATIFIED_VISION_SEMANTIC_BENCHMARK_V1_0"
PROMPT_VERSION = "P2610C5_VISION_PROMPT_V1"
SCHEMA_VERSION = "P2610C5_PHYSICAL_GROUP_SCHEMA_V1"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"
ENGINEERING_CHANGES = "NONE"

MODE_OFFLINE = "OFFLINE_VALIDATION"
MODE_LIVE = "LIVE_SHADOW"

TARGET_SAMPLE_SIZE = 10
MAX_SAMPLE_SIZE = 10
MAX_SCHEMA_PARSE_ATTEMPTS = 1

P2610B1_OUTPUT_DIRNAME = "PhaseP2610B1_population_generalization"
P2610C1C2_OUTPUT_DIRNAME = "PhaseP2610C1C2_evidence_inventory_candidate_selection"
P2610C3_OUTPUT_DIRNAME = "PhaseP2610C3_visual_completeness_claude_shadow"
P2610C4_OUTPUT_DIRNAME = "PhaseP2610C4_shadow_truth_reconciliation_benchmark_calibration"
P269_OUTPUT_DIRNAME = "PhaseP269_reinforcement_group_interpretation"
SELECTION_MANIFEST_NAME = "selection_manifest.json"
POPULATION_MANIFEST_NAME = "population_manifest.json"
C3_GATE_MANIFEST_NAME = "visual_completeness_manifest.json"
C3_SIX_BEAM_NAME = "six_beam_benchmark.json"

STATUS_READY = "VISION_READY"
STATUS_LIMITED = "VISION_READY_WITH_LIMITATIONS"
STATUS_REVIEW = "VISION_REVIEW_ONLY"
STATUS_NOT_READY = "VISION_NOT_READY"

STRATA = (
    "SIMPLE_LONGITUDINAL",
    "MULTI_GROUP_LONGITUDINAL",
    "MAIN_EXTRA_COMPLEXITY",
    "SAME_SPEC_DISTINCT_GROUPS",
    "STIRRUP_SEMANTIC_COMPLEXITY",
    "NEIGHBOUR_ASSOCIATION_RISK",
    "LIMITED_RENDER",
    "OTHER_HIGH_INFORMATION_COMPLEXITY",
)

ALLOWED_LAYERS = ("TOP", "BOTTOM", "SIDE_FACE", "OTHER", "UNKNOWN")
ALLOWED_ROLE_HYPOTHESES = ("MAIN", "EXTRA", "UNKNOWN")
ALLOWED_SCOPES = (
    "FULL_SPAN",
    "LEFT_SUPPORT",
    "RIGHT_SUPPORT",
    "BOTH_SUPPORTS",
    "PARTIAL_LEFT",
    "PARTIAL_RIGHT",
    "PARTIAL_SUPPORT",
    "UNKNOWN",
)
ALLOWED_LENGTH = ("LONGER", "SHORTER", "SIMILAR", "UNKNOWN")
FORBIDDEN_CLAUDE_FIELDS = (
    "recover",
    "production_action",
    "steel_quantity",
    "weight",
    "BBS",
    "bbs",
    "cut_length",
    "workbook",
    "estimator_kg",
    "steel_weight",
)
