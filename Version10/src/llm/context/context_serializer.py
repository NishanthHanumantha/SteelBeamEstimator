"""Deterministic serialization for engineering context."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


class ContextSerializer:
    """Convert engineering data into stable structured dictionaries."""

    @staticmethod
    def serialize(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): ContextSerializer.serialize(value[key])
                for key in sorted(value.keys(), key=lambda item: str(item))
            }
        if isinstance(value, list):
            return [ContextSerializer.serialize(item) for item in value]
        if isinstance(value, tuple):
            return [ContextSerializer.serialize(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    @staticmethod
    def to_text(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @staticmethod
    def checksum(payload: Dict[str, Any]) -> str:
        return hashlib.sha256(ContextSerializer.to_text(payload).encode("utf-8")).hexdigest()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    @staticmethod
    def sections_to_prompt_payload(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        ordered: Dict[str, Any] = {}
        for section in sections:
            name = str(section.get("section_name"))
            ordered[name] = section.get("content")
        return ordered
