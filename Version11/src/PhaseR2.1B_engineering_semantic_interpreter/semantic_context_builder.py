"""
semantic_context_builder.py — Build SemanticContext from annotation + dictionary.
MODEL_VERSION: 7.11.0

Combines:
  - Recovered text (clean_text from R.2.0 MTEXT recovery)
  - Regex match data (quantity, diameter, grade, role from R.1)
  - Semantic Dictionary lookup (R.2.1A)

Produces a SemanticContext with all gathered facts but NO engineering decisions.
The decision pipeline (role resolver, placement resolver, etc.) runs afterwards.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .semantic_models import SemanticContext

# Tokenise: split on spaces, hyphens (non-Y/R/T prefix), dots, parens
_TOKEN_SPLIT = re.compile(r"[\s,]+")


class SemanticContextBuilder:
    """
    Build a SemanticContext from a raw R.1 annotation dict and dictionary data.
    """

    def build(
        self,
        annotation: Dict[str, Any],
        dictionary_entries: Dict[str, Any],
        vocabulary_map: Dict[str, str],
    ) -> SemanticContext:
        clean_text  = annotation.get("clean_text", "") or ""
        raw_text    = annotation.get("raw_text", "") or ""
        quantity    = int(annotation.get("quantity") or 0)
        diameter    = float(annotation.get("diameter_mm") or 0.0)
        grade       = str(annotation.get("steel_grade") or "Y460")
        spacing     = annotation.get("spacing_mm")
        bar_label   = str(annotation.get("bar_label") or "")
        regex_role  = str(annotation.get("role") or "UNKNOWN")
        zone        = str(annotation.get("position_zone") or "UNKNOWN_ZONE")
        is_rebar    = bool(annotation.get("is_reinforcement", False))

        tokens      = _tokenise(clean_text)
        dict_entry, vocab_match = self._lookup(clean_text, tokens, dictionary_entries, vocabulary_map)

        return SemanticContext(
            annotation_id   = str(annotation.get("annotation_id", "")),
            beam_id         = str(annotation.get("beam_id", "")),
            raw_text        = raw_text,
            clean_text      = clean_text,
            quantity        = quantity,
            diameter        = diameter,
            grade           = grade,
            spacing         = spacing,
            bar_label       = bar_label,
            regex_role      = regex_role,
            position_zone   = zone,
            is_reinforcement= is_rebar,
            dictionary_entry= dict_entry,
            vocabulary_match= vocab_match,
            raw_tokens      = tokens,
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _lookup(
        self,
        clean_text: str,
        tokens: List[str],
        dictionary_entries: Dict[str, Any],
        vocabulary_map: Dict[str, str],
    ) -> tuple:
        """
        Return (dict_entry, vocab_key) for the best match in the vocabulary.

        Priority:
          1. Direct vocabulary alias match anywhere in clean_text
          2. Token-level match
          3. None
        """
        upper = clean_text.upper()

        # longest-first scan of vocabulary_map aliases
        sorted_aliases = sorted(vocabulary_map.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias.upper() in upper:
                canonical = vocabulary_map[alias]
                entry = dictionary_entries.get(canonical)
                return entry, canonical

        # token-level fallback
        for token in tokens:
            if token in vocabulary_map:
                canonical = vocabulary_map[token]
                entry = dictionary_entries.get(canonical)
                return entry, canonical
            key = token.upper()
            if key in dictionary_entries:
                return dictionary_entries[key], key

        return None, None


def _tokenise(text: str) -> List[str]:
    """Split text into upper-case tokens for dictionary lookup."""
    raw = _TOKEN_SPLIT.sub(" ", text).strip()
    parts = raw.split()
    result = []
    for p in parts:
        # Also emit a version with dots/parens stripped
        stripped = p.strip(".()[]")
        result.append(p.upper())
        if stripped != p:
            result.append(stripped.upper())
    return result
