"""Deterministic cache for engineering reasoning results."""

from __future__ import annotations

import hashlib
from typing import Dict, Optional

from reasoning_models import EngineeringReasoningResult


class ReasoningCache:
    """Cache reasoning results by task, context checksum, and template version."""

    def __init__(self) -> None:
        self._cache: Dict[str, EngineeringReasoningResult] = {}
        self._hits = 0
        self._misses = 0

    def build_key(self, task_type: str, context_checksum: str, template_version: str) -> str:
        payload = f"{task_type.upper()}:{context_checksum}:{template_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[EngineeringReasoningResult]:
        cached = self._cache.get(cache_key)
        if cached is None:
            self._misses += 1
            return None
        self._hits += 1
        return cached

    def set(self, cache_key: str, result: EngineeringReasoningResult) -> None:
        self._cache[cache_key] = result

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        return len(self._cache)

    def statistics(self) -> Dict[str, int]:
        return {
            "cache_size": self.size,
            "cache_hits": self._hits,
            "cache_misses": self._misses,
        }
