"""
Phase P2.6.10-B.2 — Render Quality & Direction-Aware Adaptive Crop Recovery.
MODEL_VERSION: 10.11.13

Shadow / validation only. Additive wrapper around frozen P2.6.10-B.
Fourth drawing set only. No Claude Vision. No production mutation.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.13"
PHASE_ID = "P2.6.10-B.2"
PHASE_NAME = "Render Quality & Direction-Aware Adaptive Crop Recovery"
OUTPUT_DIRNAME = "PhaseP2610B2_render_quality_directional_recovery"
SCOPE = "RENDER_QUALITY_DIRECTIONAL_RECOVERY"
MODE = "SHADOW_VALIDATION"
ENGINEERING_CHANGES = "NONE"

GATE_VERSION = "P2610B2_RENDER_QUALITY_DIRECTIONAL_RECOVERY_V1_0"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"

DRAWING_SET_KEY = "Fourth"
MODE_OFFLINE = "OFFLINE_VALIDATION"

# Reporting / regression identifiers only. Never imported by recovery/quality/pipeline.
STRESS_BEAMS = (
    ("Fourth", "B141"),
    ("Fourth", "B66"),
    ("Fourth", "B161"),
    ("Fifth", "B128"),
    ("Fifth", "B55"),
    ("Fifth", "B65"),
)

REPORT_BLANK_BEAMS = ("B32", "B33", "B34", "B35", "B36", "B37", "B38", "B39")
REPORT_CLIP_BEAMS = ("B19", "B24", "B24A", "B152", "B176")
REPORT_QUALITY_BEAMS = ("B26", "B68A", "B69A", "B70", "B99", "B99A")

MAX_CONTEXT_ATTEMPTS = 3
MAX_DETAIL_ATTEMPTS = 2
EXPAND_STEP_CONTEXT_MM = 1100.0
EXPAND_STEP_DETAIL_MM = 600.0
TRIM_PAD_MM = 220.0
MAX_EXPAND_FACTOR = 1.85
MAX_CONTEXT_WIDTH_MM = 14000.0
MAX_CONTEXT_HEIGHT_MM = 10000.0
MAX_DETAIL_WIDTH_MM = 8200.0
MAX_DETAIL_HEIGHT_MM = 6800.0
MIN_WIDTH_MM = 900.0
MIN_HEIGHT_MM = 700.0
DETAIL_INSET_FRAC = 0.06

EMPTY_FOREGROUND_MAX = 0.004
BLACK_DARK_MIN = 0.82
LOW_INFO_FOREGROUND_MAX = 0.028
BORDER_BAND_FRAC = 0.035
MEANINGFUL_BORDER_FRAC = 0.012
LOW_CONTEXT_COVERAGE_MAX = 0.55

TRANSLATION_DX_MM = 4000.0
TRANSLATION_DY_MM = -2500.0
TRANSLATION_TOL_MM = 40.0

P2610A_OUTPUT_DIRNAME = "PhaseP2610A_beam_region_crop_audit"
P2610B_OUTPUT_DIRNAME = "PhaseP2610B_adaptive_beam_detail_crop"
P2610B1_OUTPUT_DIRNAME = "PhaseP2610B1_population_generalization"
P266_OUTPUT_DIRNAME = "PhaseP266_semantic_longitudinal_resolver"
