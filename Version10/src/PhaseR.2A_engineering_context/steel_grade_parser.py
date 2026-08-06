"""
Steel Grade Parser.

Extracts all steel grades from the GN DXF and identifies the primary
(dominant) steel grade for beam reinforcement from TABLE 2.
"""
from __future__ import annotations
import re
from typing import List, Optional, Set, Tuple

from .general_notes_text_extractor import GeneralNotesTextExtractor

_STEEL_PAT = re.compile(r"\bFe\s*(\d{3})\b|\bFY[-\s]?(\d{3})\b|\bHYSD\b|\bTOR\b", re.I)

# TABLE 2 x-range for steel grade column
_STEEL_COL_X_MIN = 1650.0
_STEEL_COL_X_MAX = 1680.0
_TABLE2_Y_TOP    = 725.0
_TABLE2_Y_BOTTOM = 530.0

# Key element used to identify the primary beam steel grade
_BEAM_ELEMENT_KEYWORDS = re.compile(r"BEAM IN SUPER", re.I)


class SteelGradeParser:
    def __init__(self, extractor: GeneralNotesTextExtractor):
        self._ext = extractor

    def parse(self) -> Tuple[List[str], str, List[str]]:
        """
        Returns (all_grades_sorted, primary_grade, warnings).
        Primary grade = steel grade specified for BEAM IN SUPERSTRUCTURE in TABLE 2.
        """
        all_items = self._ext.extract()
        warnings: List[str] = []
        found_grades: Set[str] = set()

        for item in all_items:
            for m in _STEEL_PAT.finditer(item.text):
                num = m.group(1) or m.group(2)
                if num:
                    found_grades.add(f"Fe{num}")

        # Determine primary grade from TABLE 2 beam row
        primary = self._primary_from_table2()
        if primary:
            found_grades.add(primary)
        else:
            warnings.append("SteelGradeParser: Could not determine primary steel grade from TABLE 2 beam row.")
            # Fall back to most common grade in dev length table headers
            primary = self._primary_from_dev_table()
            if not primary:
                primary = "Fe415"   # IS standard default
                warnings.append("SteelGradeParser: Using IS default Fe415 as primary steel grade.")

        grades_sorted = sorted(found_grades, key=lambda g: int(g[2:]))
        return grades_sorted, primary, warnings

    def _primary_from_table2(self) -> Optional[str]:
        """Read the steel grade from the BEAM IN SUPERSTRUCTURE row of TABLE 2."""
        region = self._ext.items_in_region(
            1540.0, 1680.0, _TABLE2_Y_BOTTOM, _TABLE2_Y_TOP
        )
        region.sort(key=lambda i: -i.y)

        # Find the Y of the beam row
        beam_y: Optional[float] = None
        for item in region:
            if _BEAM_ELEMENT_KEYWORDS.search(item.text):
                beam_y = item.y
                break

        if beam_y is None:
            return None

        # Find steel grade value in same Y band
        for item in region:
            if abs(item.y - beam_y) <= 5.0:
                m = _STEEL_PAT.search(item.text)
                if m:
                    num = m.group(1) or m.group(2)
                    if num:
                        return f"Fe{num}"
        return None

    def _primary_from_dev_table(self) -> Optional[str]:
        """Read the first steel grade from the dev length table header."""
        item = self._ext.find_anchor(r"LD\s+FOR\s+FY[-\s]?(\d{3})")
        if item:
            m = re.search(r"FY[-\s]?(\d{3})", item.text, re.I)
            if m:
                return f"Fe{m.group(1)}"
        return None
