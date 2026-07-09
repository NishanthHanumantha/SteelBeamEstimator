"""Deterministic response parsing helpers."""

from __future__ import annotations

import re
from typing import Any


def extract_text(response: Any) -> str:
    """Extract plain text from an Anthropic messages response."""
    content = getattr(response, "content", None)
    if not content:
        raise ValueError("Response has no content blocks")
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            return str(text)
    raise ValueError("Response contains no text blocks")


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace without changing meaning."""
    return re.sub(r"[ \t]+", " ", text).strip()


def strip_markdown(text: str) -> str:
    """Remove lightweight markdown decoration markers."""
    cleaned = text
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    return cleaned.strip()


def strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks while preserving inline content."""
    return re.sub(r"```[\w]*\n?.*?```", "", text, flags=re.DOTALL).strip()
