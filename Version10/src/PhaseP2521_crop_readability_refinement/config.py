"""
Phase P2.5.2.1 — Crop Readability Refinement.
MODEL_VERSION: 10.6.6

Visual evidence refinement only. No Claude. No engineering mutations.
Candidate selection remains frozen from P2.5.2.
"""
from __future__ import annotations

from typing import Tuple

MODEL_VERSION = "10.6.6"
PHASE_ID = "P2.5.2.1"
PHASE_NAME = "Crop Readability Refinement"
OUTPUT_DIRNAME = "PhaseP2521_crop_readability_refinement"
SCOPE = "FOURTH_SET_ONLY"
MODE = "VISUAL_EVIDENCE_REFINEMENT_ONLY"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "NONE"

P252_OUTPUT = "PhaseP252_vision_candidate_set"
P250_OUTPUT = "PhaseP250_beam_evidence_crop_qa"
P251_OUTPUT = "PhaseP251_quantity_intent_schema"

# Provenance labels
PROVENANCE_P250 = "ORIGINAL_P250_EVIDENCE"
PROVENANCE_P252 = "P252_EVIDENCE"
PROVENANCE_P2521 = "P2521_REFINED_EVIDENCE"

# Crop types
CROP_LOCAL_REFINED = "local_refined"
CROP_BEAM_CONTEXT_REFINED = "beam_context_refined"
CROP_LOCAL_ORIGINAL = "local_original_p252"
CROP_BEAM_CONTEXT_ORIGINAL = "beam_context_original_p252"

# Readability QA
READABILITY_PASS = "READABILITY_PASS"
READABILITY_PARTIAL = "READABILITY_PARTIAL"
READABILITY_FAIL = "READABILITY_FAIL"
READABILITY_REVIEW_REQUIRED = "READABILITY_REVIEW_REQUIRED"

# Extreme crop safety (aligned with P2.5.2 / P2.5.0.1)
EXTREME_CROP_HEIGHT_MM = 10000.0
EXTREME_CROP_WIDTH_MM = 50000.0

# Padding around evidence unions (mm) — derived from P250 EVIDENCE_PAD / BASE_MARGIN family
LOCAL_PAD_MM = 180.0
LOCAL_PAD_RELAXED_MM = 280.0
CONTEXT_PAD_MM = 320.0
CONTEXT_PAD_RELAXED_MM = 450.0

# Local beam snippet half-span around annotation (mm)
LOCAL_BEAM_HALF_SPAN_MM = 1600.0
# Medium context half-span cap around annotation when full beam is very long (mm)
CONTEXT_BEAM_HALF_SPAN_MM = 3200.0
# Absolute caps for refined crops (below extreme thresholds)
MAX_REFINED_WIDTH_MM = 9000.0
MAX_REFINED_HEIGHT_MM = 7000.0
MIN_REFINED_WIDTH_MM = 900.0
MIN_REFINED_HEIGHT_MM = 700.0

# Occupancy / whitespace readability thresholds (deterministic geometric heuristics)
MIN_ANNOTATION_OCCUPANCY_PASS = 0.008  # 0.8%
MIN_ANNOTATION_OCCUPANCY_PARTIAL = 0.003  # 0.3%
MIN_EVIDENCE_OCCUPANCY_PASS = 0.012
MIN_EVIDENCE_OCCUPANCY_PARTIAL = 0.005
MIN_BEAM_OCCUPANCY_PASS = 0.08
MIN_BEAM_OCCUPANCY_PARTIAL = 0.03
MAX_WHITESPACE_RATIO_PASS = 0.82
MAX_WHITESPACE_RATIO_PARTIAL = 0.92
MIN_ASPECT = 0.20
MAX_ASPECT = 5.0

# Iteration hard-cap
MAX_REFINEMENT_ITERS = 4

# Frozen candidate-count invariants from P2.5.2
EXPECTED_VISION_CANDIDATES = 14
EXPECTED_DEFERRED = 16
EXPECTED_EXCLUDED = 293
EXPECTED_ELIGIBLE = 323
EXPECTED_UNRESOLVED = 30
EXPECTED_OCR = 25

# Golden texts (must not change classification)
GOLDEN_OCR_SAMPLE = r"4L-Y12@\X100C/C"
GOLDEN_DEV_NOTE = "Ld"
GOLDEN_SFR_NOTE = "S.F.R.ON EACH FACE"
GOLDEN_B97A_TEXT = "4-Y25"
GOLDEN_B97A_BEAM = "B97A"
GOLDEN_B97A_ANN = "ANN-d7128f62"

BBox = Tuple[float, float, float, float]
