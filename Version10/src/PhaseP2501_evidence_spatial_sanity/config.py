"""
Phase P2.5.0.1 — Evidence Spatial Sanity Diagnostic.
MODEL_VERSION: 10.6.1
DIAGNOSTIC ONLY — no Claude, no engineering/ownership mutations.
"""
from __future__ import annotations

MODEL_VERSION = "10.6.1"
PHASE_ID = "P2.5.0.1"
PHASE_NAME = "Evidence Spatial Sanity Diagnostic"
OUTPUT_DIRNAME = "PhaseP2501_evidence_spatial_sanity"
SCOPE = "FOURTH_SET_ONLY"
MODE = "DIAGNOSTIC_ONLY"
ENGINEERING_CHANGES = "NONE"

# Focus beams for deep traces
FOCUS_BEAMS = ("B97A", "B98A")
# Known-good visual comparisons (P2.5.0 PASS, readable crops)
KNOWN_GOOD_BEAMS = ("B14", "B60")

# Diagnostic crop-health bands (measurement only — not hard gates)
EXTREME_CROP_HEIGHT_RATIO = 8.0
EXTREME_CROP_AREA_RATIO = 40.0
EXTREME_Y_GAP_MM = 5000.0

ROOT_CAUSE_LABELS = (
    "COORDINATE_SPACE_MISMATCH",
    "UNIT_MISMATCH",
    "TRANSFORM_ERROR",
    "OWNERSHIP_ERROR",
    "SOURCE_GEOMETRY_ERROR",
    "EVIDENCE_EXPANSION_ERROR",
    "LEADER_EXPANSION_ERROR",
    "LEGITIMATE_LARGE_CONTEXT",
    "UNKNOWN_REQUIRES_REVIEW",
)
