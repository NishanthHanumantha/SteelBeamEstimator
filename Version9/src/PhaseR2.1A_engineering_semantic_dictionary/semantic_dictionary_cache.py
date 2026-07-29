"""Singleton cache for Engineering Semantic Dictionary."""
from __future__ import annotations

from typing import Optional

from .semantic_dictionary_models import SemanticDictionary

_CACHE: Optional[SemanticDictionary] = None


class SemanticDictionaryCache:
    """Process-wide singleton cache. Dictionary loads once; reload for development."""

    @staticmethod
    def get() -> Optional[SemanticDictionary]:
        return _CACHE

    @staticmethod
    def set(dictionary: SemanticDictionary) -> None:
        global _CACHE
        _CACHE = dictionary

    @staticmethod
    def clear() -> None:
        global _CACHE
        _CACHE = None

    @staticmethod
    def is_loaded() -> bool:
        return _CACHE is not None
