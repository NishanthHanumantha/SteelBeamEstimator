"""
Phase P2.5.2.2 — Render-Safe Annotation Bounds.
MODEL_VERSION: 10.6.7

Diagnostic / visual evidence refinement only.
No Claude. No engineering mutations. Candidate set frozen.
"""
from __future__ import annotations

from typing import Tuple

MODEL_VERSION = "10.6.7"
PHASE_ID = "P2.5.2.2"
PHASE_NAME = "Render-Safe Annotation Bounds"
OUTPUT_DIRNAME = "PhaseP2522_render_safe_annotation_bounds"
SCOPE = "FOURTH_SET_ONLY"
MODE = "RENDER_SAFE_VISUAL_REFINEMENT_ONLY"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "NONE"

P2521_OUTPUT = "PhaseP2521_crop_readability_refinement"
P252_OUTPUT = "PhaseP252_vision_candidate_set"
P250_OUTPUT = "PhaseP250_beam_evidence_crop_qa"

PROVENANCE_P2521 = "P2521_REFINED_EVIDENCE"
PROVENANCE_P2522 = "P2522_RENDER_SAFE_EVIDENCE"

CROP_LOCAL_RENDER_SAFE = "local_render_safe"
CROP_BEAM_CONTEXT_RENDER_SAFE = "beam_context_render_safe"

# Pixel safety
MIN_RENDER_SAFE_MARGIN_PX = 24
MAX_RENDER_SAFETY_ITERATIONS = 4
# Extra pixel buffer beyond deficit so we do not oscillate on re-render
EXPAND_BUFFER_PX = 8
# Glyph overrun around mathematical DXF annotation bbox (search region)
GLYPH_OVERRUN_PAD_PX = 28
GLYPH_OVERRUN_PAD_MM = 80.0

# Ink detection (non-background)
BG_LUMA_THRESHOLD = 245

# Extreme / size caps (aligned with P2.5.2.1 / P2.5.0.1)
EXTREME_CROP_HEIGHT_MM = 10000.0
EXTREME_CROP_WIDTH_MM = 50000.0
MAX_REFINED_WIDTH_MM = 9000.0
MAX_REFINED_HEIGHT_MM = 7000.0
MAX_SIDE_EXPAND_MM = 1200.0  # per-iteration hard cap on one side

# Readability
READABILITY_PASS = "READABILITY_PASS"
READABILITY_PARTIAL = "READABILITY_PARTIAL"
READABILITY_FAIL = "READABILITY_FAIL"
READABILITY_REVIEW = "READABILITY_REVIEW"

# Flags
FLAG_ANNOTATION_RENDER_CLIPPED = "ANNOTATION_RENDER_CLIPPED"
FLAG_ANNOTATION_RENDER_EDGE_RISK = "ANNOTATION_RENDER_EDGE_RISK"
FLAG_LEADER_RENDER_EDGE_RISK = "LEADER_RENDER_EDGE_RISK"
FLAG_TOP_ANNOTATION_EDGE_RISK = "TOP_ANNOTATION_EDGE_RISK"
FLAG_BOTTOM_ANNOTATION_EDGE_RISK = "BOTTOM_ANNOTATION_EDGE_RISK"

# Frozen invariants
EXPECTED_VISION_CANDIDATES = 14

GOLDEN_OCR_SAMPLE = r"4L-Y12@\X100C/C"
GOLDEN_B97A_BEAM = "B97A"
GOLDEN_B97A_TEXT = "4-Y25"

BBox = Tuple[float, float, float, float]
