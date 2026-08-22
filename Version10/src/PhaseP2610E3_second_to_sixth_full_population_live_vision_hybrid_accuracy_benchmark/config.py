"""
P2.6.10-E.3 — Second-to-Sixth Full-Population Live Vision Hybrid Accuracy Benchmark.
MODEL_VERSION: 10.11.24

SHADOW ONLY. Default OFFLINE_VALIDATION. Live Claude only in LIVE_BENCHMARK.
Does not promote the hybrid architecture into production.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.24"
PHASE_ID = "P2.6.10-E.3"
PHASE_NAME = "Second-to-Sixth Set Full-Population Live Vision Hybrid Accuracy Benchmark & Performance Report"
OUTPUT_DIRNAME = "PhaseP2610E3_second_to_sixth_full_population_live_vision_hybrid_accuracy_benchmark"
GATE_VERSION = "P2610E3_SECOND_TO_SIXTH_FULL_POPULATION_LIVE_VISION_HYBRID_ACCURACY_BENCHMARK_AND_REPORT_V1_0"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"
ENGINEERING_CHANGES = "NONE"
LIVE_CLAUDE_CALL = True

MODE_OFFLINE = "OFFLINE_VALIDATION"
MODE_LIVE = "LIVE_BENCHMARK"
DEFAULT_MODE = MODE_OFFLINE

MAX_API_ATTEMPTS = 2
MAX_SCHEMA_PARSE_ATTEMPTS = 1
MIN_RENDER_BYTES = 200

STATUS_READY = "VISION_READY"
STATUS_LIMITED = "VISION_READY_WITH_LIMITATIONS"
STATUS_NOT_READY = "VISION_NOT_READY"
STATUS_REVIEW = "VISION_REVIEW_ONLY"

PROV_REUSED = "VISION_REUSED_CURRENT_ARCHITECTURE"
PROV_RETRIED = "VISION_RETRIED_AFTER_HISTORICAL_FAILURE"
PROV_NEW = "VISION_NEW_LIVE_CALL"
PROV_NOT_AVAILABLE = "VISION_NOT_AVAILABLE"
PROV_API_FAILED = "VISION_API_FAILED"
PROV_SCHEMA_FAILED = "VISION_SCHEMA_FAILED"
PROV_UNUSABLE = "VISION_SEMANTIC_UNUSABLE"
PROV_FALLBACK = "DETERMINISTIC_FALLBACK"

KIND_HYBRID = "HYBRID"
KIND_FALLBACK = "FALLBACK"

INCLUDED_SET_KEYS = ("Second", "Third", "Fourth", "Fifth", "Sixth")
EXCLUDED_SET_KEYS = ("First",)

SET_TOKENS = {
    "First": ("first", "1st"),
    "Second": ("second", "2nd"),
    "Third": ("third", "3rd"),
    "Fourth": ("fourth", "4th"),
    "Fifth": ("fifth", "5th"),
    "Sixth": ("sixth", "6th"),
}

P2610E2_OUTPUT_DIRNAME = "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark"
P2610E1_OUTPUT_DIRNAME = "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark"
QA30_DIRNAME = "PhaseQA30_unseen_benchmark"
FIFTH_SET_KEY = "Fifth"

DOCX_NAME = "Steel_Beam_Estimation_Current_Hybrid_Performance_Report_Second_to_Sixth_Sets.docx"
PDF_NAME = "Steel_Beam_Estimation_Current_Hybrid_Performance_Report_Second_to_Sixth_Sets.pdf"

TRUTH_ESTIMATOR = "ESTIMATOR_EXCEL"
TRUTH_VALIDATED = "VALIDATED_BENCHMARK"
TRUTH_NONE = "NONE"

FORMULA_STEEL = "max(0, 100 - abs(model_kg - benchmark_kg) / benchmark_kg * 100)"
FORMULA_STEEL_SOURCE = "PhaseQA.2A_ground_truth_benchmark.metrics_engine.MetricsEngine._steel / QA.2A metric8"
FORMULA_OVERALL = "mean(beam_identification, bar_identification, correct_of_detected, weight_accuracy)"
FORMULA_OVERALL_SOURCE = "QA.3.0 four-KPI mean; diameter excluded"
