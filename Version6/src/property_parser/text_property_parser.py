"""Deterministic reinforcement text notation parser — Phase G.5.3.1."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.property_parser.property_parser_types import (
    PROP_BAR_TYPE,
    PROP_DIAMETER,
    PROP_QUANTITY,
    PROP_REINFORCEMENT_CODE,
    PROP_SPACING,
    UNIT_COUNT,
    UNIT_MILLIMETRE,
    UNIT_NONE,
)


@dataclass(frozen=True)
class ParsedReinforcementText:
    raw_text: str
    quantity: Optional[int] = None
    bar_type: Optional[str] = None
    diameter: Optional[int] = None
    spacing: Optional[int] = None
    spacing_pattern: Optional[str] = None
    parse_success: bool = False
    pattern_name: str = ""

    def as_properties(self) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        if self.quantity is not None:
            results[PROP_QUANTITY] = {
                "parsed_value": self.quantity,
                "normalized_value": self.quantity,
                "unit": UNIT_COUNT,
            }
        if self.bar_type is not None:
            results[PROP_BAR_TYPE] = {
                "parsed_value": self.bar_type,
                "normalized_value": self.bar_type,
                "unit": UNIT_NONE,
            }
        if self.diameter is not None:
            results[PROP_DIAMETER] = {
                "parsed_value": self.diameter,
                "normalized_value": f"{self.diameter} mm",
                "unit": UNIT_MILLIMETRE,
            }
        if self.spacing is not None:
            normalized = f"{self.spacing} mm"
            if self.spacing_pattern:
                normalized = f"{self.spacing} mm {self.spacing_pattern}"
            results[PROP_SPACING] = {
                "parsed_value": self.spacing,
                "normalized_value": normalized,
                "unit": UNIT_MILLIMETRE,
                "spacing_pattern": self.spacing_pattern,
            }
        if self.parse_success:
            code = self.reinforcement_code()
            if code:
                results[PROP_REINFORCEMENT_CODE] = {
                    "parsed_value": code,
                    "normalized_value": code,
                    "unit": UNIT_NONE,
                }
        return results

    def reinforcement_code(self) -> str:
        parts: List[str] = []
        if self.quantity is not None:
            parts.append(str(self.quantity))
        if self.bar_type:
            parts.append(self.bar_type)
        if self.diameter is not None:
            parts.append(str(self.diameter))
        code = "".join(parts) if parts else self.raw_text.strip()
        if self.spacing is not None:
            suffix = f"@{self.spacing}"
            if self.spacing_pattern:
                suffix = f"{suffix} {self.spacing_pattern}"
            code = f"{code}{suffix}"
        return code

    def get_for_type(self, property_type: str) -> Optional[Dict[str, Any]]:
        return self.as_properties().get(property_type)


class TextPropertyParser:
    """Parse engineering reinforcement notation from text."""

    _PATTERNS = (
        (
            "qty_bar_dia_at_spacing",
            re.compile(
                r"^(?P<qty>\d+)\s*(?P<bar>[YTR])\s*(?P<dia>\d+)\s*@\s*(?P<spc>\d+)\s*(?P<sppat>C/C|C\.C\.|CC)?$",
                re.IGNORECASE,
            ),
        ),
        (
            "bar_dia_at_spacing",
            re.compile(
                r"^(?P<bar>[YTR])(?P<dia>\d+)\s*@\s*(?P<spc>\d+)\s*(?P<sppat>C/C|C\.C\.|CC)?$",
                re.IGNORECASE,
            ),
        ),
        (
            "bar_dia_spaced",
            re.compile(
                r"^(?P<bar>[YTR])?(?P<dia>\d+)\s+@\s*(?P<spc>\d+)\s*(?P<sppat>C/C|C\.C\.|CC)?$",
                re.IGNORECASE,
            ),
        ),
        (
            "hash_notation",
            re.compile(r"^(?P<qty>\d+)\s*#\s*(?P<dia>\d+)$"),
        ),
        (
            "dash_notation",
            re.compile(
                r"^(?P<qty>\d+)\s*-\s*(?P<bar>[YTR])?(?P<dia>\d+)$",
                re.IGNORECASE,
            ),
        ),
        (
            "compact_qty_bar_dia",
            re.compile(
                r"^(?P<qty>\d+)\s*(?P<bar>[YTR])(?P<dia>\d+)$",
                re.IGNORECASE,
            ),
        ),
        (
            "compact_bar_dia",
            re.compile(r"^(?P<bar>[YTR])(?P<dia>\d+)$", re.IGNORECASE),
        ),
    )

    @classmethod
    def normalize_text(cls, text: str) -> str:
        cleaned = str(text or "").strip().upper()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.replace("C.C.", "C/C").replace("CC", "C/C")
        return cleaned

    @classmethod
    def parse(cls, text: str) -> ParsedReinforcementText:
        raw = str(text or "").strip()
        normalized = cls.normalize_text(raw)
        if not normalized:
            return ParsedReinforcementText(raw_text=raw, parse_success=False)

        for pattern_name, pattern in cls._PATTERNS:
            match = pattern.match(normalized)
            if not match:
                continue
            groups = match.groupdict()
            qty = cls._to_int(groups.get("qty"))
            bar = groups.get("bar")
            dia = cls._to_int(groups.get("dia"))
            spc = cls._to_int(groups.get("spc"))
            sppat = groups.get("sppat")
            if sppat:
                sppat = "C/C"
            return ParsedReinforcementText(
                raw_text=raw,
                quantity=qty,
                bar_type=bar.upper() if bar else None,
                diameter=dia,
                spacing=spc,
                spacing_pattern=sppat,
                parse_success=True,
                pattern_name=pattern_name,
            )

        return ParsedReinforcementText(raw_text=raw, parse_success=False)

    @staticmethod
    def _to_int(value: Optional[str]) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except ValueError:
            return None
