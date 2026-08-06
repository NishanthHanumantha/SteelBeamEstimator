"""
fact_models.py — Core data models for Phase R.2.1C.
MODEL_VERSION: 7.12.0

Three independent engineering concepts:

  Role      — observable from annotation text  (MAIN_BAR, EXTRA_BAR, ...)
  Placement — observable from position zone    (TOP, BOTTOM, SIDE, ...)
  Intent    — ALWAYS unknown until geometry proves otherwise

Intent candidates are geometry-dependent possibilities derived from
(role + placement) combinations, referencing engineering rules derived from
labelled beam drawings (B1, B2, B8, B9, B10).

Engineering facts derived from labelled drawings:
  - TOP bars that run only over supports     → likely TOP_EXTRA (short)
  - TOP bars that run full span              → likely TOP_MAIN (continuous)
  - BOTTOM bars at mid-span                 → likely BOTTOM_MAIN
  - BOTTOM bars that start at support        → likely BOTTOM_EXTRA
  - These distinctions REQUIRE bar extent data — unavailable until R.3.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Roles (observable) ───────────────────────────────────────────────────────
ROLE_MAIN_BAR    = "MAIN_BAR"
ROLE_EXTRA_BAR   = "EXTRA_BAR"
ROLE_STIRRUP     = "STIRRUP"
ROLE_SPACER_BAR  = "SPACER_BAR"
ROLE_SIDE_FACE   = "SIDE_FACE"
ROLE_UNKNOWN     = "UNKNOWN"

ALL_ROLES = {
    ROLE_MAIN_BAR, ROLE_EXTRA_BAR, ROLE_STIRRUP,
    ROLE_SPACER_BAR, ROLE_SIDE_FACE, ROLE_UNKNOWN,
}

# ── Placements (observable) ──────────────────────────────────────────────────
PLACEMENT_TOP        = "TOP"
PLACEMENT_BOTTOM     = "BOTTOM"
PLACEMENT_SIDE       = "SIDE"
PLACEMENT_BOTH_FACE  = "BOTH_FACE"
PLACEMENT_UNKNOWN    = "UNKNOWN"

ALL_PLACEMENTS = {
    PLACEMENT_TOP, PLACEMENT_BOTTOM, PLACEMENT_SIDE,
    PLACEMENT_BOTH_FACE, PLACEMENT_UNKNOWN,
}

# ── Intent (ALWAYS unknown here) ─────────────────────────────────────────────
INTENT_UNKNOWN = "UNKNOWN"

# ── Candidate intents (what R.3 will resolve) ────────────────────────────────
CANDIDATE_TOP_MAIN            = "TOP_MAIN"
CANDIDATE_TOP_EXTRA           = "TOP_EXTRA"
CANDIDATE_CONTINUOUS_TOP      = "CONTINUOUS_TOP"
CANDIDATE_SUPPORT_TOP         = "SUPPORT_TOP"
CANDIDATE_BOTTOM_MAIN         = "BOTTOM_MAIN"
CANDIDATE_BOTTOM_EXTRA        = "BOTTOM_EXTRA"
CANDIDATE_CONTINUOUS_BOTTOM   = "CONTINUOUS_BOTTOM"
CANDIDATE_SUPPORT_BOTTOM      = "SUPPORT_BOTTOM"
CANDIDATE_CURTAILMENT_TOP     = "CURTAILMENT_TOP"
CANDIDATE_CURTAILMENT_BOTTOM  = "CURTAILMENT_BOTTOM"
CANDIDATE_CURTAILMENT_BAR     = "CURTAILMENT_BAR"
CANDIDATE_SUPPORT_BAR         = "SUPPORT_BAR"
CANDIDATE_SPACER_BAR          = "SPACER_BAR"
CANDIDATE_CHAIR_BAR           = "CHAIR_BAR"
CANDIDATE_STIRRUP             = "STIRRUP"
CANDIDATE_SIDE_FACE_REINF     = "SIDE_FACE_REINFORCEMENT"
CANDIDATE_UNKNOWN             = "UNKNOWN"

# ── Confidence levels ────────────────────────────────────────────────────────
CONF_HIGH   = "HIGH"
CONF_MEDIUM = "MEDIUM"
CONF_LOW    = "LOW"


@dataclass(frozen=True)
class EngineeringFact:
    """
    A geometry-independent engineering fact about one reinforcement annotation.

    Role and Placement are derived from observable evidence.
    Intent is ALWAYS UNKNOWN until R.3 Geometry Context Engine resolves it.
    Intent candidates list all plausible intents that geometry can distinguish.

    This object is the clean contract between Phase R.2.1C and Phase R.3.
    """
    annotation_id:           str
    beam_id:                 str
    clean_text:              str

    # ── Measured quantities (exact, never multiplied) ────────────────────────
    quantity:                int
    diameter:                float
    grade:                   str
    spacing:                 Optional[float]

    # ── Observable engineering facts ─────────────────────────────────────────
    role:                    str              # MAIN_BAR / EXTRA_BAR / etc.
    placement:               str              # TOP / BOTTOM / SIDE / BOTH_FACE / UNKNOWN

    # ── Deferred intent ──────────────────────────────────────────────────────
    intent:                  str              # ALWAYS "UNKNOWN" at this stage
    intent_candidates:       List[str]        # e.g. [TOP_MAIN, TOP_EXTRA, ...]

    # ── Semantic modifiers and flags ─────────────────────────────────────────
    modifiers:               List[str]        # ONE_EACH_FACE / SIDE_FACE_REINFORCEMENT / ...
    semantic_flags:          List[str]        # S.F.R. / O.E.F. / ROLE_OVERRIDE / ...

    # ── Confidence and traceability ──────────────────────────────────────────
    confidence:              str             # applies to role + placement ONLY
    source:                  str             # where role/placement evidence came from
    engineering_notes:       List[str]       # explains WHY intent is unresolved

    # ── Full lineage back to R.2.1B ──────────────────────────────────────────
    original_semantic_object: Dict[str, Any]  # complete ESO for full traceability

    # ── Normalization metadata ────────────────────────────────────────────────
    intent_deferred_reason:  str             # why intent cannot be resolved now
    geometry_required:       bool            # always True (except STIRRUP/SIDE_FACE)
