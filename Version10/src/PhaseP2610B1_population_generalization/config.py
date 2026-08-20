"""
Phase P2.6.10-B.1 — All-Beam Population Generalization & Anti-Hardcoding Validation.
MODEL_VERSION: 10.11.12

Shadow / validation only. Reuses the P2.6.10-B crop engine.
Fourth drawing set only. No Claude Vision. No production mutation.
"""
from __future__ import annotations

MODEL_VERSION = "10.11.12"
PHASE_ID = "P2.6.10-B.1"
PHASE_NAME = "All-Beam Population Generalization & Anti-Hardcoding Validation"
OUTPUT_DIRNAME = "PhaseP2610B1_population_generalization"
SCOPE = "POPULATION_GENERALIZATION_ANTI_HARDCODING"
MODE = "SHADOW_VALIDATION"
ENGINEERING_CHANGES = "NONE"

GATE_VERSION = "P2610B1_POPULATION_GENERALIZATION_ANTI_HARDCODING_V1_0"

PRODUCTION_WRITE = False
SHADOW_ONLY = True
PRODUCTION_ACTION = "NO_CHANGE"

DRAWING_SET_KEY = "Fourth"
MODE_OFFLINE = "OFFLINE_VALIDATION"

# Reporting / regression identifiers only. Not used by crop localization.
STRESS_BEAMS = (
    ("Fourth", "B141"),
    ("Fourth", "B66"),
    ("Fourth", "B161"),
    ("Fifth", "B128"),
    ("Fifth", "B55"),
    ("Fifth", "B65"),
)

P2610A_OUTPUT_DIRNAME = "PhaseP2610A_beam_region_crop_audit"
P2610B_OUTPUT_DIRNAME = "PhaseP2610B_adaptive_beam_detail_crop"
P266_OUTPUT_DIRNAME = "PhaseP266_semantic_longitudinal_resolver"

TRANSLATION_DX_MM = 4000.0
TRANSLATION_DY_MM = -2500.0
TRANSLATION_TOL_MM = 40.0
