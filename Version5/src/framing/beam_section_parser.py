"""Parse beam section designation text into width and depth."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

# B11(150X600), B23 (250 X 700), with optional unicode multiply sign
_BEAM_MARK_SECTION = re.compile(
    r"^(B\d+)\s*\(\s*(\d+)\s*[xX×]\s*(\d+)\s*\)\s*$",
    re.IGNORECASE,
)
_PLAIN_SECTION = re.compile(
    r"^(\d+)\s*[xX×]\s*(\d+)\s*$",
    re.IGNORECASE,
)
_EMBEDDED_SECTION = re.compile(
    r"(B\d+)\s*\(\s*(\d+)\s*[xX×]\s*(\d+)\s*\)",
    re.IGNORECASE,
)

LABEL_SOURCE = "LABEL"
LABEL_CONFIDENCE = 1.0


@dataclass(frozen=True)
class ParsedSection:
    width: int
    depth: int
    designation: str
    source: str = LABEL_SOURCE
    confidence: float = LABEL_CONFIDENCE
    beam_mark: Optional[str] = None

    def to_resolution_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "depth": self.depth,
            "source": self.source,
            "confidence": self.confidence,
            "designation": self.designation,
        }


class BeamSectionParser:
    """Recognise common beam designation formats from framing plan labels."""

    def __init__(
        self,
        min_width: int = 100,
        max_width: int = 600,
        min_depth: int = 150,
        max_depth: int = 1500,
    ) -> None:
        self._min_width = min_width
        self._max_width = max_width
        self._min_depth = min_depth
        self._max_depth = max_depth

    def parse(self, text: str) -> Optional[ParsedSection]:
        normalized = self._normalize(text)
        if not normalized:
            return None

        match = _BEAM_MARK_SECTION.match(normalized)
        if match:
            beam_mark = match.group(1).upper()
            width = int(match.group(2))
            depth = int(match.group(3))
            if self._valid(width, depth):
                return ParsedSection(
                    width=width,
                    depth=depth,
                    designation=f"{width}x{depth}",
                    beam_mark=beam_mark,
                )

        match = _PLAIN_SECTION.match(normalized)
        if match:
            width = int(match.group(1))
            depth = int(match.group(2))
            if self._valid(width, depth):
                return ParsedSection(
                    width=width,
                    depth=depth,
                    designation=f"{width}x{depth}",
                )

        match = _EMBEDDED_SECTION.search(normalized)
        if match:
            beam_mark = match.group(1).upper()
            width = int(match.group(2))
            depth = int(match.group(3))
            if self._valid(width, depth):
                return ParsedSection(
                    width=width,
                    depth=depth,
                    designation=f"{width}x{depth}",
                    beam_mark=beam_mark,
                )
        return None

    def _normalize(self, text: str) -> str:
        cleaned = str(text).strip().replace("×", "X")
        cleaned = re.sub(r"\s+", "", cleaned)
        return cleaned.upper()

    def _valid(self, width: int, depth: int) -> bool:
        return (
            self._min_width <= width <= self._max_width
            and self._min_depth <= depth <= self._max_depth
        )
