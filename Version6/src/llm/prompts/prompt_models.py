"""Prompt template domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class TemplateMetadata:
    """Parsed YAML frontmatter from a template file."""

    name: str
    version: str = "1.0"
    author: str = ""
    description: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptTemplate:
    """Rendered prompt artifact with lineage metadata."""

    template_name: str
    template_path: str
    raw_template: str
    rendered_prompt: str
    variables: Dict[str, Any]
    checksum: str
    version: str
    created_timestamp: str
    metadata: Optional[TemplateMetadata] = None

    @staticmethod
    def now_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()


class TemplateNotFoundError(FileNotFoundError):
    """Raised when a template file or registry entry cannot be resolved."""


class TemplateValidationError(ValueError):
    """Raised when a template fails structural validation."""
