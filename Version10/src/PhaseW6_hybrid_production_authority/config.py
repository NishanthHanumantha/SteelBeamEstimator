"""
P W.6 — Hybrid Production Authority Integration.

Promotes the validated W.5 Hybrid path into the Version10 production
pipeline as the semantic authority. Deterministic engineering remains
the sole authority for geometry, cut length, DL, hooks, pieces, weight,
BBS, and Excel.
"""
from __future__ import annotations

MODEL_VERSION = "10.0.0"
PHASE_ID = "W.6"
PHASE_NAME = "Hybrid Production Authority Integration"
OUTPUT_DIRNAME = "PhaseW6_hybrid_semantic_resolution"
GATE_VERSION = "W6_HYBRID_PRODUCTION_AUTHORITY_V1"

PRE_HYBRID_FILENAME = "beam_reinforcement_models_production.pre_hybrid.json"
RESOLUTION_FILENAME = "hybrid_resolution.json"
OBSERVABILITY_FILENAME = "hybrid_observability.json"
HANDOFF_LEDGER_FILENAME = "hybrid_handoff_ledger.json"
COVERAGE_FILENAME = "hybrid_coverage.json"

R13_REL = "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"
R13_DIR_REL = "data/output/PhaseR1.3_pipeline_integration"

CLASS_SUCCESS = "HYBRID_SUCCESS"
CLASS_UNAVAILABLE = "HYBRID_UNAVAILABLE"
CLASS_TIMEOUT = "HYBRID_TIMEOUT"
CLASS_API_ERROR = "HYBRID_API_ERROR"
CLASS_RESOLUTION_ERROR = "HYBRID_RESOLUTION_ERROR"
CLASS_FALLBACK = "HYBRID_FALLBACK_USED"
CLASS_SKIPPED = "HYBRID_SKIPPED_OFF"

PROTECTED_BAR_KEYS = (
    "cut_length_mm",
    "cut_length_m",
    "spacing_mm",
    "spacing_pattern",
    "stirrup_segments",
    "shape_code",
    "geometry",
)

LONGITUDINAL_BUCKETS = (
    "top_main_bars",
    "top_extra_bars",
    "bottom_main_bars",
    "bottom_extra_bars",
    "side_face_reinforcement",
)
STIRRUP_BUCKET = "stirrups"
SPACER_BUCKET = "spacer_bars"
ALL_BAR_BUCKETS = LONGITUDINAL_BUCKETS + (STIRRUP_BUCKET, SPACER_BUCKET, "supplementary_bars")

VISION_SEMANTIC_FIELDS = (
    "quantity",
    "diameter_mm",
    "bar_label",
    "semantic_role",
    "support_zone",
    "extent",
)
