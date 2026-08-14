"""Classify stirrup notation quality from DXF text. Runtime — no evaluation oracles."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from PhaseP256_controlled_field_level_vision_experiment.field_validator import (
    validate_diameter,
    validate_legs,
    validate_spacing,
)

from .config import (
    QUALITY_CLEAN,
    QUALITY_MALFORMED,
    QUALITY_OCR,
    QUALITY_PARTIAL,
    QUALITY_SCHEDULE,
)


def _load_parse_stirrup_callout():
    """Load SI.0 parser by path — package name contains a dot."""
    path = (
        Path(__file__).resolve().parents[1]
        / "PhaseSI.0_stirrup_recovery"
        / "si0_stirrup_annotation_parser.py"
    )
    spec = importlib.util.spec_from_file_location("si0_stirrup_annotation_parser", path)
    if spec is None or spec.loader is None:
        raise ImportError("SI.0 stirrup parser is unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_stirrup_callout


parse_stirrup_callout = _load_parse_stirrup_callout()

_PREFIX_RE = re.compile(r"(?P<legs>\d+)\s*L\s*-?\s*Y\s*(?P<dia>\d+)", re.IGNORECASE)
_SLASH_RE = re.compile(r"\d+\s*/\s*\d+")
_GLYPH = "\\X"


def _as_list(v: Any) -> List[int]:
    out: List[int] = []
    for x in v or []:
        try:
            out.append(int(round(float(x))))
        except Exception:
            continue
    return out


def has_ocr_glyph(text: str) -> bool:
    return _GLYPH in str(text or "")


def strip_ocr_glyph(text: str) -> str:
    return str(text or "").replace(_GLYPH, "")


def slash_schedule_in_text(text: str) -> bool:
    return bool(_SLASH_RE.search(str(text or "")))


def _complete(parsed: Dict[str, Any]) -> bool:
    return bool(
        parsed.get("is_parseable")
        and parsed.get("diameter_mm") is not None
        and parsed.get("spacings_mm")
    )


def parse_notation(text: str) -> Dict[str, Any]:
    raw = str(text or "")
    parsed_raw = parse_stirrup_callout(raw)
    stripped = strip_ocr_glyph(raw)
    parsed_strip = parse_stirrup_callout(stripped) if has_ocr_glyph(raw) else parsed_raw
    prefix = _PREFIX_RE.search(raw.replace(" ", ""))
    return {
        "raw_parseable": _complete(parsed_raw),
        "stripped_parseable": _complete(parsed_strip),
        "has_ocr_glyph": has_ocr_glyph(raw),
        "slash_schedule": slash_schedule_in_text(raw),
        "explicit_prefix": bool(prefix),
        "legs": (parsed_strip.get("legs") if _complete(parsed_strip) else None)
        or (int(prefix.group("legs")) if prefix else None),
        "diameter_mm": parsed_strip.get("diameter_mm")
        if _complete(parsed_strip)
        else (float(prefix.group("dia")) if prefix else None),
        "spacings_mm": list(parsed_strip.get("spacings_mm") or []) if _complete(parsed_strip) else [],
        "bar_label": parsed_strip.get("bar_label") if _complete(parsed_strip) else None,
        "parsed": parsed_strip,
    }


def classify_annotation_quality(text: str) -> str:
    info = parse_notation(text)
    if info["raw_parseable"] and not info["has_ocr_glyph"]:
        return QUALITY_CLEAN
    if info["slash_schedule"] and info["stripped_parseable"]:
        return QUALITY_SCHEDULE
    if info["has_ocr_glyph"] and info["stripped_parseable"]:
        return QUALITY_OCR
    if not info["stripped_parseable"] and not info["explicit_prefix"]:
        return QUALITY_MALFORMED
    return QUALITY_PARTIAL


def vision_matches_notation(
    *,
    vis_diameter: Any,
    vis_legs: Any,
    vis_spacing: Sequence[int],
    notation: Dict[str, Any],
) -> bool:
    try:
        if notation.get("diameter_mm") is not None and vis_diameter is not None:
            if abs(float(notation["diameter_mm"]) - float(vis_diameter)) >= 0.6:
                return False
        if notation.get("legs") is not None and vis_legs is not None:
            if int(notation["legs"]) != int(vis_legs):
                return False
    except Exception:
        return False
    nsp = _as_list(notation.get("spacings_mm"))
    vsp = _as_list(vis_spacing)
    if nsp and vsp and nsp != vsp:
        return False
    return True


def field_validity(*, diameter: Any, legs: Any, spacing: Sequence[int]) -> Dict[str, Any]:
    dia_ok, dia_err = (True, []) if diameter is None else validate_diameter(diameter)
    legs_ok, legs_err = (True, []) if legs is None else validate_legs(legs)
    sp_ok, sp_err = (True, []) if not spacing else validate_spacing(list(spacing))
    return {
        "diameter_ok": dia_ok,
        "legs_ok": legs_ok,
        "spacing_ok": sp_ok,
        "errors": list(dia_err) + list(legs_err) + list(sp_err),
    }


__all__ = [
    "classify_annotation_quality",
    "field_validity",
    "has_ocr_glyph",
    "parse_notation",
    "slash_schedule_in_text",
    "strip_ocr_glyph",
    "vision_matches_notation",
]
