"""Normalize drawing title text for anchor matching."""

import re

from src.utils.text_cleaner import clean_dxf_text

_MTEXT_PREFIX = re.compile(r"\\[A-Za-z][^;\\]*;")
_WHITESPACE = re.compile(r"\s+")


def normalize_drawing_text(raw_text: str) -> str:
    """Strip AutoCAD codes and collapse whitespace for title matching."""
    text = clean_dxf_text(str(raw_text))
    text = _MTEXT_PREFIX.sub("", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text
