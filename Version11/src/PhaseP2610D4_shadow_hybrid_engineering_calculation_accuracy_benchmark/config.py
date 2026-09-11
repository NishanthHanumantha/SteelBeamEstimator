"""
P2.6.10-D.4 — Shadow Hybrid Engineering Calculation & Accuracy Benchmark.
MODEL_VERSION: 10.11.22

SHADOW ONLY. Calculate hybrid steel using existing deterministic engines.
No Claude. No DXF. No production writes. Do not mutate D.1/D.2/D.3.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.22"
PHASE_ID = "P2.6.10-D.4"
PHASE_NAME = "Shadow Hybrid Engineering Calculation & Accuracy Benchmark"
OUTPUT_DIRNAME = "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark"
GATE_VERSION = "P2610D4_SHADOW_HYBRID_ENGINEERING_CALCULATION_ACCURACY_BENCHMARK_V1_0"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"
ENGINEERING_CHANGES = "NONE"
LIVE_CLAUDE_CALL = False

P2610D3_OUTPUT_DIRNAME = "PhaseP2610D3_hybrid_engineering_binding_compatibility"
P2610D2_OUTPUT_DIRNAME = "PhaseP2610D2_shadow_hybrid_semantic_resolver"
P2610D1_OUTPUT_DIRNAME = "PhaseP2610D1_vision_semantic_contract_hybrid_foundation"
P2610B1_OUTPUT_DIRNAME = "PhaseP2610B1_population_generalization"
POPULATION_MANIFEST_NAME = "benchmark_population_manifest.json"
BINDING_RESULTS_NAME = "engineering_binding_results.json"
D3_RESULTS_NAME = "P2.6.10-D.3_RESULTS.json"

STATUS_COMPLETE = "SHADOW_COMPLETE"
STATUS_PARTIAL = "SHADOW_PARTIAL"
STATUS_AMBIGUOUS = "SHADOW_AMBIGUOUS"
STATUS_INCOMPATIBLE = "SHADOW_INCOMPATIBLE"
STATUS_NO_TRUTH = "NO_BENCHMARK_TRUTH"
STATUS_WITHHELD = "CALCULATION_WITHHELD_AMBIGUITY"
STATUS_GROUP_AMBIGUOUS = "SHADOW_ENGINEERING_AMBIGUOUS"
STATUS_CALCULATED = "CALCULATED"

TRUTH_ESTIMATOR = "ESTIMATOR_EXCEL"
TRUTH_NONE = "NONE"
