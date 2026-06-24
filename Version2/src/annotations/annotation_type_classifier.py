"""Classify cleaned reinforcement annotations into engineering categories."""

import re
from typing import Literal

from src.annotations.annotation_text_cleaner import AnnotationTextCleaner

AnnotationType = Literal[
    "BAR",
    "STIRRUP",
    "DIMENSION",
    "ANCHORAGE",
    "SIDE_FACE_REINF",
    "NOTE",
    "UNKNOWN",
]

_STIRRUP_AT = "@"
_STIRRUP_CC = "C/C"
_SIDE_FACE_PATTERN = re.compile(
    r"SIDE\s*\.?\s*FACE|(?:^|[^A-Z])SFR(?:[^A-Z]|$)|S\.F\.R",
    re.IGNORECASE,
)
_ANCHORAGE_PATTERN = re.compile(r"LD", re.IGNORECASE)
_DIMENSION_PATTERN = re.compile(r"^\d+$")
_BAR_PATTERN = re.compile(r"^\d+-?Y\d+(?:\s*,\s*\d+-?Y\d+)*$", re.IGNORECASE)
_BAR_TOKEN_PATTERN = re.compile(r"\d+-?Y\d+", re.IGNORECASE)
_NOTE_PATTERN = re.compile(
    r"TYPICAL|PROVIDE|CONTINUE|DETAIL|SECTION",
    re.IGNORECASE,
)


class AnnotationTypeClassifier:
    """Assign exactly one engineering category per annotation."""

    def __init__(self) -> None:
        self._cleaner = AnnotationTextCleaner()

    def classify(self, raw_text: str) -> tuple[str, str, AnnotationType]:
        clean_text = self._cleaner.clean(raw_text)
        annotation_type = self._classify_clean_text(clean_text)
        return raw_text, clean_text, annotation_type

    def _classify_clean_text(self, clean_text: str) -> AnnotationType:
        normalized = clean_text.strip()
        if not normalized:
            return "UNKNOWN"

        upper = normalized.upper()

        if _STIRRUP_AT in normalized or _STIRRUP_CC in upper:
            return "STIRRUP"

        if _SIDE_FACE_PATTERN.search(normalized):
            return "SIDE_FACE_REINF"

        if _ANCHORAGE_PATTERN.search(normalized):
            return "ANCHORAGE"

        if _DIMENSION_PATTERN.match(normalized):
            return "DIMENSION"

        if self._is_bar(normalized):
            return "BAR"

        if _NOTE_PATTERN.search(normalized):
            return "NOTE"

        return "UNKNOWN"

    @staticmethod
    def _is_bar(normalized: str) -> bool:
        if "@" in normalized:
            return False
        if _BAR_PATTERN.match(normalized):
            return True
        tokens = _BAR_TOKEN_PATTERN.findall(normalized)
        if not tokens:
            return False
        remainder = _BAR_TOKEN_PATTERN.sub("", normalized)
        remainder = re.sub(r"[\s,()]+", "", remainder)
        return remainder == ""
