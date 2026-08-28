"""
Cover Table Parser — TABLE 2 in the General Notes DXF.

Table structure (from spatial analysis, x~1549-1660, y~699-553):

  Headers:  SL NO | MEMBER | CLEAR COVER | [MIX/CONCRETE GRADE] | [GRADE OF STEEL]
  Rows by SL:
   1. FOOTING                       cover=50, M30, Fe550
   2. COLUMN PEDESTAL               cover=40, M30, Fe550
   3. COLUMNS/WALL ABOVE PLINTH     cover=40, M30, Fe550
   4. PLINTH BEAM                   cover=30, M30, Fe550
   5. RETAINING WALLS               cover=30, M30, Fe550
   6. COLUMNS/WALL BELOW PLINTH     cover=40, M30, Fe550
   7. BEAM IN SUPERSTRUCTURE        cover=30, M30, Fe550
   8. SLAB IN SUPERSTRUCTURE        cover=30, M30, Fe550
   9. LINTELS                       cover=25, M30, Fe550
  10. OVERHEAD WATER TANK BOTTOM    cover=30, M30, Fe550
  11. OVERHEAD WATER TANK WALLS     cover=30, M30, Fe550
  12. OVERHEAD WATER TANK TOP SLAB  cover=30, M30, Fe550

Strategy: spatial scan of TABLE 2 region, group by Y row,
match columns by X proximity to header X positions.
"""
from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple

from .general_notes_text_extractor import DXFTextItem, GeneralNotesTextExtractor
from .engineering_context_model import CoverRule

# Spatial bounds of TABLE 2 (from probe analysis)
_TABLE2_X_MIN = 1540.0
_TABLE2_X_MAX = 1680.0
_TABLE2_HEADER_Y = 723.0   # approx y of "TABLE 2" label

_MEMBER_KEYWORDS = re.compile(
    r"FOOTING|COLUMN|PEDESTAL|PLINTH|BEAM|SLAB|RETAINING|WALL|LINTEL|OVERHEAD|TANK|STAIR|UNDERGROUND|UNDER GROUND",
    re.I,
)
_CONCRETE_GRADE_PAT = re.compile(r"\bM(20|25|30|35|40)\b", re.I)
_STEEL_GRADE_PAT    = re.compile(r"\bFe\s*(\d{3})\b", re.I)
_COVER_VALUE_PAT    = re.compile(r"^\*?\s*(\d{2,3})\s*\*?$")

_Y_ROW_TOL = 5.0


def _is_cover_value(text: str) -> Optional[int]:
    """Return the cover mm value if the text is a bare numeric cover, else None."""
    m = _COVER_VALUE_PAT.match(text.strip())
    if m:
        v = int(m.group(1))
        if 10 <= v <= 100:
            return v
    return None


