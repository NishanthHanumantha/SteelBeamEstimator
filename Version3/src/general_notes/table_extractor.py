"""Spatial table extraction from General Notes text annotations."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.general_notes.general_notes_parser import TextAnnotation
from src.general_notes.normalizers import (
    normalize_concrete_grade,
    normalize_diameter_mm,
    normalize_steel_grade,
)

_LD_ANCHOR_RE = re.compile(
    r"(?:LD\s+FOR\s+)?(?:FY[-\s]*|Fe\s*)(\d{3})\s*D?",
    re.IGNORECASE,
)
_CONCRETE_HEADER_RE = re.compile(r"M\s*(\d{2,3})\s*GRADE", re.IGNORECASE)
_SERIAL_RE = re.compile(r"^(\d+)\.?$")
_LDC_VALUE_RE = re.compile(r"^\d{2,4}$")


@dataclass
class GridTable:
    name: str
    anchor_text: str
    row_labels: List[str]
    column_labels: List[str]
    values: List[List[Optional[int]]]
    row_positions: List[float] = field(default_factory=list)
    column_positions: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverRow:
    serial: Optional[int]
    member_type: str
    cover_mm: int
    y_position: float
    notes: Optional[str] = None


def cluster_positions(values: List[float], tolerance: float) -> List[float]:
    if not values:
        return []
    sorted_vals = sorted(values)
    clusters: List[List[float]] = [[sorted_vals[0]]]
    for value in sorted_vals[1:]:
        if value - clusters[-1][-1] <= tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return [sum(cluster) / len(cluster) for cluster in clusters]


def nearest_cluster(value: float, clusters: List[float], tolerance: float) -> Optional[int]:
    best_index: Optional[int] = None
    best_distance = tolerance
    for index, center in enumerate(clusters):
        distance = abs(value - center)
        if distance <= best_distance:
            best_distance = distance
            best_index = index
    return best_index


class TableExtractor:
    """Extract engineering lookup tables from positioned DXF text."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._row_tol = float(config.get("row_cluster_tolerance", 3.5))
        self._col_tol = float(config.get("column_cluster_tolerance", 12.0))

    def extract_development_length_tables(
        self, texts: List[TextAnnotation]
    ) -> Dict[str, Dict[str, Dict[int, int]]]:
        anchors = self._find_ld_anchors(texts)
        tables: Dict[str, Dict[str, Dict[int, int]]] = {}
        for anchor in anchors:
            grid = self._extract_ld_grid(texts, anchor)
            if grid is None:
                continue
            steel = grid.metadata.get("steel_grade", "UNKNOWN")
            tables[steel] = self._grid_to_ld_lookup(grid)
            designation = grid.metadata.get("steel_designation")
            if designation and designation != steel and designation not in tables:
                tables[designation] = tables[steel]
        return tables

    def extract_development_length_grid_tables(
        self, texts: List[TextAnnotation]
    ) -> List[GridTable]:
        grids: List[GridTable] = []
        for anchor in self._find_ld_anchors(texts):
            grid = self._extract_ld_grid(texts, anchor)
            if grid:
                grids.append(grid)
        return grids

    def extract_cover_table(self, texts: List[TextAnnotation]) -> List[CoverRow]:
        y_min = float(self._config.get("cover_table_y_min", 500.0))
        y_max = float(self._config.get("cover_table_y_max", 720.0))
        x_min = float(self._config.get("cover_table_x_min", 1540.0))

        region = [
            t
            for t in texts
            if t.x >= x_min and y_min <= t.y <= y_max
        ]
        serials: Dict[float, int] = {}
        members: Dict[float, str] = {}
        covers: Dict[float, int] = {}

        for ann in region:
            text = ann.text.strip()
            if _SERIAL_RE.match(text) and ann.x < 1552:
                serial_match = _SERIAL_RE.match(text)
                if serial_match:
                    serials[ann.y] = int(serial_match.group(1))
            elif ann.x > 1605 and _LDC_VALUE_RE.match(text):
                covers[ann.y] = int(text)
            elif 1552 <= ann.x <= 1600 and len(text) > 3 and not _LDC_VALUE_RE.match(text):
                if "MEMBER" not in text.upper() and "CLEAR" not in text.upper():
                    members[ann.y] = text

        rows: List[CoverRow] = []
        for y, member in sorted(members.items(), key=lambda item: -item[0]):
            cover_y = self._nearest_y(y, list(covers.keys()), self._row_tol)
            if cover_y is None:
                continue
            cover_mm = covers[cover_y]
            serial_y = self._nearest_y(y, list(serials.keys()), self._row_tol)
            serial = serials.get(serial_y) if serial_y is not None else None
            rows.append(
                CoverRow(
                    serial=serial,
                    member_type=member.strip(),
                    cover_mm=cover_mm,
                    y_position=y,
                )
            )
        return rows

    def _find_ld_anchors(self, texts: List[TextAnnotation]) -> List[TextAnnotation]:
        anchors: List[TextAnnotation] = []
        y_min = float(self._config.get("ld_table_y_min", 775.0))
        x_min = float(self._config.get("ld_table_x_min", 1540.0))
        for ann in texts:
            if ann.y < y_min or ann.x < x_min:
                continue
            if _LD_ANCHOR_RE.search(ann.text):
                anchors.append(ann)
        anchors.sort(key=lambda item: item.y, reverse=True)
        return anchors

    def _extract_ld_grid(
        self, texts: List[TextAnnotation], anchor: TextAnnotation
    ) -> Optional[GridTable]:
        match = _LD_ANCHOR_RE.search(anchor.text)
        if not match:
            return None
        numeric = match.group(1)
        raw = anchor.text.upper()
        suffix = "D" if re.search(rf"{numeric}\s*D", raw) else ""
        steel_grade = f"Fe{numeric}{suffix}"
        # LD grid headers use base grade without D suffix for table key consistency
        table_key = f"Fe{numeric}"
        y_bottom = anchor.y - 60.0
        y_top = anchor.y + 8.0
        x_left = float(self._config.get("ld_table_x_min", 1540.0)) - 10.0
        x_right = anchor.x + 120.0

        region = [
            t
            for t in texts
            if x_left <= t.x <= x_right and y_bottom <= t.y <= y_top
        ]

        column_headers: Dict[float, str] = {}
        for ann in region:
            header_match = _CONCRETE_HEADER_RE.search(ann.text)
            if header_match:
                column_headers[ann.x] = f"M{header_match.group(1)}"

        if not column_headers:
            for ann in region:
                grade = normalize_concrete_grade(ann.text)
                if grade and "GRADE" in ann.text.upper():
                    column_headers[ann.x] = grade["grade"]

        col_positions = cluster_positions(list(column_headers.keys()), self._col_tol)
        col_labels = []
        for pos in col_positions:
            nearest_x = min(column_headers.keys(), key=lambda x: abs(x - pos))
            col_labels.append(column_headers[nearest_x])

        diameter_rows: Dict[float, int] = {}
        for ann in region:
            if ann.x < 1555:
                diameter = normalize_diameter_mm(ann.text)
                if diameter:
                    diameter_rows[ann.y] = diameter

        row_positions = cluster_positions(list(diameter_rows.keys()), self._row_tol)
        row_labels = []
        for pos in row_positions:
            nearest_y = min(diameter_rows.keys(), key=lambda y: abs(y - pos))
            row_labels.append(str(diameter_rows[nearest_y]))

        values: List[List[Optional[int]]] = []
        for row_y in row_positions:
            row_values: List[Optional[int]] = []
            nearest_row_y = min(diameter_rows.keys(), key=lambda y: abs(y - row_y))
            for col_x in col_positions:
                cell = self._find_ld_cell_value(region, nearest_row_y, col_x)
                row_values.append(cell)
            values.append(row_values)

        if not row_labels or not col_labels or not any(any(row) for row in values):
            return None

        return GridTable(
            name=f"development_length_{steel_grade}",
            anchor_text=anchor.text,
            row_labels=row_labels,
            column_labels=col_labels,
            values=values,
            row_positions=row_positions,
            column_positions=col_positions,
            metadata={
                "steel_grade": table_key,
                "steel_designation": steel_grade,
                "anchor_y": anchor.y,
            },
        )

    def _find_ld_cell_value(
        self,
        region: List[TextAnnotation],
        row_y: float,
        col_x: float,
    ) -> Optional[int]:
        candidates: List[Tuple[float, str]] = []
        for ann in region:
            if not _LDC_VALUE_RE.match(ann.text.strip()):
                continue
            if abs(ann.y - row_y) <= self._row_tol and abs(ann.x - col_x) <= self._col_tol:
                candidates.append((abs(ann.y - row_y) + abs(ann.x - col_x), ann.text))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return int(candidates[0][1])

    def _grid_to_ld_lookup(self, grid: GridTable) -> Dict[str, Dict[int, int]]:
        lookup: Dict[str, Dict[int, int]] = {}
        for row_index, diameter_label in enumerate(grid.row_labels):
            diameter = int(diameter_label)
            for col_index, concrete in enumerate(grid.column_labels):
                value = grid.values[row_index][col_index]
                if value is None:
                    continue
                lookup.setdefault(concrete, {})[diameter] = value
        return lookup

    def _nearest_y(self, y: float, positions: List[float], tolerance: float) -> Optional[float]:
        best: Optional[float] = None
        best_dist = tolerance
        for pos in positions:
            dist = abs(pos - y)
            if dist <= best_dist:
                best_dist = dist
                best = pos
        return best
