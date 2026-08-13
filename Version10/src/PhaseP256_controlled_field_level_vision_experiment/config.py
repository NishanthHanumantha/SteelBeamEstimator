"""
Phase P2.5.6 — Controlled Field-Level Vision Experiment.
MODEL_VERSION: 10.8.2

Architecture:
  P2.5.1 QuantityIntent (deterministic authority, immutable)
          +
  P2.5.4 Claude Vision (shadow observer; frozen replay or live via P2.5.5)
          ↓
  P2.5.5 candidate-level shadow (unchanged artefacts)
          ↓
  P2.5.6 field-level validation / arbitration
          ↓
  shadow-only field candidates — NEVER production

Claude never writes steel / BBS / Excel / production reinforcement objects.
P2.5.4 41-candidate Fourth Set benchmark is FROZEN — not rebuilt.
P2.5.5 artefacts are not overwritten.
"""
from __future__ import annotations

MODEL_VERSION = "10.8.2"
PHASE_ID = "P2.5.6"
PHASE_NAME = "Controlled Field-Level Vision Experiment"
OUTPUT_DIRNAME = "PhaseP256_controlled_field_level_vision_experiment"
SCOPE = "FOURTH_SET_ONLY"
MODE = "SHADOW_FIELD_EXPERIMENT_ONLY"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "SHADOW_OBSERVER"
P255_MODEL_VERSION = "10.8.1"
P254_MODEL_VERSION = "10.8.0"

FROZEN_BENCHMARK_COUNT = 41
VISION_SOURCE_REPLAY = "REPLAY_P254_FROZEN"
VISION_SOURCE_LIVE = "LIVE_P254_PROMPT"

# Field identifiers
FIELD_SEMANTIC_TYPE = "semantic_type"
FIELD_ROLE = "reinforcement_role"
FIELD_DIAMETER = "diameter"
FIELD_QUANTITY = "quantity"
FIELD_LEGS = "legs"
FIELD_SPACING = "spacing"
FIELD_ASSOCIATION = "beam_association"
FIELD_ZONE = "zone"

FIELDS = (
    FIELD_SEMANTIC_TYPE,
    FIELD_ROLE,
    FIELD_DIAMETER,
    FIELD_QUANTITY,
    FIELD_LEGS,
    FIELD_SPACING,
    FIELD_ASSOCIATION,
    FIELD_ZONE,
)

# Field-level states
ST_BOTH_AGREE = "BOTH_AGREE"
ST_VISION_FIELD_CANDIDATE = "VISION_FIELD_CANDIDATE"
ST_VISION_CONFLICT = "VISION_CONFLICT"
ST_VISION_REJECTED = "VISION_REJECTED"
ST_VISION_UNRESOLVED = "VISION_UNRESOLVED"
ST_DETERMINISTIC_ONLY = "DETERMINISTIC_ONLY"
ST_UNRESOLVED = "UNRESOLVED"
ST_NOT_APPLICABLE = "NOT_APPLICABLE"

# Field decisions — production never changes
DEC_KEEP_DET = "KEEP_DETERMINISTIC"
DEC_KEEP_DET_CONFLICT = "KEEP_DETERMINISTIC_FLAG_CONFLICT"
DEC_SHADOW_CANDIDATE = "ACCEPT_AS_SHADOW_CANDIDATE"
DEC_UNRESOLVED = "UNRESOLVED"
DEC_NOT_APPLICABLE = "NOT_APPLICABLE"
DEC_ZONE_DIAGNOSTIC = "ZONE_DIAGNOSTIC_ONLY"

SHADOW_OBJECT_KIND = "FieldLevelShadowResult"
PRODUCTION_WRITE = False
ZONE_PROMOTABLE = False
ZONE_CANDIDATE_ALLOWED = False
