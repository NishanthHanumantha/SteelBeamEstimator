"""
Phase P2.5.11 — Evidence Enrichment for Held New-Stirrup Recoveries.
MODEL_VERSION: 10.10.0

Shadow-only research. Does not authorize production promotion.
Consumes P2.5.10 insertion classification; does not bypass it.
"""
from __future__ import annotations

MODEL_VERSION = "10.10.0"
PHASE_ID = "P2.5.11"
PHASE_NAME = "Evidence Enrichment for Held New-Stirrup Recoveries"
OUTPUT_DIRNAME = "PhaseP2511_evidence_enrichment"
SCOPE = "FIFTH_SET_PRIMARY"
MODE = "REPLAY_P257_LIVE_RESULTS"
ENGINEERING_CHANGES = "NONE"
CLAUDE = "REPLAY_ONLY"
MAX_PROMOTION_LEVEL = "CONTROLLED_RECOMPUTE"
PRODUCTION_WRITE = False

STRATEGY_UNKNOWN_ONLY = "P259_UNKNOWN_ONLY"
STRATEGY_P2510 = "P2510_GATED_UNKNOWN_ONLY"
STRATEGY_P2511 = "P2511_EVIDENCE_ENRICHED"

STRENGTH_STRONG = "STRONG"
STRENGTH_MODERATE = "MODERATE"
STRENGTH_WEAK = "WEAK"
STRENGTH_UNSAFE = "UNSAFE"

QUALITY_CLEAN = "CLEAN_COMPLETE"
QUALITY_SCHEDULE = "OCR_BUT_SCHEDULE_VISIBLE"
QUALITY_OCR = "OCR_TRUNCATED"
QUALITY_MALFORMED = "MALFORMED"
QUALITY_PARTIAL = "PARTIAL"

DEC_ALLOW = "ALLOW"
DEC_HOLD = "HOLD"
DEC_REJECT = "REJECT"

REASON_VALID_NOTATION = "VALID_BEAM_STIRRUP_NOTATION"
REASON_VALID_UNIFORM = "VALID_UNIFORM_STIRRUP"
REASON_COMPLETE_SCHEDULE = "COMPLETE_STIRRUP_SCHEDULE"
REASON_TARGET_ASSOC = "TARGET_BEAM_ASSOCIATION"
REASON_PLAUSIBILITY = "ENGINEERING_PLAUSIBILITY"
REASON_SPATIAL = "SPATIAL_SUPPORT"
REASON_CONTEXTUAL = "CONTEXTUAL_SUPPORT"
REASON_PRESERVE_P2510_ALLOW = "PRESERVED_P2510_ALLOW"
REASON_PRESERVE_P2510_REJECT = "PRESERVED_P2510_REJECT"
REASON_MALFORMED = "MALFORMED_STIRRUP_NOTATION"
REASON_OCR_TRUNCATED = "OCR_TRUNCATED"
REASON_INVALID_DIAMETER = "INVALID_DIAMETER"
REASON_INVALID_LEGS = "INVALID_LEGS"
REASON_INVALID_SPACING = "INVALID_SPACING"
REASON_WEAK_ASSOC = "WEAK_BEAM_ASSOCIATION"
REASON_CONTRADICTION = "CONTRADICTORY_EVIDENCE"
REASON_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
REASON_UNSUPPORTED_NEW = "UNSUPPORTED_NEW_STIRRUP"
REASON_NO_NOTATION = "NO_VALID_STIRRUP_NOTATION"

PRIMARY_SET_KEY = "Fifth"
P2510_OUTPUT = "PhaseP2510_new_stirrup_safety"
P259_OUTPUT = "PhaseP259_beam_safe_arbitration"

RUNTIME_CONTEXT_KEYS = frozenset(
    {
        "beam_id",
        "span_mm",
        "stirrup_count",
        "has_stirrups",
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
        "vis_normalized_notation",
        "trigger_reason",
        "owned_by_beam",
        "has_leader",
        "chain_semantic_stirrup",
        "peer_agreement_count",
        "complete_schedule_in_text",
        "numeric_slash_schedule_in_text",
        "annotation_quality",
        "notation_parseable",
        "notation_legs",
        "notation_diameter",
        "notation_spacing",
        "engineering_plausible",
        "spatial_support",
        "contextual_support",
        "fields_match_notation",
    }
)
