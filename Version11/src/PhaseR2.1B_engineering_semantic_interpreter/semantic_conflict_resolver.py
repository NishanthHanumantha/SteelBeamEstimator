"""
semantic_conflict_resolver.py — Handle conflicting semantic evidence.
MODEL_VERSION: 7.11.0

Priority for resolution:
  1. Explicit Modifier  (highest)
  2. Semantic Dictionary
  3. Regex Guess        (R.1 classifier output)
  4. UNKNOWN            (lowest)

When the semantic dictionary disagrees with the R.1 classifier, the dictionary
wins. When an explicit modifier disagrees with the dictionary, the modifier wins.

Produces a deterministic, auditable decision.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .semantic_models import (
    SemanticContext,
    SemanticModifier,
    ROLE_SIDE_FACE,
    ROLE_UNKNOWN,
    SOURCE_EXPLICIT_MODIFIER,
    SOURCE_SEMANTIC_DICTIONARY,
    SOURCE_REGEX_GUESS,
    SOURCE_UNKNOWN,
    CONF_HIGH,
    CONF_MEDIUM,
    CONF_LOW,
)


class SemanticConflictResolver:
    """
    Adjudicate between competing role / meaning / placement signals.

    Accepts pre-computed candidates from role resolver and meaning builder,
    applies the priority cascade, and returns a final (confidence, source, notes).
    """

    def resolve(
        self,
        ctx: SemanticContext,
        modifiers: List[SemanticModifier],
        role_source: str,
        meaning_from_dict: Optional[str],
    ) -> Dict[str, Any]:
        """
        Return dict with keys: confidence, source, conflict_notes.
        """
        conflict_notes = []
        has_explicit   = role_source == SOURCE_EXPLICIT_MODIFIER
        has_dict       = role_source == SOURCE_SEMANTIC_DICTIONARY or meaning_from_dict not in (None, "UNKNOWN")
        has_regex      = role_source == SOURCE_REGEX_GUESS

        # Detect conflicts
        r1_role = ctx.regex_role
        dict_meaning = meaning_from_dict or "UNKNOWN"

        if has_explicit:
            conflict_notes.append(
                f"Conflict resolver: explicit modifier wins over R.1 role ({r1_role})"
            )
            confidence = CONF_HIGH
            source = SOURCE_EXPLICIT_MODIFIER

        elif has_dict:
            if dict_meaning != "UNKNOWN" and r1_role not in ("UNKNOWN", None):
                # Check if dictionary meaning conflicts with regex role
                conflict_notes.append(
                    f"Dictionary meaning ({dict_meaning}) may differ from R.1 role ({r1_role}) — dictionary wins"
                )
            confidence = CONF_HIGH if dict_meaning != "UNKNOWN" else CONF_MEDIUM
            source = SOURCE_SEMANTIC_DICTIONARY

        elif has_regex:
            conflict_notes.append(
                f"Role from R.1 classifier: {r1_role} (no dictionary override)"
            )
            confidence = CONF_MEDIUM
            source = SOURCE_REGEX_GUESS

        else:
            conflict_notes.append("No reliable role evidence — UNKNOWN")
            confidence = CONF_LOW
            source = SOURCE_UNKNOWN

        return {
            "confidence": confidence,
            "source": source,
            "conflict_notes": conflict_notes,
        }
