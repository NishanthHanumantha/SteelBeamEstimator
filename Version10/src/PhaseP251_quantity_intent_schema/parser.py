"""
Deterministic quantity-expression parsers.

Longitudinal: N-Ydd, composites N-Ydd + M-Yee
Stirrup: reuse Phase SI.1 StirrupNotationParser (no duplication of logic).
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

from .config import (
    SEM_LONGITUDINAL_BAR,
    SEM_STIRRUP,
    SEM_UNKNOWN,
    SOURCE_ANNOTATION_TEXT,
    SOURCE_STIRRUP_PATTERN,
    SOURCE_UNRESOLVED,
    STATUS_COMPOSITE,
    STATUS_EXPLICIT,
    STATUS_SPACING_BASED,
    STATUS_UNRESOLVED,
)
from .models import QuantityComponent

# Explicit longitudinal: 4-Y25, 7Y20, 2 - Y16
_LONGITUDINAL_RE = re.compile(
    r"(?P<qty>\d+)\s*-?\s*Y\s*(?P<dia>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Ambiguous range: 4/6-Y20, 4 TO 6-Y20
_AMBIGUOUS_RE = re.compile(
    r"(?P<a>\d+)\s*(?:/|TO|–|-)\s*(?P<b>\d+)\s*-?\s*Y\s*(?P<dia>\d+)",
    re.IGNORECASE,
)

# Stirrup-like: has @ spacing
_STIRRUP_HINT_RE = re.compile(r"Y\s*\d+.*@", re.IGNORECASE)


@dataclass
class ParseResult:
    semantic_hint: str = SEM_UNKNOWN
    quantity_status: str = STATUS_UNRESOLVED
    quantity_source: str = SOURCE_UNRESOLVED
    quantity_expression: Optional[str] = None
    quantity_value: Optional[int] = None
    diameter_expression: Optional[str] = None
    diameter_value_mm: Optional[float] = None
    spacing_expression: Optional[str] = None
    spacing_value_mm: Optional[float] = None
    spacing_values_mm: List[float] = field(default_factory=list)
    leg_expression: Optional[str] = None
    leg_count: Optional[int] = None
    unit: str = "COUNT"
    components: List[QuantityComponent] = field(default_factory=list)
    parse_note: str = ""
    ambiguous: bool = False


def normalize_text(raw: str) -> str:
    t = (raw or "").strip()
    t = re.sub(r"\s+", "", t)
    return t.upper()


def _load_stirrup_parser():
    """Import SI.1 StirrupNotationParser without mutating sys.path permanently."""
    si1 = (
        Path(__file__).resolve().parents[1]
        / "PhaseSI.1_stirrup_improvement"
    )
    if str(si1) not in sys.path:
        sys.path.insert(0, str(si1))
    from stirrup_notation_parser import StirrupNotationParser  # type: ignore

    return StirrupNotationParser()


def parse_stirrup(raw: str) -> ParseResult:
    parser = _load_stirrup_parser()
    parsed = parser.parse(raw)
    if not parsed.is_parseable or not parsed.spacings_mm:
        return ParseResult(
            semantic_hint=SEM_STIRRUP,
            quantity_status=STATUS_UNRESOLVED,
            quantity_source=SOURCE_STIRRUP_PATTERN,
            quantity_expression=raw,
            parse_note=parsed.parse_note or "stirrup_not_parseable",
        )
    spacings = [float(x) for x in parsed.spacings_mm]
    return ParseResult(
        semantic_hint=SEM_STIRRUP,
        quantity_status=STATUS_SPACING_BASED,
        quantity_source=SOURCE_STIRRUP_PATTERN,
        quantity_expression=raw,
        # Do NOT set quantity_value = legs (not longitudinal piece count)
        quantity_value=None,
        diameter_expression=f"Y{int(parsed.diameter_mm)}"
        if float(parsed.diameter_mm).is_integer()
        else f"Y{parsed.diameter_mm}",
        diameter_value_mm=float(parsed.diameter_mm),
        spacing_expression="/".join(str(int(x)) for x in spacings) if spacings else None,
        spacing_value_mm=spacings[0] if len(spacings) == 1 else None,
        spacing_values_mm=spacings,
        leg_expression=f"{parsed.legs}L",
        leg_count=int(parsed.legs),
        unit="SPACING_MM",
        parse_note=parsed.parse_note or "stirrup_parsed",
    )


def parse_longitudinal_single(raw: str) -> Optional[ParseResult]:
    m = _LONGITUDINAL_RE.fullmatch(normalize_text(raw).replace(" ", ""))
    # also allow raw with spaces via search on cleaned
    cleaned = normalize_text(raw)
    m = _LONGITUDINAL_RE.fullmatch(cleaned)
    if not m:
        return None
    qty = int(m.group("qty"))
    dia = float(m.group("dia"))
    return ParseResult(
        semantic_hint=SEM_LONGITUDINAL_BAR,
        quantity_status=STATUS_EXPLICIT,
        quantity_source=SOURCE_ANNOTATION_TEXT,
        quantity_expression=f"{qty}-Y{int(dia) if dia.is_integer() else dia}",
        quantity_value=qty,
        diameter_expression=f"Y{int(dia) if dia.is_integer() else dia}",
        diameter_value_mm=dia,
        unit="COUNT",
        components=[
            QuantityComponent(
                quantity_expression=f"{qty}-Y{int(dia) if dia.is_integer() else dia}",
                quantity_value=qty,
                diameter_expression=f"Y{int(dia) if dia.is_integer() else dia}",
                diameter_value_mm=dia,
                parse_ok=True,
            )
        ],
        parse_note="longitudinal_explicit",
    )


def parse_composite(raw: str) -> Optional[ParseResult]:
    """4-Y20 + 2-Y16 → COMPOSITE with components (do not flatten to 6)."""
    parts = re.split(r"\s*\+\s*", (raw or "").strip())
    if len(parts) < 2:
        return None
    comps: List[QuantityComponent] = []
    for p in parts:
        single = parse_longitudinal_single(p)
        if single is None or single.quantity_value is None:
            return None
        comps.extend(single.components)
    return ParseResult(
        semantic_hint=SEM_LONGITUDINAL_BAR,
        quantity_status=STATUS_COMPOSITE,
        quantity_source=SOURCE_ANNOTATION_TEXT,
        quantity_expression=(raw or "").strip(),
        quantity_value=None,  # not flattened
        diameter_expression=None,
        diameter_value_mm=None,
        unit="COUNT",
        components=comps,
        parse_note="composite_longitudinal",
    )


def parse_ambiguous(raw: str) -> Optional[ParseResult]:
    cleaned = normalize_text(raw)
    # Avoid matching 100/150/100 stirrup spacings
    if "@" in cleaned:
        return None
    m = _AMBIGUOUS_RE.search((raw or "").strip())
    if not m:
        return None
    a, b = int(m.group("a")), int(m.group("b"))
    if a == b:
        return None
    dia = float(m.group("dia"))
    return ParseResult(
        semantic_hint=SEM_LONGITUDINAL_BAR,
        quantity_status=STATUS_UNRESOLVED,
        quantity_source=SOURCE_UNRESOLVED,
        quantity_expression=(raw or "").strip(),
        diameter_expression=f"Y{int(dia) if dia.is_integer() else dia}",
        diameter_value_mm=dia,
        ambiguous=True,
        parse_note="AMBIGUOUS_QUANTITY",
    )


def parse_quantity_expression(
    raw: str,
    *,
    chain_semantic_type: Optional[str] = None,
) -> ParseResult:
    text = (raw or "").strip()
    if not text:
        return ParseResult(parse_note="empty_text")

    sem = (chain_semantic_type or "").strip()

    # Prefer stirrup path when semantic or @notation indicates stirrup
    if sem == "StirrupNote" or _STIRRUP_HINT_RE.search(text):
        # Guard: pure longitudinal never has @
        if "@" in text or sem == "StirrupNote":
            r = parse_stirrup(text)
            # fix spacing_expression
            if r.spacing_values_mm:
                r.spacing_expression = "/".join(str(int(x)) for x in r.spacing_values_mm)
            return r

    amb = parse_ambiguous(text)
    if amb is not None:
        return amb

    comp = parse_composite(text)
    if comp is not None:
        return comp

    single = parse_longitudinal_single(text)
    if single is not None:
        return single

    # BarCallout that failed patterns
    if sem == "BarCallout":
        return ParseResult(
            semantic_hint=SEM_LONGITUDINAL_BAR,
            quantity_status=STATUS_UNRESOLVED,
            quantity_source=SOURCE_UNRESOLVED,
            quantity_expression=text,
            parse_note="bar_callout_unparsed",
        )

    return ParseResult(
        quantity_expression=text,
        quantity_status=STATUS_UNRESOLVED,
        quantity_source=SOURCE_UNRESOLVED,
        parse_note="unrecognized_expression",
    )
