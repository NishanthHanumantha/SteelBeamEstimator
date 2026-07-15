"""
GN Extractor — Part 2 of Phase GN.1 audit.

Parses the General Notes DXF and extracts every engineering parameter:
  - Grade of Steel
  - Grade of Concrete (per element)
  - Development Length Table
  - Concrete Cover
  - Spacer Bar Rules
  - Hook / Bend / Lap rules
  - IS456 / IS2502 constants

READ-ONLY: no production logic is changed.
"""
from __future__ import annotations
import re
import pathlib
from typing import Any, Dict, List, Optional, Tuple

from .gn_models import ExtractedParameter, SourceClass

# ---------------------------------------------------------------------------
# Regex patterns for engineering parameters
# ---------------------------------------------------------------------------
_RE_STEEL_GRADE   = re.compile(r"\bFe[0-9]{3}\b|\bHYSD\b|\bTOR\b|\bFY[-\s]?([0-9]{3})\b", re.I)
_RE_CONC_GRADE    = re.compile(r"\bM([0-9]{2})\b")
_RE_DEV_LENGTH    = re.compile(r"\bLd\b|\bL\.?D\b|development\s+length|anchorage", re.I)
_RE_DEV_TABLE     = re.compile(r"LD\s+FOR\s+FY[-\s]?([0-9]{3})", re.I)
_RE_COVER         = re.compile(r"(?:clear\s+cover|nominal\s+cover|cover)\s*[=:]\s*([0-9]+)\s*mm", re.I)
_RE_COVER_TABLE   = re.compile(r"([0-9]+)\s*mm", re.I)
_RE_SPACER        = re.compile(r"spacer|chair|cover\s+block", re.I)
_RE_HOOK_STD      = re.compile(r"standard\s+(?:90|135)\s*(?:degree)?\s*(?:hook|bend)", re.I)
_RE_HOOK_LEN      = re.compile(r"([0-9]+)\s*[xX]\s*db|([0-9]+)d\b", re.I)
_RE_LAP_TABLE     = re.compile(r"table[-\s]*1|lap.*table|lapped\s+splice", re.I)
_RE_LAP_MIN       = re.compile(r"(?:min(?:imum)?\s+)?(?:lap\s+)?(?:length\s+)?(?:shall\s+be\s+)?([0-9]+)\s*mm", re.I)
_RE_IS456         = re.compile(r"IS\s*456[-:\s]*([0-9]{4})?", re.I)
_RE_IS2502        = re.compile(r"IS\s*2502", re.I)
_RE_DENSITY       = re.compile(r"(?:steel\s+)?density|unit\s+weight", re.I)


def _clean(raw: str) -> str:
    """Strip DXF formatting codes and control characters."""
    raw = re.sub(r"\\[A-Za-z][^;]*;", "", raw)
    raw = re.sub(r"%%[A-Za-z]", "", raw)
    raw = raw.replace("\x00", "").strip()
    return raw


