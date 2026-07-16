"""Resolve equivalent notations to canonical engineering meanings (normalization only)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class EngineeringVocabularyResolver:
    """
    Maps notation aliases to canonical engineering_meaning keys.
    Configuration-driven — no semantic interpretation / behaviour.
    """

    def __init__(self, config: Dict[str, Any]):
        self._vocab = config.get("vocabulary", {}) or {}
        self._patterns = config.get("pattern_meanings", []) or []
        self._defaults = config.get("defaults", {}) or {}
        self._alias_index = self._build_alias_index()
        self._compiled_patterns = [
            (re.compile(p["pattern"], re.I), p) for p in self._patterns
        ]

    def _build_alias_index(self) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for meaning, meta in self._vocab.items():
            for alias in meta.get("aliases", []):
                key = self._norm_key(alias)
                index[key] = meaning
            # Also index the meaning key itself
            index[self._norm_key(meaning)] = meaning
        return index

    @staticmethod
    def _norm_key(text: str) -> str:
        t = re.sub(r"\s+", " ", (text or "").strip().upper())
        t = t.replace(" ", "")
        return t

    def resolve(self, notation: str) -> Optional[str]:
        """Return canonical engineering_meaning or None if unresolved."""
        key = self._norm_key(notation)
        if key in self._alias_index:
            return self._alias_index[key]
        # Soft match: strip surrounding parentheses
        if notation.startswith("(") and notation.endswith(")"):
            inner = self._norm_key(notation[1:-1])
            if inner in self._alias_index:
                return self._alias_index[inner]
        return None

    def resolve_pattern(self, notation: str) -> Optional[Dict[str, Any]]:
        for rx, meta in self._compiled_patterns:
            if rx.search(notation):
                return meta
        return None

    def resolve_full(
        self, notation: str, inventory_category: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Return (engineering_meaning, field_overrides).
        Vocabulary alias wins; then pattern; else defaults.
        """
        meaning = self.resolve(notation)
        if meaning and meaning in self._vocab:
            meta = dict(self._vocab[meaning])
            meta["engineering_meaning"] = meaning
            # Prefer inventory category if more specific and meaning has no override need
            if inventory_category and meta.get("category") in (None, "UNKNOWN"):
                meta["category"] = inventory_category
            return meaning, meta

        pattern_meta = self.resolve_pattern(notation)
        if pattern_meta:
            meta = dict(pattern_meta)
            meaning = meta.get("engineering_meaning", "UNKNOWN")
            return meaning, meta

        defaults = dict(self._defaults)
        defaults["category"] = inventory_category or defaults.get("category", "UNKNOWN")
        return defaults.get("engineering_meaning", "UNKNOWN"), defaults

    def vocabulary_map(self) -> Dict[str, str]:
        """alias (original) -> engineering_meaning for export."""
        result = {}
        for meaning, meta in self._vocab.items():
            for alias in meta.get("aliases", []):
                result[alias] = meaning
            result[meaning] = meaning
        return result

    def all_meanings(self) -> List[str]:
        return sorted(self._vocab.keys())
