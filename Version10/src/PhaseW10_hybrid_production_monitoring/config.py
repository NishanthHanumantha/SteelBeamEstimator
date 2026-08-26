"""
P W.10 — Hybrid production monitoring, evidence review, operational metrics.

Read-only over existing W.5/W.6/W.8 artefacts. Never writes Excel, never
mutates VB.1, never logs secrets. Monitoring failure must not fail estimation.
"""
from __future__ import annotations

MODEL_VERSION = "10.0.0"
PHASE_ID = "W.10"
PHASE_NAME = "Hybrid Production Monitoring"
GATE_VERSION = "W10_HYBRID_PRODUCTION_MONITORING_V1"

OUTPUT_DIRNAME = "PhaseW10_hybrid_monitoring"
MONITOR_FILENAME = "hybrid_production_monitor.json"
BEAM_REVIEW_FILENAME = "beam_evidence_reviews.json"

W6_REL = "data/output/PhaseW6_hybrid_semantic_resolution"
W5_REL = "data/output/PhaseW5_production_hybrid_shadow"
EVIDENCE_REL = f"{W6_REL}/hybrid_evidence"
R13_REL = "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"
PRE_HYBRID_REL = (
    "data/output/PhaseR1.3_pipeline_integration/"
    "beam_reinforcement_models_production.pre_hybrid.json"
)
STEEL_REL = "data/output/Production_Output/steel_weight_summary.json"
EXCEL_REL = "data/output/Production_Output/Estimation_Output.xlsx"

# W.10 review labels. Mapped from W.5 comparison.py — not a claim of improvement.
DETERMINISTIC_AGREEMENT = "DETERMINISTIC_AGREEMENT"
SEMANTIC_REINFORCEMENT = "SEMANTIC_REINFORCEMENT"
SEMANTIC_CORRECTION = "SEMANTIC_CORRECTION"
MATERIAL_DISAGREEMENT = "MATERIAL_DISAGREEMENT"
UNAVAILABLE_OR_FALLBACK = "UNAVAILABLE_OR_FALLBACK"

DUP_SAME_IMAGE_ACCEPTABLE = "SAME_IMAGE_ACCEPTABLE"
DUP_COMPATIBILITY_FALLBACK = "COMPATIBILITY_FALLBACK"
DUP_DETAIL_NOT_AVAILABLE = "DETAIL_NOT_AVAILABLE"
DUP_SELECTION_LIMITATION = "SELECTION_LIMITATION"
DUP_RENDERING_GAP = "RENDERING_GAP"
DUP_UNKNOWN = "UNKNOWN"
DUP_NOT_DUPLICATE = "NOT_DUPLICATE"
DUP_HISTORICAL_LIMITED = "HISTORICAL_OBSERVABILITY_LIMITED"

DUP_OUTCOME_RELIABLE = "RELIABLE_RESOLUTION"
DUP_OUTCOME_AMBIGUOUS = "SEMANTIC_AMBIGUITY"
DUP_OUTCOME_FAILURE = "VISION_FAILURE"
DUP_OUTCOME_UNKNOWN = "UNKNOWN"

COST_ACTUAL = "ACTUAL"
COST_ESTIMATED = "ESTIMATED"
COST_UNKNOWN = "UNKNOWN"

NOT_RECORDED = "NOT_RECORDED"
HISTORICAL_LIMITED = "HISTORICAL_OBSERVABILITY_LIMITED"

CROP_DECISION_NO_CHANGE = "NO_CHANGE_REQUIRED"
CROP_DECISION_TARGETED = "TARGETED_IMPROVEMENT"

PROTECTED_KEYS = (
    "cut_length_mm",
    "cut_length_m",
    "spacing_mm",
    "spacing_pattern",
    "stirrup_segments",
    "shape_code",
    "geometry",
)
GEOM_KEYS = ("width_mm", "depth_mm", "span_mm", "clear_span_mm", "length_mm")
