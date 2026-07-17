"""Deterministic cache for engineering contexts."""

from __future__ import annotations

import hashlib
from typing import Dict, Optional

from src.llm.context.context_models import EngineeringContext
from src.llm.context.context_serializer import ContextSerializer


class ContextCache:
    """Cache engineering contexts by deterministic input checksum."""

    def __init__(self) -> None:
        self._cache: Dict[str, EngineeringContext] = {}
        self._input_checksums: Dict[str, str] = {}

    def build_key(self, task_type: str, engineering_objects: Dict[str, object]) -> str:
        serialized = ContextSerializer.serialize(engineering_objects)
        payload = {
            "task_type": task_type.upper(),
            "engineering_objects": serialized,
        }
        digest = hashlib.sha256(ContextSerializer.to_text(payload).encode("utf-8")).hexdigest()
        return digest

    def get(self, cache_key: str, input_checksum: str) -> Optional[EngineeringContext]:
        cached = self._cache.get(cache_key)
        if cached is None:
            return None
        if self._input_checksums.get(cache_key) != input_checksum:
            self.invalidate(cache_key)
            return None
        return cached

    def set(self, cache_key: str, input_checksum: str, context: EngineeringContext) -> None:
        self._cache[cache_key] = context
        self._input_checksums[cache_key] = input_checksum

    def invalidate(self, cache_key: str) -> None:
        self._cache.pop(cache_key, None)
        self._input_checksums.pop(cache_key, None)

    def clear(self) -> None:
        self._cache.clear()
        self._input_checksums.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
