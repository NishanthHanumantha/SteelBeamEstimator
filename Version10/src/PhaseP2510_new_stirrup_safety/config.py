"""
Phase P2.5.10 — New-Stirrup Insertion Safety Gate.
MODEL_VERSION: 10.9.0

Shadow-only research. Does not authorize production promotion.
Runtime gate must not read evaluation-only workbooks or answers.
"""
from __future__ import annotations

MODEL_VERSION = "10.9.0"
PHASE_ID = "P2.5.10"
PHASE_NAME = "New-Stirrup Insertion Safety Gate"
OUTPUT_DIRNAME = "PhaseP2510_new_stirrup_safety"
SCOPE = "FIFTH_SET_PRIMARY"
MODE = "REPLAY_P257_LIVE_RESULTS"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "REPLAY_ONLY"
MAX_PROMOTION_LEVEL = "CONTROLLED_RECOMPUTE"
PRODUCTION_WRITE = False

STRATEGY_UNKNOWN_ONLY = "P259_UNKNOWN_ONLY"
STRATEGY_GATED = "P2510_GATED_UNKNOWN_ONLY"

CLS_NO_NEW = "NO_NEW_STIRRUP"
CLS_SUPPLEMENT = "SUPPLEMENTS_EXISTING_STIRRUP"
CLS_CREATES_NEW = "CREATES_NEW_STIRRUP"

DEC_ALLOW = "ALLOW"
DEC_HOLD = "HOLD"
DEC_REJECT = "REJECT"

REASON_NO_NEW_SAFE = "NO_NEW_STIRRUP_SAFE"
REASON_SUPPLEMENT_SAFE = "SUPPLEMENTS_EXISTING_STIRRUP"
REASON_NEW_SUPPORTED = "NEW_STIRRUP_SUPPORTED_BY_PRODUCTION_EVIDENCE"
REASON_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_INSERTION_EVIDENCE"
REASON_NEW_REQUIRES_STRONGER = "NEW_STIRRUP_REQUIRES_STRONGER_EVIDENCE"
REASON_SEMANTIC_CONFLICT = "DETERMINISTIC_SEMANTIC_CONFLICT"
REASON_INCOMPATIBLE_STIRRUP = "INCOMPATIBLE_EXISTING_STIRRUP"
REASON_UNSUPPORTED_NEW_ZONE = "UNSUPPORTED_NEW_ZONE"
REASON_UNSUPPORTED_NEW_PIECE = "UNSUPPORTED_NEW_PIECE"
REASON_UNSUPPORTED_NEW_STIRRUP = "UNSUPPORTED_NEW_STIRRUP"
REASON_INVALID_DIAMETER = "INVALID_DIAMETER"
REASON_INVALID_SPACING = "INVALID_SPACING"
REASON_INVALID_LEGS = "INVALID_LEGS"
REASON_INVENTED_QUANTITY = "INVENTED_QUANTITY"
REASON_UNSUPPORTED_TRANSFORM = "UNSUPPORTED_ENGINEERING_TRANSFORM"
REASON_ASSOCIATION_CONFLICT = "BEAM_ASSOCIATION_CONFLICT"
REASON_PRODUCTION_MUTATION = "PRODUCTION_MUTATION_ATTEMPT"
REASON_NEW_ZONE_NO_EXISTING = "NEW_ZONE_WITHOUT_EXISTING_ZONE"
REASON_NEW_PIECE_NO_STIRRUP = "NEW_PIECE_WITHOUT_EXISTING_STIRRUP"
REASON_NEW_STEEL_NO_EVIDENCE = "NEW_STEEL_WITHOUT_INDEPENDENT_EVIDENCE"

PRIMARY_DRAWING_SET = "Fifth Set Drawings"
PRIMARY_SET_KEY = "Fifth"
P257_OUTPUT = "PhaseP257_unseen_drawing_controlled_vision_validation"
P258_OUTPUT = "PhaseP258_controlled_vision_field_repair"
P259_OUTPUT = "PhaseP259_beam_safe_arbitration"

RUNTIME_CONTEXT_KEYS = frozenset(
    {
        "beam_id",
        "span_mm",
        "stirrup_count",
        "has_stirrups",
        "stirrup_labels",
        "stirrup_quantities",
        "stirrup_diameters",
        "stirrup_spacings",
        "zone_truncated_label",
        "existing_zone",
        "top_main_count",
        "bottom_main_count",
        "side_face_count",
        "annotation_text",
        "annotation_id",
        "candidate_id",
        "det_semantic_type",
        "vis_semantic_type",
        "vis_role",
        "vis_association",
        "vis_diameter",
        "vis_legs",
        "vis_spacing",
        "vis_quantity",
        "trigger_reason",
        "owned_by_beam",
        "peer_agreement_count",
        "complete_schedule_in_text",
        "numeric_slash_schedule_in_text",
    }
)
