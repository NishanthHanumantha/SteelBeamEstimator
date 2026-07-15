"""
Development Length Table Parser.

Parses TABLE 1 from the General Notes DXF.
The table structure (from spatial analysis):

  Header:  "LD FOR FY-415"  (and "LD FOR FY-500" below it)
  Columns: DIA.IN mm | M20 GRADE | M25 GRADE | M30 GRADE | M35 GRADE | M40 & ABOVE
  Rows:    8 | 400 | 350 | 300 | 275 | 250
           10 | 500 | 425 | 380 | 350 | 300
           12 | 565 | 485 | 455 | 400 | 355
           16 | 760 | 645 | 610 | 535 | 475
           20 | 940 | 810 | 755 | 665 | 600
           25 | 1175 | 1010 | 940 | 830 | 750
           32 | 1510 | 1290 | 1210 | 1065 | 950

All values in mm.

Strategy:
  1. Locate "LD FOR FY-NNN" anchor(s)
  2. Within X-band of table (1540–1660), group items by Y row
  3. Identify grade columns by X position of "M20 GRADE", "M25 GRADE" etc.
  4. Identify diameter column (leftmost numeric column)
  5. Match data cells to (dia, grade) by X proximity
"""
from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple

from .general_notes_text_extractor import DXFTextItem, GeneralNotesTextExtractor
from .engineering_context_model import DevelopmentLengthEntry

# X-range of the dev length table in this GN DXF (from probe analysis)
_TABLE_X_MIN = 1540.0
_TABLE_X_MAX = 1670.0

# Grade column X-centres (approx from probe — we'll detect dynamically)
_GRADE_PATTERNS = {
    "M20": re.compile(r"M20\s*(?:GRADE)?", re.I),
    "M25": re.compile(r"M25\s*(?:GRADE)?", re.I),
    "M30": re.compile(r"M30\s*(?:GRADE)?", re.I),
    "M35": re.compile(r"M35\s*(?:GRADE)?", re.I),
    "M40": re.compile(r"M40(?:\s*&?\s*ABOVE)?", re.I),
}

_STEEL_GRADE_PAT = re.compile(r"LD\s+FOR\s+FY[-\s]?(\d+)", re.I)
_DIAMETER_VALUES = {8, 10, 12, 16, 20, 25, 32, 36, 40}
_Y_CLUSTER_TOL   = 3.0   # items within ±3 DXF units considered same row


def _cluster_by_y(items: List[DXFTextItem], tol: float = _Y_CLUSTER_TOL) -> List[List[DXFTextItem]]:
    """Group items into rows by Y proximity."""
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


class DevelopmentLengthParser:
    """
    Parses the development length lookup table from the General Notes DXF.
    Returns a list of DevelopmentLengthEntry objects.
    """

    def __init__(self, extractor: GeneralNotesTextExtractor):
        self._ext = extractor

    def parse(self) -> Tuple[List[DevelopmentLengthEntry], List[str]]:
        """
        Returns (entries, warnings).
        Parses ALL steel grade tables found (Fe415, Fe500, ...).
        """
        all_items = self._ext.extract()
        table_items = self._ext.items_in_x_range(_TABLE_X_MIN, _TABLE_X_MAX, all_items)
        table_items.sort(key=lambda i: -i.y)

        # Find all table headers
        headers: List[DXFTextItem] = []
        for item in table_items:
            m = _STEEL_GRADE_PAT.search(item.text)
            if m:
                headers.append(item)

        if not headers:
            return [], ["DevelopmentLengthParser: No table headers found (LD FOR FY-NNN)"]

        entries: List[DevelopmentLengthEntry] = []
        warnings: List[str] = []

        for i, header in enumerate(headers):
            steel_grade_num = _STEEL_GRADE_PAT.search(header.text).group(1)
            steel_grade = f"Fe{steel_grade_num}"

            # Determine Y range for this table block
            y_top = header.y + 5.0
            y_bottom = headers[i + 1].y - 2.0 if i + 1 < len(headers) else (header.y - 60.0)

            block = [
                item for item in table_items
                if y_bottom <= item.y <= y_top
            ]

            parsed, w = self._parse_table_block(block, steel_grade)
            entries.extend(parsed)
            warnings.extend(w)

        if not entries:
            warnings.append("DevelopmentLengthParser: Table found but no data rows parsed.")
        return entries, warnings

    def _parse_table_block(
        self,
        block: List[DXFTextItem],
        steel_grade: str,
    ) -> Tuple[List[DevelopmentLengthEntry], List[str]]:
        warnings: List[str] = []

        # Locate grade column headers
        grade_x: Dict[str, float] = {}
        for item in block:
            for grade_name, pat in _GRADE_PATTERNS.items():
                if pat.search(item.text):
                    grade_x[grade_name] = item.x

        if not grade_x:
            return [], [f"No grade columns found for {steel_grade} table"]

        # Build column centre list sorted by X
        col_centres = sorted(grade_x.items(), key=lambda kv: kv[1])

        # Filter data rows: items that are pure integers
        data_items = [
            item for item in block
            if re.fullmatch(r"\d{2,4}", item.text.strip())
        ]

        # Cluster data items by Y row
        clusters = _cluster_by_y(data_items)

        entries: List[DevelopmentLengthEntry] = []
        for row in clusters:
            row_sorted = sorted(row, key=lambda i: i.x)
            if not row_sorted:
                continue

            # The leftmost integer is the diameter
            diameter_candidate = int(row_sorted[0].text.strip())
            if diameter_candidate not in _DIAMETER_VALUES:
                continue

            dia_mm = diameter_candidate
            remaining = row_sorted[1:]

            # Match each remaining value to nearest grade column
            for val_item in remaining:
                best_grade: Optional[str] = None
                best_dist = float("inf")
                for grade_name, cx in col_centres:
                    dist = abs(val_item.x - cx)
                    if dist < best_dist:
                        best_dist = dist
                        best_grade = grade_name

                if best_grade and best_dist < 20.0:
                    try:
                        length_mm = int(val_item.text.strip())
                        entries.append(DevelopmentLengthEntry(
                            steel_grade=steel_grade,
                            diameter_mm=dia_mm,
                            concrete_grade=best_grade,
                            length_mm=length_mm,
                            source="GN_DXF_TABLE_1",
                        ))
                    except ValueError:
                        pass

        if not entries:
            warnings.append(
                f"DevelopmentLengthParser: No data rows parsed for {steel_grade}"
            )
        return entries, warnings
