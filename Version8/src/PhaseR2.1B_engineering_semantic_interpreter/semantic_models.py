"""
semantic_models.py — Immutable dataclasses for Phase R.2.1B.
MODEL_VERSION: 7.11.0
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Canonical engineering meanings ──────────────────────────────────────────
MEANING_SIDE_FACE       = "SIDE_FACE_REINFORCEMENT"
MEANING_TOP_MAIN        = "TOP_MAIN"
MEANING_BOTTOM_MAIN     = "BOTTOM_MAIN"
MEANING_TOP_EXTRA       = "TOP_EXTRA"
MEANING_BOTTOM_EXTRA    = "BOTTOM_EXTRA"
MEANING_STIRRUP         = "STIRRUP"
MEANING_SPACER          = "SPACER"
MEANING_LAP             = "LAP"
MEANING_DEVELOPMENT     = "DEVELOPMENT"
MEANING_UNKNOWN         = "UNKNOWN"

# ── Canonical roles ──────────────────────────────────────────────────────────
ROLE_SIDE_FACE          = "SIDE_FACE"
ROLE_MAIN_BAR           = "MAIN_BAR"
ROLE_EXTRA_BAR          = "EXTRA_BAR"
ROLE_STIRRUP            = "STIRRUP"
ROLE_SPACER_BAR         = "SPACER_BAR"
ROLE_DEVELOPMENT        = "DEVELOPMENT"
ROLE_LAP                = "LAP"
ROLE_UNKNOWN            = "UNKNOWN"

# ── Canonical placements ─────────────────────────────────────────────────────
PLACEMENT_NEAR_FACE     = "NEAR_FACE"
PLACEMENT_FAR_FACE      = "FAR_FACE"
PLACEMENT_BOTH_FACE     = "BOTH_FACE"
PLACEMENT_SIDE_FACE     = "SIDE_FACE"
PLACEMENT_TOP           = "TOP"
PLACEMENT_BOTTOM        = "BOTTOM"
PLACEMENT_UNKNOWN       = "UNKNOWN"

# ── Canonical modifiers ──────────────────────────────────────────────────────
MODIFIER_ONE_EACH_FACE  = "ONE_EACH_FACE"
MODIFIER_BOTH_FACES     = "BOTH_FACES"
MODIFIER_NEAR_FACE      = "NEAR_FACE"
MODIFIER_FAR_FACE       = "FAR_FACE"
MODIFIER_TYPICAL        = "TYPICAL"
MODIFIER_U_BAR          = "U_BAR"
MODIFIER_SIDE_FACE_REINF = "SIDE_FACE_REINFORCEMENT"

# ── Confidence levels ────────────────────────────────────────────────────────
CONF_HIGH   = "HIGH"
CONF_MEDIUM = "MEDIUM"
CONF_LOW    = "LOW"

# ── Annotation source ────────────────────────────────────────────────────────
SOURCE_EXPLICIT_MODIFIER  = "EXPLICIT_MODIFIER"
SOURCE_SEMANTIC_DICTIONARY = "SEMANTIC_DICTIONARY"
SOURCE_REGEX_GUESS        = "REGEX_GUESS"
SOURCE_UNKNOWN            = "UNKNOWN"


@dataclass(frozen=True)
class SemanticModifier:
    """A parsed modifier extracted from annotation text."""
    raw_token:  str
    canonical:  str           # e.g. ONE_EACH_FACE
    source_text: str          # substring that triggered this modifier
    priority:   int = 0       # higher = higher priority


@dataclass(frozen=True)
class SemanticContext:
    """
    Intermediate context assembled from annotation + dictionary lookup.
    No engineering decisions yet — only gathered facts.
    """
    annotation_id:      str
    beam_id:            str
    raw_text:           str
    clean_text:         str
    quantity:           int
    diameter:           float
    grade:              str
    spacing:            Optional[float]
    bar_label:          str
    regex_role:         str           # role from R.1 annotation classifier
    position_zone:      str           # TOP_ZONE / BOTTOM_ZONE / etc.
    is_reinforcement:   bool
    dictionary_entry:   Optional[Dict[str, Any]]   # best dict match or None
    vocabulary_match:   Optional[str]              # canonical key from vocabulary
    raw_tokens:         List[str] = field(default_factory=list)


@dataclass(frozen=True)
class EngineeringSemanticObject:
    """
    Final structured engineering meaning for one reinforcement annotation.

    Pure engineering semantics — no calculations, no multipliers.
    The downstream calculation engine decides multipliers from modifier data.
    """
    annotation_id:       str
    beam_id:             str
    raw_text:            str
    clean_text:          str

    # ── Core engineering meaning ─────────────────────────────────────────────
    engineering_meaning: str       # e.g. SIDE_FACE_REINFORCEMENT
    engineering_role:    str       # e.g. SIDE_FACE
    placement:           str       # e.g. BOTH_FACE
    quantity:            int       # raw annotation quantity — no multiplication
    diameter:            float     # mm
    grade:               str       # Y / R / T / Y460 etc.
    spacing:             Optional[float]   # mm; stirrups only

    # ── Modifier and flags ───────────────────────────────────────────────────
    modifiers:           List[str]         # canonical modifier names
    semantic_flags:      List[str]         # e.g. ["ROLE_OVERRIDE", "S.F.R."]

    # ── Confidence and traceability ──────────────────────────────────────────
    confidence:          str               # HIGH / MEDIUM / LOW
    source:              str               # EXPLICIT_MODIFIER / SEMANTIC_DICTIONARY / REGEX_GUESS
    engineering_notes:   List[str]

    # ── Original R.1 role for audit ──────────────────────────────────────────
    original_r1_role:    str               # role as assigned by R.1 classifier
    role_overridden:     bool              # True if semantic role differs from R.1 role
