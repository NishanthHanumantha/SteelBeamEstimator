"""
engineering_meaning_builder.py — Produce final EngineeringSemanticObject.
MODEL_VERSION: 7.11.0

Maps role → engineering_meaning using canonical rules.
No calculations, no multipliers — pure engineering meaning.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .semantic_models import (
    SemanticContext,
    SemanticModifier,
    EngineeringSemanticObject,
    ROLE_SIDE_FACE,
    ROLE_MAIN_BAR,
    ROLE_EXTRA_BAR,
    ROLE_STIRRUP,
    ROLE_SPACER_BAR,
    ROLE_DEVELOPMENT,
    ROLE_LAP,
    ROLE_UNKNOWN,
    MEANING_SIDE_FACE,
    MEANING_TOP_MAIN,
    MEANING_BOTTOM_MAIN,
    MEANING_TOP_EXTRA,
    MEANING_BOTTOM_EXTRA,
    MEANING_STIRRUP,
    MEANING_SPACER,
    MEANING_DEVELOPMENT,
    MEANING_LAP,
    MEANING_UNKNOWN,
    PLACEMENT_TOP,
    PLACEMENT_BOTTOM,
)

# Role + Placement → final engineering meaning
_ROLE_PLACEMENT_TO_MEANING = {
    (ROLE_SIDE_FACE,   None):           MEANING_SIDE_FACE,
    (ROLE_MAIN_BAR,    PLACEMENT_TOP):  MEANING_TOP_MAIN,
    (ROLE_MAIN_BAR,    PLACEMENT_BOTTOM): MEANING_BOTTOM_MAIN,
    (ROLE_EXTRA_BAR,   PLACEMENT_TOP):  MEANING_TOP_EXTRA,
    (ROLE_EXTRA_BAR,   PLACEMENT_BOTTOM): MEANING_BOTTOM_EXTRA,
    (ROLE_STIRRUP,     None):           MEANING_STIRRUP,
    (ROLE_SPACER_BAR,  None):           MEANING_SPACER,
    (ROLE_DEVELOPMENT, None):           MEANING_DEVELOPMENT,
    (ROLE_LAP,         None):           MEANING_LAP,
    (ROLE_UNKNOWN,     None):           MEANING_UNKNOWN,
}

# R.1 role → canonical engineering meaning (for override map)
_R1_TO_MEANING = {
    "TOP_MAIN":               MEANING_TOP_MAIN,
    "BOTTOM_MAIN":            MEANING_BOTTOM_MAIN,
    "TOP_EXTRA":              MEANING_TOP_EXTRA,
    "BOTTOM_EXTRA":           MEANING_BOTTOM_EXTRA,
    "STIRRUP":                MEANING_STIRRUP,
    "SPACER_BAR":             MEANING_SPACER,
    "SIDE_FACE_REINFORCEMENT": MEANING_SIDE_FACE,
    "DEVELOPMENT":            MEANING_DEVELOPMENT,
    "LAP":                    MEANING_LAP,
}

# Canonical semantic role → what the R.1 model should store in groups JSON
SEMANTIC_ROLE_TO_R1_ROLE = {
    ROLE_SIDE_FACE:    "SIDE_FACE_REINFORCEMENT",
    ROLE_MAIN_BAR:     None,   # depends on placement; keep existing
    ROLE_EXTRA_BAR:    None,   # depends on placement; keep existing
    ROLE_STIRRUP:      "STIRRUP",
    ROLE_SPACER_BAR:   "SPACER_BAR",
    ROLE_DEVELOPMENT:  "DEVELOPMENT",
    ROLE_LAP:          "LAP",
    ROLE_UNKNOWN:      "UNKNOWN",
}


class EngineeringMeaningBuilder:
    """
    Assemble the final EngineeringSemanticObject from all resolved components.
    """

    def build(
        self,
        ctx: SemanticContext,
        modifiers: List[SemanticModifier],
        semantic_role: str,
        placement: str,
        confidence: str,
        source: str,
        role_notes: List[str],
        placement_notes: List[str],
        quantity_notes: List[str],
        conflict_notes: List[str],
        quantity: int,
    ) -> EngineeringSemanticObject:

        # ── Determine engineering meaning ────────────────────────────────────
        meaning = self._resolve_meaning(semantic_role, placement, ctx)

        # ── Build semantic flags ─────────────────────────────────────────────
        flags = self._build_flags(ctx, modifiers, semantic_role)

        # ── Check if R.1 role was overridden ─────────────────────────────────
        r1_r1_role = ctx.regex_role
        # Map semantic role to the R.1 production role string
        prod_role = SEMANTIC_ROLE_TO_R1_ROLE.get(semantic_role)
        role_overridden = (
            prod_role is not None
            and prod_role != r1_r1_role
            and semantic_role != ROLE_MAIN_BAR
            and semantic_role != ROLE_EXTRA_BAR
        )

        # ── Compile engineering notes ─────────────────────────────────────────
        eng_notes = (
            role_notes
            + placement_notes
            + quantity_notes
            + conflict_notes
        )

        return EngineeringSemanticObject(
            annotation_id      = ctx.annotation_id,
            beam_id            = ctx.beam_id,
            raw_text           = ctx.raw_text,
            clean_text         = ctx.clean_text,
            engineering_meaning= meaning,
            engineering_role   = semantic_role,
            placement          = placement,
            quantity           = quantity,
            diameter           = ctx.diameter,
            grade              = ctx.grade,
            spacing            = ctx.spacing,
            modifiers          = [m.canonical for m in modifiers],
            semantic_flags     = flags,
            confidence         = confidence,
            source             = source,
            engineering_notes  = eng_notes,
            original_r1_role   = r1_r1_role,
            role_overridden    = role_overridden,
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _resolve_meaning(
        self,
        role: str,
        placement: str,
        ctx: SemanticContext,
    ) -> str:
        # Direct SIDE_FACE check
        if role == ROLE_SIDE_FACE:
            return MEANING_SIDE_FACE

        # Role + placement lookup
        key = (role, placement)
        if key in _ROLE_PLACEMENT_TO_MEANING:
            return _ROLE_PLACEMENT_TO_MEANING[key]

        # Try role + None
        key2 = (role, None)
        if key2 in _ROLE_PLACEMENT_TO_MEANING:
            return _ROLE_PLACEMENT_TO_MEANING[key2]

        # Fallback to R.1 role if available
        r1_meaning = _R1_TO_MEANING.get(ctx.regex_role)
        if r1_meaning:
            return r1_meaning

        return MEANING_UNKNOWN

    def _build_flags(
        self,
        ctx: SemanticContext,
        modifiers: List[SemanticModifier],
        semantic_role: str,
    ) -> List[str]:
        flags = []
        mod_canonicals = [m.canonical for m in modifiers]

        if "SIDE_FACE_REINFORCEMENT" in mod_canonicals:
            flags.append("S.F.R.")
        if "ONE_EACH_FACE" in mod_canonicals:
            flags.append("O.E.F.")
        if "BOTH_FACES" in mod_canonicals:
            flags.append("BOTH_FACE")
        if semantic_role == ROLE_SIDE_FACE and ctx.regex_role != "SIDE_FACE_REINFORCEMENT":
            flags.append("ROLE_OVERRIDE")
        if not ctx.is_reinforcement:
            flags.append("NO_BAR_SPEC")

        return flags
