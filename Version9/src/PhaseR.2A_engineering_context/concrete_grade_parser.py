"""
Concrete Grade Parser.

Extracts the concrete grade table from TABLE 2 and identifies the
project-level concrete grades for each element type.
"""
from __future__ import annotations
import re
from typing import Dict, List, Set, Tuple

from .general_notes_text_extractor import GeneralNotesTextExtractor

_CONC_PAT = re.compile(r"\bM(20|25|30|35|40)\b", re.I)

# TABLE 2 region
_CONC_COL_X_MIN = 1635.0
_CONC_COL_X_MAX = 1660.0
_TABLE2_Y_TOP   = 725.0
_TABLE2_Y_BOT   = 530.0

_MEMBER_PAT = re.compile(
    r"FOOTING|COLUMN|PEDESTAL|PLINTH|BEAM|SLAB|RETAINING|WALL|LINTEL|"
    r"OVERHEAD|TANK|STAIR|UNDER\s*GROUND",
    re.I
)


class ConcreteGradeParser:
    def __init__(self, extractor: GeneralNotesTextExtractor):
        self._ext = extractor

    def parse(self) -> Tuple[List[str], Dict[str, str], List[str]]:
        """
        Returns (all_grades_sorted, element_grade_map, warnings).
        element_grade_map: {"BEAM IN SUPERSTRUCTURE": "M30", ...}
        """
        warnings: List[str] = []
        all_items = self._ext.extract()
        found_grades: Set[str] = set()

        for item in all_items:
            for m in _CONC_PAT.finditer(item.text):
                found_grades.add(f"M{m.group(1)}")

        # Build element-grade map from TABLE 2
        element_map: Dict[str, str] = {}
        region = self._ext.items_in_region(
            1540.0, 1680.0, _TABLE2_Y_BOT, _TABLE2_Y_TOP
        )
        region.sort(key=lambda i: -i.y)

        # Group by Y row
        rows = self._group_by_y(region)
        for row in rows:
            member = ""
            grade = ""
            for item in sorted(row, key=lambda i: i.x):
                if _MEMBER_PAT.search(item.text) and not item.text.strip().isdigit():
                    member = item.text.strip().upper()
                m = _CONC_PAT.search(item.text)
                if m and _CONC_COL_X_MIN <= item.x <= _CONC_COL_X_MAX:
                    grade = f"M{m.group(1)}"
            if member and grade:
                element_map[member] = grade

        if not element_map:
            warnings.append("ConcreteGradeParser: Could not build element-grade map from TABLE 2.")

        grades_sorted = sorted(found_grades, key=lambda g: int(g[1:]))
        return grades_sorted, element_map, warnings

    def _group_by_y(self, items, tol=5.0):
        if not items:
            return []
        s = sorted(items, key=lambda i: -i.y)
        clusters = [[s[0]]]
        for item in s[1:]:
            if abs(item.y - clusters[-1][0].y) <= tol:
                clusters[-1].append(item)
            else:
                clusters.append([item])
        return clusters
