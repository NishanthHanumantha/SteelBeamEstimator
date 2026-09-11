"""
P2.6.10-E.1 — Fifth Set Hybrid Architecture Accuracy Benchmark.
MODEL_VERSION: 10.11.22

BENCHMARK / REPORTING ONLY. Default OFFLINE_REPLAY. No production writes.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.22"
PHASE_ID = "P2.6.10-E.1"
PHASE_NAME = "Fifth Set Hybrid Architecture Accuracy Benchmark & Performance Report"
OUTPUT_DIRNAME = "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark"
GATE_VERSION = "P2610E1_FIFTH_SET_HYBRID_ARCHITECTURE_ACCURACY_BENCHMARK_V1_0"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"
ENGINEERING_CHANGES = "NONE"
LIVE_CLAUDE_CALL = False

MODE_OFFLINE = "OFFLINE_REPLAY"
MODE_LIVE = "LIVE_HYBRID_BENCHMARK"
DEFAULT_MODE = MODE_OFFLINE

P2610D1_OUTPUT_DIRNAME = "PhaseP2610D1_vision_semantic_contract_hybrid_foundation"
P2610D4_OUTPUT_DIRNAME = "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark"
P2610D4_UNIT_MIN = 28

TRUTH_ESTIMATOR = "ESTIMATOR_EXCEL"
TRUTH_NONE = "NONE"

FORMULA_OVERALL = "mean(beam_identification, bar_identification, correct_of_detected, steel_accuracy)"
FORMULA_OVERALL_SOURCE = "PhaseQA.2A_ground_truth_benchmark.report_compiler / QA.3.0 overall_accuracy_docx._overall_of"
FORMULA_STEEL = "max(0, 100 - abs(model_kg - benchmark_kg) / benchmark_kg * 100)"
FORMULA_STEEL_SOURCE = "PhaseQA.2A_ground_truth_benchmark.metrics_engine.MetricsEngine._steel / QA.2A metric8"
FORMULA_BAR_MATCH = "PhaseQA.2A_ground_truth_benchmark.bar_matcher.BarMatcher"
FORMULA_BEAM_MATCH = "PhaseQA.2A_ground_truth_benchmark.beam_matcher.BeamMatcher"
