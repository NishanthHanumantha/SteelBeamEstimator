"""Load and cache markdown prompt templates."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from src.llm.prompts.prompt_models import TemplateMetadata, TemplateNotFoundError
from src.llm.prompts.prompt_registry import RegistryEntry

_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass
class LoadedTemplate:
    """Cached template payload."""

    cache_key: str
    raw_content: str
    body: str
    metadata: TemplateMetadata
    checksum: str


class TemplateLoader:
    """Read UTF-8 markdown templates with deterministic caching."""

    def __init__(self) -> None:
        self._cache: Dict[str, LoadedTemplate] = {}

    def load(self, entry: RegistryEntry) -> LoadedTemplate:
        path = entry.absolute_path
        if not path.exists():
            raise TemplateNotFoundError(f"Template file not found: {path}")

        mtime = path.stat().st_mtime_ns
        cache_key = self._cache_key(path, mtime)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        raw_content = path.read_text(encoding="utf-8")
        metadata, body = self._parse_frontmatter(raw_content, entry.template_name)
        checksum = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
        loaded = LoadedTemplate(
            cache_key=cache_key,
            raw_content=raw_content,
            body=body.strip(),
            metadata=metadata,
            checksum=checksum,
        )
        self._cache = {cache_key: loaded}
        return loaded

    @staticmethod
    def _cache_key(path: Path, mtime_ns: int) -> str:
        digest = hashlib.sha256(f"{path}|{mtime_ns}".encode("utf-8")).hexdigest()
        return digest

    @staticmethod
    def _parse_frontmatter(content: str, fallback_name: str) -> Tuple[TemplateMetadata, str]:
        match = _FRONTMATTER_PATTERN.match(content)
        if not match:
            return (
                TemplateMetadata(name=fallback_name.lower(), version="1.0"),
                content,
            )

        frontmatter = match.group(1)
        body = content[match.end() :]
        fields = TemplateLoader._parse_yaml_like(frontmatter)
        metadata = TemplateMetadata(
            name=str(fields.get("name", fallback_name.lower())),
            version=str(fields.get("version", "1.0")),
            author=str(fields.get("author", "")),
            description=str(fields.get("description", "")),
            extra={
                key: value
                for key, value in fields.items()
                if key not in {"name", "version", "author", "description"}
            },
        )
        return metadata, body

    @staticmethod
    def _parse_yaml_like(frontmatter: str) -> Dict[str, str]:
        fields: Dict[str, str] = {}
        for line in frontmatter.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            fields[key.strip()] = value.strip()
        return fields