class GNExtractor:
    """
    Extracts engineering parameters from the General Notes DXF.
    Returns a list of ExtractedParameter records.
    """

    def __init__(self, gn_dxf_path: pathlib.Path):
        self._path = gn_dxf_path
        self._texts: List[Dict] = []

    # ------------------------------------------------------------------
    def extract(self) -> List[ExtractedParameter]:
        self._load_texts()
        params: List[ExtractedParameter] = []

        params.extend(self._extract_steel_grade())
        params.extend(self._extract_concrete_grade())
        params.extend(self._extract_development_length())
        params.extend(self._extract_cover())
        params.extend(self._extract_spacer())
        params.extend(self._extract_hook_bend())
        params.extend(self._extract_lap())
        params.extend(self._extract_is456())
        params.extend(self._extract_is2502())

        return params

    # ------------------------------------------------------------------
    def _load_texts(self) -> None:
        try:
            import ezdxf
            doc = ezdxf.readfile(str(self._path))
            msp = doc.modelspace()
            for e in msp:
                if e.dxftype() == "TEXT":
                    raw = e.dxf.text
                    layer = e.dxf.layer
                    x, y = e.dxf.insert.x, e.dxf.insert.y
                elif e.dxftype() == "MTEXT":
                    raw = e.plain_mtext() if hasattr(e, "plain_mtext") else e.text
                    layer = e.dxf.layer
                    x, y = e.dxf.insert.x, e.dxf.insert.y
                else:
                    continue
                c = _clean(raw)
                if c:
                    self._texts.append({"text": c, "layer": layer, "x": x, "y": y})
        except Exception as exc:
            self._texts = []
            print(f"[GNExtractor] DXF load error: {exc}")

    # ------------------------------------------------------------------
    def _make_param(
        self,
        name: str,
        source_text: str,
        parsed: Any,
        layer: str,
        classification: str = SourceClass.GENERAL_NOTES,
        notes: str = "",
    ) -> ExtractedParameter:
        return ExtractedParameter(
            parameter_name=name,
            source_drawing=self._path.name,
            source_layer=layer,
            source_text=source_text[:200],
            parsed_value=parsed,
            classification=classification,
            notes=notes,
        )

    # ------------------------------------------------------------------
    def _extract_steel_grade(self) -> List[ExtractedParameter]:
        results = []
        seen_grades = set()
        for item in self._texts:
            m = _RE_STEEL_GRADE.search(item["text"])
            if m:
                grade = m.group(0).upper()
                if grade not in seen_grades:
                    seen_grades.add(grade)
                    results.append(self._make_param(
                        "steel_grade",
                        item["text"],
                        grade,
                        item["layer"],
                        notes="Found in GN DXF via steel grade pattern"
                    ))
        # If found in dev length table header like "LD FOR FY-415"
        for item in self._texts:
            m = _RE_DEV_TABLE.search(item["text"])
            if m:
                grade = f"Fe{m.group(1)}"
                if grade not in seen_grades:
                    seen_grades.add(grade)
                    results.append(self._make_param(
                        "steel_grade",
                        item["text"],
                        grade,
                        item["layer"],
                        notes="Inferred from development length table header"
                    ))
        return results

    def _extract_concrete_grade(self) -> List[ExtractedParameter]:
        results = []
        seen = {}
        for item in self._texts:
            for m in _RE_CONC_GRADE.finditer(item["text"]):
                grade = f"M{m.group(1)}"
                if grade not in seen:
                    seen[grade] = item
        # Emit as a table if multiple grades found
        if seen:
            grades_list = sorted(seen.keys(), key=lambda g: int(g[1:]))
            results.append(self._make_param(
                "concrete_grade_table",
                " | ".join(seen[g]["text"][:50] for g in grades_list[:4]),
                grades_list,
                list(seen.values())[0]["layer"],
                notes="Development length table lists: " + ", ".join(grades_list),
            ))
        return results

    def _extract_development_length(self) -> List[ExtractedParameter]:
        results = []
        table_header = None
        for item in self._texts:
            # Table header "LD FOR FY-415"
            if _RE_DEV_TABLE.search(item["text"]):
                table_header = item["text"]
                results.append(self._make_param(
                    "development_length_table_header",
                    item["text"],
                    {"rule": item["text"], "standard": "IS 456:2000 Table 65"},
                    item["layer"],
                    notes="Development length table header found in GN DXF"
                ))
            if _RE_DEV_LENGTH.search(item["text"]):
                results.append(self._make_param(
                    "development_length_rule",
                    item["text"],
                    item["text"][:120],
                    item["layer"],
                    notes="Development length clause"
                ))
        # Look for numeric development length multipliers
        multipliers = []
        for item in self._texts:
            for m in re.finditer(r"(\d+)d\b", item["text"]):
                val = int(m.group(1))
                if 30 <= val <= 60:
                    multipliers.append({"text": item["text"][:80], "value": val, "layer": item["layer"]})
        if multipliers:
            results.append(self._make_param(
                "development_length_multiplier",
                multipliers[0]["text"],
                [m["value"] for m in multipliers],
                multipliers[0]["layer"],
                notes=f"Numeric development length multiplier(s) detected: {[m['value'] for m in multipliers]}"
            ))
        return results

    def _extract_cover(self) -> List[ExtractedParameter]:
        results = []
        for item in self._texts:
            m = _RE_COVER.search(item["text"])
            if m:
                results.append(self._make_param(
                    "concrete_cover_mm",
                    item["text"],
                    int(m.group(1)),
                    item["layer"],
                    notes="Explicit cover specification found"
                ))
        if not results:
            results.append(self._make_param(
                "concrete_cover_mm",
                "NOT FOUND IN GN DXF",
                None,
                "N/A",
                classification=SourceClass.HARDCODED,
                notes=(
                    "No explicit cover value found in GN DXF text. "
                    "Pipeline uses hardcoded 40mm (IS 456:2000 Table 16 — Beams)."
                )
            ))
        return results

    def _extract_spacer(self) -> List[ExtractedParameter]:
        results = []
        for item in self._texts:
            if _RE_SPACER.search(item["text"]):
                results.append(self._make_param(
                    "spacer_rule",
                    item["text"],
                    item["text"][:120],
                    item["layer"],
                    notes="Spacer / cover block clause found"
                ))
        if not results:
            results.append(self._make_param(
                "spacer_rule",
                "NOT EXPLICITLY SPECIFIED IN GN DXF",
                None,
                "N/A",
                classification=SourceClass.HARDCODED,
                notes="No spacer bar rules found in GN DXF."
            ))
        return results

    def _extract_hook_bend(self) -> List[ExtractedParameter]:
        results = []
        for item in self._texts:
            if _RE_HOOK_STD.search(item["text"]):
                # Extract hook length multipliers
                lengths = _RE_HOOK_LEN.findall(item["text"])
                parsed = [int(a or b) for a, b in lengths if (a or b)]
                results.append(self._make_param(
                    "hook_bend_rule",
                    item["text"],
                    {"rule": item["text"][:120], "multipliers_xdb": parsed},
                    item["layer"],
                    notes="Standard hook/bend specification found"
                ))
        # Also collect xdb mentions
        for item in self._texts:
            for m in re.finditer(r"([0-9]+)\s*[xX]\s*db", item["text"]):
                val = int(m.group(1))
                results.append(self._make_param(
                    "hook_length_xdb",
                    item["text"],
                    f"{val}xdb",
                    item["layer"],
                    notes=f"{val}xdb hook length mentioned"
                ))
        return results

    def _extract_lap(self) -> List[ExtractedParameter]:
        results = []
        for item in self._texts:
            if _RE_LAP_TABLE.search(item["text"]):
                results.append(self._make_param(
                    "lap_length_table_ref",
                    item["text"],
                    item["text"][:120],
                    item["layer"],
                    notes="Lap length reference to Table-1 in GN"
                ))
        # Minimum lap
        for item in self._texts:
            if "300mm" in item["text"] and "lap" in item["text"].lower():
                results.append(self._make_param(
                    "lap_length_minimum_mm",
                    item["text"],
                    300,
                    item["layer"],
                    notes="Minimum lap splice length = 300mm"
                ))
        return results

    def _extract_is456(self) -> List[ExtractedParameter]:
        results = []
        seen = set()
        for item in self._texts:
            if _RE_IS456.search(item["text"]):
                key = item["text"][:50]
                if key not in seen:
                    seen.add(key)
                    results.append(self._make_param(
                        "IS456_reference",
                        item["text"],
                        "IS 456:2000",
                        item["layer"],
                        notes="IS 456 standard reference found"
                    ))
        return results

    def _extract_is2502(self) -> List[ExtractedParameter]:
        results = []
        for item in self._texts:
            if _RE_IS2502.search(item["text"]):
                results.append(self._make_param(
                    "IS2502_reference",
                    item["text"],
                    "IS 2502",
                    item["layer"],
                    notes="IS 2502 standard reference found"
                ))
        return results
