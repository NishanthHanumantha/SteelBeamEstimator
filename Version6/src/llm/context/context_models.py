"""Typed models for engineering context infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


class ContextValidationError(ValueError):
    """Raised when engineering context fails validation."""


@dataclass
class ContextMetadata:
    generated_timestamp: str
    source_modules: List[str]
    schema_version: str
    builder_version: str
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextSection:
    section_name: str
    priority: str
    content: Dict[str, Any]
    token_estimate: int
    checksum: str


@dataclass
class EngineeringContext:
    context_id: str
    context_version: str
    task_type: str
    sections: List[ContextSection]
    estimated_tokens: int
    checksum: str
    metadata: ContextMetadata

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
