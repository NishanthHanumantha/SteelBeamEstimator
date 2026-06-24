"""Utilities for stripping CAD formatting from raw annotation text."""

import re

_ANNOTATION_PREFIX = re.compile(r"\\A\d+;", re.IGNORECASE)
_PXT_PREFIX = re.compile(r"\\pxt\d+;", re.IGNORECASE)
_UNDERLINE_TOGGLE = re.compile(r"%%[A-Za-z]")
_MULTI_SPACE = re.compile(r"\s+")


class AnnotationTextCleaner:
    """Remove CAD MTEXT/TEXT codes while preserving engineering meaning."""

    def clean(self, raw_text: str) -> str:
        text = str(raw_text).replace("\\P", " ").replace("\n", " ").replace("\r", " ")
        text = _UNDERLINE_TOGGLE.sub("", text)
        text = text.replace("\\L", "")
        text = _ANNOTATION_PREFIX.sub("", text)
        text = _PXT_PREFIX.sub("", text)
        text = re.sub(r"\\[A-Za-z]+\d*;", "", text)
        text = text.replace("\\", "")
        text = re.sub(r"[{}]", "", text)
        text = _MULTI_SPACE.sub(" ", text).strip()
        return text

    def clean_pair(self, raw_text: str) -> tuple[str, str]:
        return raw_text, self.clean(raw_text)
