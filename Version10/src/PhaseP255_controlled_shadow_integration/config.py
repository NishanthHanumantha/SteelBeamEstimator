"""
Phase P2.5.5 — Controlled Shadow Integration.
MODEL_VERSION: 10.8.1

Architecture:
  P2.5.1 QuantityIntent (deterministic authority, immutable)
          +
  P2.5.4 Claude Vision (shadow observer; frozen replay or live)
          ↓
  P2.5.5 arbitrator / safety gates
          ↓
  shadow-only artefacts

Claude never writes steel / BBS / Excel / production reinforcement objects.
P2.5.4 41-candidate Fourth Set benchmark is FROZEN — not rebuilt.
"""
from __future__ import annotations

MODEL_VERSION = "10.8.1"
PHASE_ID = "P2.5.5"
PHASE_NAME = "Controlled Shadow Integration"
OUTPUT_DIRNAME = "PhaseP255_controlled_shadow_integration"
SCOPE = "FOURTH_SET_ONLY"
MODE = "SHADOW_INTEGRATION_ONLY"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "SHADOW_OBSERVER"
P254_MODEL_VERSION = "10.8.0"

P250_OUTPUT = "PhaseP250_beam_evidence_crop_qa"
P251_OUTPUT = "PhaseP251_quantity_intent_schema"
P254_OUTPUT = "PhaseP254_semantic_reinforcement_vision_benchmark"

FROZEN_BENCHMARK_COUNT = 41
VISION_SOURCE_REPLAY = "REPLAY_P254_FROZEN"
VISION_SOURCE_LIVE = "LIVE_P254_PROMPT"

DEFAULT_ELIGIBILITY = "CONFIGURED_FULL_SHADOW"

# Operational comparison classes
CMP_BOTH_AGREE = "BOTH_AGREE"
CMP_VISION_ONLY_RESOLVED = "VISION_ONLY_RESOLVED"
CMP_DETERMINISTIC_ONLY_RESOLVED = "DETERMINISTIC_ONLY_RESOLVED"
CMP_VISION_CONFLICT = "VISION_CONFLICT"
CMP_BOTH_UNRESOLVED = "BOTH_UNRESOLVED"
CMP_VISION_WRONG = "VISION_WRONG"

# Arbitration actions — production never changes
ACT_KEEP_DET = "KEEP_DETERMINISTIC"
ACT_SHADOW_VISION = "SHADOW_ONLY_VISION_RESOLUTION"
ACT_KEEP_DET_CONFLICT = "KEEP_DETERMINISTIC_FLAG_CONFLICT"
ACT_UNRESOLVED = "UNRESOLVED"
ACT_KEEP_DET_VISION_ERROR = "KEEP_DETERMINISTIC_FLAG_VISION_ERROR"

ELIGIBILITY_REASONS = (
    "OCR_UNCERTAIN",
    "SEMANTIC_UNCERTAIN",
    "ROLE_UNCERTAIN",
    "TYPE_UNCERTAIN",
    "BEAM_ASSOCIATION_UNCERTAIN",
    "DIFFICULT_VISUAL",
    "SIDE_FACE_CANDIDATE",
    "MULTI_ANNOTATION_AMBIGUITY",
    "CONFIGURED_FULL_SHADOW",
)

IMPORTANT_FIELDS = (
    "type",
    "role",
    "beam_association",
    "diameter",
    "quantity",
    "spacing",
)

SHADOW_OBJECT_KIND = "ShadowIntegrationResult"
PRODUCTION_WRITE = False
ZONE_PROMOTABLE = False