class CoverParser:
    """
    Parses the clear cover table (TABLE 2) from the General Notes DXF.
    Returns a list of CoverRule objects.
    """

    def __init__(self, extractor: GeneralNotesTextExtractor):
        self._ext = extractor

    def parse(self) -> Tuple[List[CoverRule], List[str]]:
        all_items = self._ext.extract()

        # Locate TABLE 2 anchor
        table2_anchor = self._ext.find_table_title(2)
        if table2_anchor is None:
            table2_anchor = self._ext.find_anchor(r"^\s*TABLE\s+2\s*$")
        if table2_anchor is None:
            return self._fallback_parse(all_items)

        # Scan TABLE 2 region: from anchor Y downward to ~anchor.y - 200.
        # X window is relative to the TABLE 2 label so non-Galera sheets still parse.
        y_top    = table2_anchor.y + 5.0
        y_bottom = table2_anchor.y - 220.0
        x_min = table2_anchor.x - 30.0
        x_max = table2_anchor.x + 280.0

        region = self._ext.items_in_region(x_min, x_max, y_bottom, y_top)
        if not region:
            region = self._ext.items_in_region(
                _TABLE2_X_MIN, _TABLE2_X_MAX, y_bottom, y_top
            )
        region.sort(key=lambda i: -i.y)

        if not region:
            return self._fallback_parse(all_items)

        return self._parse_region(region)

    def _parse_region(
        self, region: List[DXFTextItem]
    ) -> Tuple[List[CoverRule], List[str]]:
        warnings: List[str] = []

        # Find header row for column positions
        cover_col_x: Optional[float] = None
        conc_col_x:  Optional[float] = None
        steel_col_x: Optional[float] = None
        member_col_x: Optional[float] = None

        for item in region:
            if "CLEAR COVER" in item.text.upper():
                cover_col_x = item.x
            if "CONCRETE" in item.text.upper() or "MIX" in item.text.upper():
                conc_col_x = item.x
            if "STEEL" in item.text.upper() or "GRADE OF" in item.text.upper():
                steel_col_x = item.x
            if "MEMBER" in item.text.upper():
                member_col_x = item.x

        # If we found cover column, use spatial matching
        # Otherwise fallback to scanning member names
        if cover_col_x is None:
            cover_col_x = 1612.0   # from probe data

        # Group items by Y-row
        rows = self._group_by_y(region)

        rules: List[CoverRule] = []
        for row in rows:
            rule = self._parse_row(
                row, cover_col_x,
                conc_col_x  or 1646.0,
                steel_col_x or 1660.0,
                member_col_x or 1556.0,
            )
            if rule:
                rules.append(rule)

        if not rules:
            warnings.append("CoverParser: No cover rules extracted from TABLE 2 region.")
            return self._fallback_rules(), warnings

        return rules, warnings

    def _parse_row(
        self,
        row: List[DXFTextItem],
        cover_x: float,
        conc_x: float,
        steel_x: float,
        member_x: float,
    ) -> Optional[CoverRule]:
        member_text = ""
        cover_mm: Optional[int] = None
        concrete_grade = "UNKNOWN"
        steel_grade = "UNKNOWN"

        for item in sorted(row, key=lambda i: i.x):
            text = item.text.strip()
            # Member name — widest X range, non-numeric
            if abs(item.x - member_x) < 80 and _MEMBER_KEYWORDS.search(text) and not text.lstrip("(*").isdigit():
                member_text = text

            # Cover value — integer close to cover column
            if abs(item.x - cover_x) < 20:
                v = _is_cover_value(text)
                if v:
                    cover_mm = v

            # Concrete grade
            m = _CONCRETE_GRADE_PAT.search(text)
            if m and abs(item.x - conc_x) < 25:
                concrete_grade = f"M{m.group(1)}"

            # Steel grade
            m = _STEEL_GRADE_PAT.search(text)
            if m and abs(item.x - steel_x) < 25:
                steel_grade = f"Fe{m.group(1)}"

        if member_text and cover_mm is not None:
            return CoverRule(
                element_type=member_text.upper(),
                cover_mm=cover_mm,
                concrete_grade=concrete_grade,
                steel_grade=steel_grade,
                source="GN_DXF_TABLE_2",
            )
        return None

    def _group_by_y(
        self, items: List[DXFTextItem], tol: float = _Y_ROW_TOL
    ) -> List[List[DXFTextItem]]:
        if not items:
            return []
        sorted_items = sorted(items, key=lambda i: -i.y)
        clusters: List[List[DXFTextItem]] = [[sorted_items[0]]]
        for item in sorted_items[1:]:
            if abs(item.y - clusters[-1][0].y) <= tol:
                clusters[-1].append(item)
            else:
                clusters.append([item])
        return clusters

    def _fallback_parse(
        self, all_items: List[DXFTextItem]
    ) -> Tuple[List[CoverRule], List[str]]:
        warnings = ["CoverParser: TABLE 2 anchor not found; using fallback rules."]
        return self._fallback_rules(), warnings

    def _fallback_rules(self) -> List[CoverRule]:
        """IS 456:2000 Table 16 defaults as absolute fallback."""
        return [
            CoverRule("BEAM IN SUPERSTRUCTURE",       30, "M30", "Fe550", "FALLBACK_IS456", "GN TABLE 2 not parsed"),
            CoverRule("SLAB IN SUPERSTRUCTURE",       30, "M30", "Fe550", "FALLBACK_IS456", "GN TABLE 2 not parsed"),
            CoverRule("COLUMN",                       40, "M30", "Fe550", "FALLBACK_IS456", "GN TABLE 2 not parsed"),
            CoverRule("FOOTING",                      50, "M30", "Fe550", "FALLBACK_IS456", "GN TABLE 2 not parsed"),
        ]
