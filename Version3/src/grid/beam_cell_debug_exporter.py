"""Debug exports for beam ownership cells (visual validation, no logic changes)."""

import json
from pathlib import Path
from typing import Any, List, TypedDict

import ezdxf
from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.grid.beam_cell_builder import BeamCell
from src.grid.beam_cell_validator import BeamCellValidator

DEBUG_LAYER = "DEBUG_BEAM_CELLS"
HEADER_MARKER_RADIUS_MM = 250.0
TEXT_HEIGHT_MM = 600.0
ROW_TEXT_OFFSET_MM = 900.0


class CellBbox(TypedDict):
    xmin: float
    ymin: float
    xmax: float
    ymax: float


class SourceHeader(TypedDict):
    beam_mark: str
    x: float
    y: float


class BeamCellDebugRecord(TypedDict):
    beam_mark: str
    row_id: int
    header_x: float
    header_y: float
    cell_bbox: CellBbox
    cell_width: float
    cell_height: float
    source_header: SourceHeader


class RowSummary(TypedDict):
    row_id: int
    beams: List[str]


class BeamCellDebugSummary(TypedDict):
    total_cells: int
    rows: List[RowSummary]


class BeamCellDebugValidation(TypedDict):
    total_cells: int
    cells_with_invalid_bbox: List[str]
    overlapping_cells: List[str]
    orphan_headers: List[str]
    status: str


