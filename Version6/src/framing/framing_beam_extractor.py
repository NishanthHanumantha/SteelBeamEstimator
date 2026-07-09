"""Phase A — extract beam marks and geometry from framing-plan DXF files."""

from pathlib import Path
from typing import Any, List, Optional, TypedDict

from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.extractor.beam_label_extractor import BEAM_LABEL_PATTERN
from src.framing.beam_geometry import (
    LineSegment,
    assign_segments_greedy,
    beam_mark_sort_key,
)
from src.parser.dxf_flattener import flatten_entities
from src.parser.dxf_reader import DxfReader
from src.utils.text_cleaner import TextCleaner

BEAM_LINE_LAYERS = frozenset({"STR-BEAM"})
MIN_BEAM_SEGMENT_MM = 500.0
MAX_LABEL_SEGMENT_DISTANCE_MM = 3000.0

_TEXT_TYPES = frozenset({"TEXT", "MTEXT", "ATTRIB"})
_LINE_TYPES = frozenset({"LINE", "LWPOLYLINE", "POLYLINE"})


class FramingBeam(TypedDict):
    beam_mark: str
    width_mm: int
    depth_mm: int
    length_mm: int
    center_x: float
    center_y: float


class FramingBeamExtractor:
    """Extract labelled beams from framing-plan DXF (including block inserts)."""

    def __init__(self, text_cleaner: Optional[TextCleaner] = None) -> None:
        self._cleaner = text_cleaner or TextCleaner()

    def extract_from_dxf(self, dxf_path: Path) -> List[FramingBeam]:
        reader = DxfReader(dxf_path)
        doc = reader.read()
        modelspace = reader.get_modelspace(doc)
        if modelspace is None:
            logger.error("No modelspace in {}", dxf_path)
            return []

        flat = flatten_entities(modelspace)
        labels = self._extract_labels(flat)
        segments = self._extract_beam_segments(flat)
        logger.info(
            "Framing plan: {} label(s), {} beam segment(s)",
            len(labels),
            len(segments),
        )

        label_positions = [(item["beam_mark"], item["x"], item["y"]) for item in labels]
        assignments = assign_segments_greedy(
            label_positions,
            segments,
            MAX_LABEL_SEGMENT_DISTANCE_MM,
        )

        beams: List[FramingBeam] = []
        for label in labels:
            mark = label["beam_mark"]
            segment = assignments.get(mark)
            if segment is None:
                beams.append(
                    FramingBeam(
                        beam_mark=mark,
                        width_mm=label["width_mm"],
                        depth_mm=label["depth_mm"],
                        length_mm=0,
                        center_x=round(label["x"], 3),
                        center_y=round(label["y"], 3),
                    )
                )
                logger.warning(
                    "No beam segment matched for {} at ({}, {})",
                    mark,
                    label["x"],
                    label["y"],
                )
                continue

            beams.append(
                FramingBeam(
                    beam_mark=mark,
                    width_mm=label["width_mm"],
                    depth_mm=label["depth_mm"],
                    length_mm=int(round(segment.length_mm)),
                    center_x=round(segment.center_x, 3),
                    center_y=round(segment.center_y, 3),
                )
            )

        beams.sort(key=lambda beam: beam_mark_sort_key(beam["beam_mark"]))
        return beams

    def extract_from_directory(self, framing_dir: Path) -> List[FramingBeam]:
        dxf_files = sorted(framing_dir.glob("*.dxf"))
        if not dxf_files:
            logger.warning("No DXF files in {}", framing_dir)
            return []

        all_beams: List[FramingBeam] = []
        for dxf_path in dxf_files:
            logger.info("Extracting framing beams from {}", dxf_path.name)
            all_beams.extend(self.extract_from_dxf(dxf_path))

        return self._dedupe_by_mark(all_beams)

    def _dedupe_by_mark(self, beams: List[FramingBeam]) -> List[FramingBeam]:
        by_mark: dict[str, FramingBeam] = {}
        for beam in beams:
            mark = beam["beam_mark"]
            if mark not in by_mark:
                by_mark[mark] = beam
                continue
            existing = by_mark[mark]
            if existing["length_mm"] == 0 and beam["length_mm"] > 0:
                by_mark[mark] = beam
        return sorted(by_mark.values(), key=lambda b: beam_mark_sort_key(b["beam_mark"]))

    def _extract_labels(self, entities: List[DXFGraphic]) -> List[dict[str, Any]]:
        labels: List[dict[str, Any]] = []
        seen_marks: set[str] = set()

        for entity in entities:
            if entity.dxftype() not in _TEXT_TYPES:
                continue

            text = self._entity_text(entity).strip()
            match = BEAM_LABEL_PATTERN.match(text)
            if not match:
                continue

            mark = match.group(1).upper()
            if mark in seen_marks:
                continue
            seen_marks.add(mark)

            insert = entity.dxf.insert
            labels.append(
                {
                    "beam_mark": mark,
                    "width_mm": int(match.group(2)),
                    "depth_mm": int(match.group(3)),
                    "x": float(insert.x),
                    "y": float(insert.y),
                }
            )

        return labels

    def _extract_beam_segments(self, entities: List[DXFGraphic]) -> List[LineSegment]:
        segments: List[LineSegment] = []

        for entity in entities:
            entity_type = entity.dxftype()
            layer = str(entity.dxf.layer)

            if entity_type == "LINE" and layer in BEAM_LINE_LAYERS:
                start = entity.dxf.start
                end = entity.dxf.end
                segment = LineSegment(
                    x1=float(start.x),
                    y1=float(start.y),
                    x2=float(end.x),
                    y2=float(end.y),
                    layer=layer,
                    handle=str(entity.dxf.handle),
                )
                if segment.length_mm >= MIN_BEAM_SEGMENT_MM:
                    segments.append(segment)

            elif entity_type in ("LWPOLYLINE", "POLYLINE") and layer in BEAM_LINE_LAYERS:
                segments.extend(self._polyline_segments(entity, layer))

        return segments

    def _polyline_segments(
        self, entity: DXFGraphic, layer: str
    ) -> List[LineSegment]:
        segments: List[LineSegment] = []
        if entity.dxftype() == "LWPOLYLINE":
            points = [(float(x), float(y)) for x, y in entity.get_points(format="xy")]
        else:
            points = [
                (float(v.dxf.location.x), float(v.dxf.location.y))
                for v in entity.vertices
            ]

        handle = str(entity.dxf.handle)
        for index in range(len(points) - 1):
            x1, y1 = points[index]
            x2, y2 = points[index + 1]
            segment = LineSegment(
                x1=x1, y1=y1, x2=x2, y2=y2, layer=layer, handle=handle
            )
            if segment.length_mm >= MIN_BEAM_SEGMENT_MM:
                segments.append(segment)
        return segments

    def _entity_text(self, entity: DXFGraphic) -> str:
        entity_type = entity.dxftype()
        if entity_type == "MTEXT":
            return self._cleaner.clean(str(entity.text))
        return self._cleaner.clean(str(entity.dxf.text))
