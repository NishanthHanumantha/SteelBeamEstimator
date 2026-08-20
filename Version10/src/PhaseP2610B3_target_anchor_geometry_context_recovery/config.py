"""
Phase P2.6.10-B.3 — Target Anchor Truth + Geometry-Bounded Context Recovery.
MODEL_VERSION: 10.11.14

Shadow / validation only. Overlay on frozen P2.6.10-B / B.1.
Does not mutate B.2 source. Fourth drawing set only. No Claude Vision.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.14"
PHASE_ID = "P2.6.10-B.3"
PHASE_NAME = "Target Anchor Truth + Geometry-Bounded Context Recovery"
OUTPUT_DIRNAME = "PhaseP2610B3_target_anchor_geometry_context_recovery"
SCOPE = "TARGET_ANCHOR_GEOMETRY_CONTEXT_RECOVERY"
MODE = "SHADOW_VALIDATION"
ENGINEERING_CHANGES = "NONE"

GATE_VERSION = "P2610B3_TARGET_ANCHOR_GEOMETRY_CONTEXT_RECOVERY_V1_0"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"

DRAWING_SET_KEY = "Fourth"
MODE_OFFLINE = "OFFLINE_VALIDATION"

STRESS_BEAMS = (
    ("Fourth", "B141"),
    ("Fourth", "B66"),
    ("Fourth", "B161"),
    ("Fifth", "B128"),
    ("Fifth", "B55"),
    ("Fifth", "B65"),
)

# Reporting / validation identifiers only. Never imported by crop/recovery modules.
REPORT_BLANK_BEAMS = ("B32", "B33", "B34", "B35", "B36", "B37", "B38", "B39")
REPORT_CLIP_BEAMS = ("B19", "B24", "B24A", "B152", "B176")
REPORT_QUALITY_BEAMS = ("B26", "B68A", "B69A", "B70", "B99", "B99A")
REPORT_ALIAS_DISCOVERED = (("B69A", "B69"),)

CLASS_FROZEN = "FROZEN_GOOD"
CLASS_TARGET = "TARGET_RECOVERY"
CLASS_REVIEW = "REVIEW_ONLY"

MAX_CANDIDATES = 3
CONTEXT_PAD_FRAC_MAJOR = 0.14
CONTEXT_PAD_FRAC_MINOR = 0.28
CONTEXT_PAD_MAJOR_MIN_MM = 450.0
CONTEXT_PAD_MAJOR_MAX_MM = 1600.0
CONTEXT_PAD_MINOR_MIN_MM = 280.0
CONTEXT_PAD_MINOR_MAX_MM = 1100.0
DIRECTION_EXTRA_FRAC = 0.18
DIRECTION_EXTRA_MAX_MM = 2200.0
OCCUPANCY_PAD_MM = 320.0
MIN_TARGET_COVERAGE = 0.82
MIN_OCCUPANCY = 0.045
MAX_OCCUPANCY = 0.78
CRUSH_COVERAGE_MAX = 0.42
REPLACE_SCORE_MARGIN = 0.12
ENDPOINT_TOL_MM = 40.0
EXTENT_DUP_MM = 8.0

TRANSLATION_DX_MM = 4000.0
TRANSLATION_DY_MM = -2500.0
TRANSLATION_TOL_MM = 40.0

P2610A_OUTPUT_DIRNAME = "PhaseP2610A_beam_region_crop_audit"
P2610B_OUTPUT_DIRNAME = "PhaseP2610B_adaptive_beam_detail_crop"
P2610B1_OUTPUT_DIRNAME = "PhaseP2610B1_population_generalization"
P2610B2_OUTPUT_DIRNAME = "PhaseP2610B2_render_quality_directional_recovery"
P266_OUTPUT_DIRNAME = "PhaseP266_semantic_longitudinal_resolver"