class BeamCellDebugExporter:
    """Build JSON/DXF debug artifacts from existing beam_cells.json."""

    def load_cells(self, path: Path) -> List[BeamCell]:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError(f"Expected list in {path}")
        return data

    def build_debug_records(self, cells: List[BeamCell]) -> List[BeamCellDebugRecord]:
        records: List[BeamCellDebugRecord] = []
        for cell in cells:
            xmin = float(cell["xmin"])
            ymin = float(cell["ymin"])
            xmax = float(cell["xmax"])
            ymax = float(cell["ymax"])
            header_x = float(cell["header_x"])
            header_y = float(cell["header_y"])

            records.append(
                BeamCellDebugRecord(
                    beam_mark=cell["beam_mark"],
                    row_id=int(cell["row_id"]),
                    header_x=round(header_x, 3),
                    header_y=round(header_y, 3),
                    cell_bbox=CellBbox(
                        xmin=round(xmin, 3),
                        ymin=round(ymin, 3),
                        xmax=round(xmax, 3),
                        ymax=round(ymax, 3),
                    ),
                    cell_width=round(xmax - xmin, 3),
                    cell_height=round(ymax - ymin, 3),
                    source_header=SourceHeader(
                        beam_mark=cell["beam_mark"],
                        x=round(header_x, 3),
                        y=round(header_y, 3),
                    ),
                )
            )

        records.sort(
            key=lambda item: (item["row_id"], beam_mark_sort_key(item["beam_mark"]))
        )
        return records

    def build_summary(self, cells: List[BeamCell]) -> BeamCellDebugSummary:
        by_row: dict[int, List[str]] = {}
        for cell in cells:
            by_row.setdefault(int(cell["row_id"]), []).append(cell["beam_mark"])

        rows: List[RowSummary] = []
        for row_id in sorted(by_row):
            beams = sorted(by_row[row_id], key=beam_mark_sort_key)
            rows.append(RowSummary(row_id=row_id, beams=beams))

        return BeamCellDebugSummary(total_cells=len(cells), rows=rows)

    def build_validation(
        self,
        cells: List[BeamCell],
        header_marks: List[str] | None = None,
    ) -> BeamCellDebugValidation:
        invalid_bbox = self._find_invalid_bboxes(cells)
        overlapping = BeamCellValidator()._find_overlaps(cells)

        cell_marks = {cell["beam_mark"] for cell in cells}
        orphan_headers: List[str] = []
        if header_marks is not None:
            orphan_headers = sorted(
                [mark for mark in header_marks if mark not in cell_marks],
                key=beam_mark_sort_key,
            )

        for cell in cells:
            if not self._header_inside_cell(cell):
                mark = cell["beam_mark"]
                if mark not in orphan_headers:
                    orphan_headers.append(mark)
            orphan_headers.sort(key=beam_mark_sort_key)

        status = (
            "PASS"
            if not invalid_bbox and not overlapping and not orphan_headers
            else "FAIL"
        )

        return BeamCellDebugValidation(
            total_cells=len(cells),
            cells_with_invalid_bbox=invalid_bbox,
            overlapping_cells=overlapping,
            orphan_headers=orphan_headers,
            status=status,
        )

    def export_dxf(self, cells: List[BeamCell], output_path: Path) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)

        msp = doc.modelspace()

        for cell in cells:
            xmin = float(cell["xmin"])
            ymin = float(cell["ymin"])
            xmax = float(cell["xmax"])
            ymax = float(cell["ymax"])
            header_x = float(cell["header_x"])
            header_y = float(cell["header_y"])
            center_x = (xmin + xmax) / 2.0
            center_y = (ymin + ymax) / 2.0
            mark = cell["beam_mark"]
            row_id = int(cell["row_id"])

            corners = [
                (xmin, ymin),
                (xmax, ymin),
                (xmax, ymax),
                (xmin, ymax),
                (xmin, ymin),
            ]
            msp.add_lwpolyline(
                corners,
                dxfattribs={"layer": DEBUG_LAYER},
                close=True,
            )

            msp.add_text(
                mark,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (center_x, center_y),
                },
            )
            msp.add_text(
                f"Row{row_id}",
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM * 0.75,
                    "insert": (center_x, center_y - ROW_TEXT_OFFSET_MM),
                },
            )

            msp.add_circle(
                (header_x, header_y),
                HEADER_MARKER_RADIUS_MM,
                dxfattribs={"layer": DEBUG_LAYER},
            )
            msp.add_line(
                (header_x, header_y),
                (center_x, center_y),
                dxfattribs={"layer": DEBUG_LAYER},
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(output_path)
        logger.info("Wrote DXF debug overlay to {}", output_path.resolve())

    def export_all(
        self,
        cells_path: Path,
        output_dir: Path,
        headers_path: Path | None = None,
    ) -> dict[str, Any]:
        cells = self.load_cells(cells_path)
        debug_records = self.build_debug_records(cells)
        summary = self.build_summary(cells)

        header_marks: List[str] | None = None
        if headers_path is not None and headers_path.exists():
            with headers_path.open(encoding="utf-8") as handle:
                headers_data = json.load(handle)
            if isinstance(headers_data, list):
                header_marks = [
                    item["beam_mark"]
                    for item in headers_data
                    if isinstance(item, dict) and "beam_mark" in item
                ]

        validation = self.build_validation(cells, header_marks)

        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(output_dir / "beam_cells_debug.json", debug_records)
        self._write_json(output_dir / "beam_cells_debug_summary.json", summary)
        self._write_json(
            output_dir / "beam_cells_debug_validation.json", validation
        )
        self.export_dxf(cells, output_dir / "beam_cells_debug.dxf")

        return {
            "total_cells": len(cells),
            "summary": summary,
            "validation": validation,
        }

    def _write_json(self, path: Path, data: object) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        logger.info("Wrote {}", path.resolve())

    def _find_invalid_bboxes(self, cells: List[BeamCell]) -> List[str]:
        invalid: List[str] = []
        for cell in cells:
            width = float(cell["xmax"]) - float(cell["xmin"])
            height = float(cell["ymax"]) - float(cell["ymin"])
            if width <= 0.0 or height <= 0.0:
                invalid.append(cell["beam_mark"])
        return sorted(invalid, key=beam_mark_sort_key)

    def _header_inside_cell(self, cell: BeamCell) -> bool:
        hx = float(cell["header_x"])
        hy = float(cell["header_y"])
        xmin = float(cell["xmin"])
        xmax = float(cell["xmax"])
        ymin = float(cell["ymin"])
        ymax = float(cell["ymax"])
        return xmin <= hx <= xmax and ymin <= hy <= ymax
