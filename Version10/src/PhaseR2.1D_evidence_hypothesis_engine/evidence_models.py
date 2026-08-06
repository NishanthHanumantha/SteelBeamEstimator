"""
evidence_models.py — Core data models for Phase R.2.1D.
MODEL_VERSION: 7.12.1

Two new deterministic concepts introduced here:

  ObservableEvidence  — Everything directly readable from the annotation drawing.
                        Zero engineering inference permitted.

  IntentHypothesis    — One ranked candidate with mandatory reason.
                        Priority is deterministic ordering (1 = first preference).
                        NOT probability. NOT confidence.

HypothesisEnrichedFact — Upgraded R.2.1C EngineeringFact containing both
                          ObservableEvidence and ranked IntentHypotheses.
                          intent_candidates preserved for backward compatibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Roles (from R.2.1C) ──────────────────────────────────────────────────────
ROLE_MAIN_BAR    = "MAIN_BAR"
ROLE_EXTRA_BAR   = "EXTRA_BAR"
ROLE_STIRRUP     = "STIRRUP"
ROLE_SPACER_BAR  = "SPACER_BAR"
ROLE_SIDE_FACE   = "SIDE_FACE"
ROLE_UNKNOWN     = "UNKNOWN"

# ── Placements (from R.2.1C) ─────────────────────────────────────────────────
PLACEMENT_TOP        = "TOP"
PLACEMENT_BOTTOM     = "BOTTOM"
PLACEMENT_SIDE       = "SIDE"
PLACEMENT_BOTH_FACE  = "BOTH_FACE"
PLACEMENT_UNKNOWN    = "UNKNOWN"

# ── Intent constants ─────────────────────────────────────────────────────────
INTENT_UNKNOWN = "UNKNOWN"

# ── Annotation zones (observable, derived from placement zone) ───────────────
ZONE_TOP       = "TOP_ZONE"
ZONE_BOTTOM    = "BOTTOM_ZONE"
ZONE_SIDE      = "SIDE_ZONE"
ZONE_SIDE_FACE = "SIDE_FACE_ZONE"
ZONE_UNKNOWN   = "UNKNOWN_ZONE"

PLACEMENT_TO_ZONE: Dict[str, str] = {
    PLACEMENT_TOP:       ZONE_TOP,
    PLACEMENT_BOTTOM:    ZONE_BOTTOM,
    PLACEMENT_SIDE:      ZONE_SIDE,
    PLACEMENT_BOTH_FACE: ZONE_SIDE_FACE,
    PLACEMENT_UNKNOWN:   ZONE_UNKNOWN,
}

# ── Source labels ────────────────────────────────────────────────────────────
SOURCE_SEMANTIC_DICTIONARY = "SEMANTIC_DICTIONARY"
SOURCE_EXPLICIT_MODIFIER   = "EXPLICIT_MODIFIER"
SOURCE_REGEX_GUESS         = "REGEX_GUESS"
SOURCE_R1_CLASSIFIER       = "R1_CLASSIFIER"
SOURCE_UNKNOWN             = "UNKNOWN"


@dataclass(frozen=True)
class ObservableEvidence:
    """
    All observable information from the annotation drawing.

    This dataclass MUST contain ONLY facts directly readable from the drawing.
    It MUST NOT contain engineering assumptions, inferences, or resolved intent.

    Every field is a direct observation — not a conclusion.
    """
    annotation_id:      str
    beam_id:            str
    original_text:      str             # raw annotation text (before cleaning)
    clean_text:         str             # normalised annotation text
    role_source:        str             # what evidence sourced the role
    placement_source:   str             # what evidence sourced the placement
    quantity:           int
    diameter:           float
    grade:              str
    spacing:            Optional[float]
    modifiers:          List[str]       # observed modifiers: ONE_EACH_FACE, U_BAR, etc.
    semantic_flags:     List[str]       # observed semantic flags from R.2.1A/B
    annotation_zone:    str             # position zone: TOP_ZONE / BOTTOM_ZONE / etc.
    r1_original_role:   str             # R.1 classifier's original role (no override)
    confidence_source:  str             # source backing confidence assessment
    notes:              List[str]       # pure observation notes, no inferences


@dataclass(frozen=True)
class IntentHypothesis:
    """
    A single ranked intent hypothesis.

    priority: 1-based sequential integer. 1 = first preference for R.3.
              Deterministic — NOT probabilistic.
    reason:   Mandatory explanation of why this hypothesis holds this priority.
    intent:   The candidate engineering meaning (e.g. TOP_MAIN, BOTTOM_EXTRA).
    """
    intent:   str
    priority: int
    reason:   str


@dataclass
class HypothesisEnrichedFact:
    """
    Upgraded R.2.1C EngineeringFact with ObservableEvidence and ranked hypotheses.

    This is the clean contract between Phase R.2.1D and Phase R.3.

    observable_evidence  — zero-inference drawing facts
    intent_hypotheses    — deterministic ranked hypotheses (replaces intent_candidates)
    intent_candidates    — backward compat list (derived from hypotheses, same order)
    intent               — ALWAYS "UNKNOWN" until R.3 resolves it
    """
    # ── Preserved from R.2.1C ────────────────────────────────────────────────
    annotation_id:           str
    beam_id:                 str
    clean_text:              str
    quantity:                int
    diameter:                float
    grade:                   str
    spacing:                 Optional[float]
    role:                    str
    placement:               str
    intent:                  str                      # ALWAYS "UNKNOWN"
    modifiers:               List[str]
    semantic_flags:          List[str]
    confidence:              str
    source:                  str
    engineering_notes:       List[str]
    geometry_required:       bool
    intent_deferred_reason:  str

    # ── New R.2.1D fields ────────────────────────────────────────────────────
    observable_evidence:     ObservableEvidence
    intent_hypotheses:       List[IntentHypothesis]   # ranked, replaces candidates
    intent_candidates:       List[str]                # backward compat (from hypotheses)
