"""
semantic_role_resolver.py — Determine engineering role from semantic evidence.
MODEL_VERSION: 7.11.0

Decision uses:
  1. Explicit modifier (SIDE_FACE_REINFORCEMENT modifier → SIDE_FACE role)
  2. Semantic Dictionary entry (engineering_role field)
  3. R.1 regex role (fallback — treated as REGEX_GUESS)

Does NOT use beam names or hardcoded beam IDs.
Role remains generic (MAIN_BAR, SIDE_FACE, STIRRUP) until geometry
context assigns a final directional role (TOP/BOTTOM).
"""
from __future__ import annotations

import re
from typing import List, Optional

from .semantic_models import (
    SemanticContext,
    SemanticModifier,
    MODIFIER_SIDE_FACE_REINF,
    MODIFIER_U_BAR,
    ROLE_SIDE_FACE,
    ROLE_MAIN_BAR,
    ROLE_EXTRA_BAR,
    ROLE_STIRRUP,
    ROLE_SPACER_BAR,
    ROLE_DEVELOPMENT,
    ROLE_LAP,
    ROLE_UNKNOWN,
    SOURCE_EXPLICIT_MODIFIER,
    SOURCE_SEMANTIC_DICTIONARY,
    SOURCE_REGEX_GUESS,
)

# Map R.1 roles to R.2.1B generic roles
_R1_ROLE_MAP = {
    "TOP_MAIN":              ROLE_MAIN_BAR,
    "BOTTOM_MAIN":           ROLE_MAIN_BAR,
    "TOP_EXTRA":             ROLE_EXTRA_BAR,
    "BOTTOM_EXTRA":          ROLE_EXTRA_BAR,
    "STIRRUP":               ROLE_STIRRUP,
    "SPACER_BAR":            ROLE_SPACER_BAR,
    "SIDE_FACE_REINFORCEMENT": ROLE_SIDE_FACE,
    "DEVELOPMENT":           ROLE_DEVELOPMENT,
    "LAP":                   ROLE_LAP,
    "UNKNOWN":               ROLE_UNKNOWN,
}

# Map dictionary engineering_role → R.2.1B role
_DICT_ROLE_MAP = {
    "SIDE_FACE":             ROLE_SIDE_FACE,
    "STIRRUP":               ROLE_STIRRUP,
    "MAIN_BAR":              ROLE_MAIN_BAR,
    "EXTRA_BAR":             ROLE_EXTRA_BAR,
    "SPACER_BAR":            ROLE_SPACER_BAR,
    "DEVELOPMENT":           ROLE_DEVELOPMENT,
    "LAP":                   ROLE_LAP,
}

# Stirrup detection: Y/R/T diameters @spacing
_RE_STIRRUP = re.compile(r"[YRTyrt]\s*\d+\s*@\s*\d+")


class SemanticRoleResolver:
    """
    Resolve the engineering role for an annotation using a priority cascade.

    Priority:
      1. Explicit modifier (S.F.R. modifier → SIDE_FACE)
      2. Semantic Dictionary engineering_role
      3. R.1 regex role mapped to generic role
    """

    def resolve(
        self,
        ctx: SemanticContext,
        modifiers: List[SemanticModifier],
    ) -> tuple:
        """
        Returns (role: str, source: str, notes: list[str]).
        """
        notes = []

        # ── Priority 1: Explicit modifier ────────────────────────────────────
        for mod in modifiers:
            if mod.canonical == MODIFIER_SIDE_FACE_REINF:
                notes.append(f"Role override: S.F.R. modifier → {ROLE_SIDE_FACE}")
                return ROLE_SIDE_FACE, SOURCE_EXPLICIT_MODIFIER, notes

            if mod.canonical == MODIFIER_U_BAR:
                notes.append(f"Role: U-BAR modifier detected → {ROLE_SIDE_FACE}")
                return ROLE_SIDE_FACE, SOURCE_EXPLICIT_MODIFIER, notes

        # ── Priority 2: Semantic Dictionary ──────────────────────────────────
        if ctx.dictionary_entry:
            dict_role = ctx.dictionary_entry.get("engineering_role")
            if dict_role and dict_role in _DICT_ROLE_MAP:
                mapped = _DICT_ROLE_MAP[dict_role]
                notes.append(f"Role from dictionary: {dict_role} → {mapped}")
                return mapped, SOURCE_SEMANTIC_DICTIONARY, notes

        # ── Priority 3: Stirrup detection (text pattern) ─────────────────────
        if ctx.regex_role == "STIRRUP" or _RE_STIRRUP.search(ctx.clean_text):
            notes.append("Role: STIRRUP (regex evidence)")
            return ROLE_STIRRUP, SOURCE_REGEX_GUESS, notes

        # ── Priority 4: R.1 role fallback ────────────────────────────────────
        if ctx.regex_role and ctx.regex_role != "UNKNOWN":
            mapped = _R1_ROLE_MAP.get(ctx.regex_role, ROLE_UNKNOWN)
            notes.append(f"Role from R.1 classifier: {ctx.regex_role} → {mapped}")
            source = SOURCE_REGEX_GUESS
            return mapped, source, notes

        notes.append("Role: UNKNOWN (no evidence)")
        return ROLE_UNKNOWN, SOURCE_REGEX_GUESS, notes
