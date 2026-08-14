"""
Phase P2.5.8 — Controlled Vision Field-Repair & Engineering Recompute.
MODEL_VERSION: 10.8.4

Whitelisted Vision field repairs enter an isolated shadow recompute of the
existing deterministic SI.1 / VB.1 engineering path. Production is untouched.
Claude remains interpretation-only. Maximum promotion level: CONTROLLED_RECOMPUTE.
"""
from __future__ import annotations

MODEL_VERSION = "10.8.4"
PHASE_ID = "P2.5.8"
PHASE_NAME = "Controlled Vision Field-Repair & Engineering Recompute"
OUTPUT_DIRNAME = "PhaseP258_controlled_vision_field_repair"
SCOPE = "FIFTH_SET_PRIMARY"
MODE = "REPLAY_P257_LIVE_RESULTS"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "SHADOW_OBSERVER"
MAX_PROMOTION_LEVEL = "CONTROLLED_RECOMPUTE"
PRODUCTION_WRITE = False
ZONE_PROMOTABLE = False

P257_OUTPUT = "PhaseP257_unseen_drawing_controlled_vision_validation"
PRIMARY_DRAWING_SET = "Fifth Set Drawings"
PRIMARY_SET_KEY = "Fifth"

LEVEL_SHADOW_ONLY = "SHADOW_ONLY"
LEVEL_CONTROLLED_RECOMPUTE = "CONTROLLED_RECOMPUTE"
LEVEL_BLOCKED = "BLOCKED"
LEVEL_PRODUCTION_INELIGIBLE = "PRODUCTION_INELIGIBLE"

DET_UNKNOWN = "DETERMINISTIC_UNKNOWN"
DET_PARTIAL = "DETERMINISTIC_PARTIAL"
DET_CONFIRMED = "DETERMINISTIC_CONFIRMED"

DEC_PROMOTE = "CONTROLLED_RECOMPUTE"
DEC_BLOCK = "BLOCKED"
DEC_INELIGIBLE = "PRODUCTION_INELIGIBLE"

WHITELIST_FIELDS = ("diameter", "legs", "spacing")
FORBIDDEN_FIELDS = (
    "quantity",
    "zone",
    "cut_length",
    "development_length",
    "hooks",
    "curtailment",
    "continuity",
)

PROMPT_VERSION = "P254_SEMANTIC_VISION_PROMPT_V1"
SCHEMA_VERSION = "P254_SEMANTIC_INTERPRETATION_SCHEMA_V1"
