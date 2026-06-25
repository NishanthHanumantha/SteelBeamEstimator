"""Export beam sketch debug JSON, DXF, and validation."""

import json
from pathlib import Path
from typing import Any, List, TypedDict

import ezdxf
from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.grid.beam_sketch_debug_detector import BeamSketchDebugDetector, HeaderOccurrence
from src.parser.dxf_reader import DxfReader
from src.parser.entity_extractor import EntityExtractor
from src.extractor.reinforcement_detail_extractor import ReinforcementDetailExtractor

DEBUG_LAYER = "DEBUG_SKETCHES"
HEADER_MARKER_RADIUS_MM = 250.0
TEXT_HEIGHT_MM = 600.0
MARK_TEXT_OFFSET_MM = 900.0


class BeamSketchDebugValidation(TypedDict):
    total_beams: int
    total_sketches: int
    beams_with_multiple_sketches: List[str]
    beams_without_sketches: List[str]
    status: str


class BeamSketchDebugExporter:
    """Build sketch debug artifacts from reinforcement DXF."""

    def __init__(self) -> None:
        self._detector = BeamSketchDebugDetector()

    def export_all(
        self,
        dxf_path: Path,
        output_dir: Path,
        cells_path: Path | None = None,
    ) -> dict[str, Any]:
        reader = DxfReader(dxf_path)
        doc = reader.read()
        modelspace = reader.get_modelspace(doc)
        if modelspace is None:
            raise ValueError("No modelspace in DXF")

        entities = EntityExtractor().extract(modelspace)
        raw_headers = ReinforcementDetailExtractor()._find_headers(entities, None)
        headers = [
            HeaderOccurrence(
                beam_mark=str(item["beam_mark"]),
                x=float(item["x"]),
                y=float(item["y"]),
                handle=str(item.get("handle", "")),
            )
            for item in raw_headers
        ]

        cell_lookup = self._load_cell_lookup(cells_path)
        sketches = self._detector.detect(doc, headers, cell_lookup)

        expected_marks = sorted(
            {header.beam_mark for header in headers},
            key=beam_mark_sort_key,
        )
        validation = self._build_validation(sketches, expected_marks)

        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(output_dir / "beam_sketches_debug.json", sketches)
        self._write_json(
            output_dir / "beam_sketches_debug_validation.json", validation
        )
        self._export_dxf(sketches, output_dir / "beam_sketches_debug.dxf")

        return {
            "sketches": sketches,
            "validation": validation,
        }

    def _load_cell_lookup(self, cells_path: Path | None) -> dict[str, dict[str, float]]:
        if cells_path is None or not cells_path.exists():
            return {}

        with cells_path.open(encoding="utf-8") as handle:
            cells = json.load(handle)

        lookup: dict[str, dict[str, float]] = {}
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            mark = str(cell.get("beam_mark", ""))
            if not mark:
                continue
            lookup[mark] = {
                "xmin": float(cell["xmin"]),
                "ymin": float(cell["ymin"]),
                "xmax": float(cell["xmax"]),
                "ymax": float(cell["ymax"]),
            }
        return lookup

    def _build_validation(
        self,
        sketches: List[dict[str, Any]],
        expected_marks: List[str],
    ) -> BeamSketchDebugValidation:
        per_mark: dict[str, int] = {}
        for sketch in sketches:
            mark = sketch["beam_mark"]
            per_mark[mark] = per_mark.get(mark, 0) + 1

        beams_with_multiple = sorted(
            [mark for mark, count in per_mark.items() if count > 1],
            key=beam_mark_sort_key,
        )
        beams_without = sorted(
            [mark for mark in expected_marks if per_mark.get(mark, 0) == 0],
            key=beam_mark_sort_key,
        )

        status = "PASS" if not beams_without else "FAIL"

        return BeamSketchDebugValidation(
            total_beams=len(expected_marks),
            total_sketches=len(sketches),
            beams_with_multiple_sketches=beams_with_multiple,
            beams_without_sketches=beams_without,
            status=status,
        )

    def _export_dxf(self, sketches: List[dict[str, Any]], output_path: Path) -> None:
        doc = ezdxf.new("R2010")
        if DEBUG_LAYER not in doc.layers:
            doc.layers.add(DEBUG_LAYER)

        msp = doc.modelspace()

        for sketch in sketches:
            bbox = sketch["bbox"]
            xmin = float(bbox["xmin"])
            ymin = float(bbox["ymin"])
            xmax = float(bbox["xmax"])
            ymax = float(bbox["ymax"])
            header_x = float(sketch["header_x"])
            header_y = float(sketch["header_y"])
            center_x = (xmin + xmax) / 2.0
            center_y = (ymin + ymax) / 2.0
            sketch_id = sketch["sketch_id"]
            beam_mark = sketch["beam_mark"]

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
                sketch_id,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM,
                    "insert": (center_x, center_y),
                },
            )
            msp.add_text(
                beam_mark,
                dxfattribs={
                    "layer": DEBUG_LAYER,
                    "height": TEXT_HEIGHT_MM * 0.75,
                    "insert": (center_x, center_y - MARK_TEXT_OFFSET_MM),
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
        logger.info("Wrote {}", output_path.resolve())

    def _write_json(self, path: Path, data: object) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        logger.info("Wrote {}", path.resolve())
