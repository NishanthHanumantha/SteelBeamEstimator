"""Debug-only reinforcement sketch detection (per header occurrence, no merging)."""

from contextlib import contextmanager
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from ezdxf.document import Drawing
from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.geometry import geometry_graph as gg
from src.geometry.geometry_graph import GeometryGraphBuilder, SketchComponent

# Moderate expansion for debug (production defaults remain unchanged).
DEBUG_SEED_BBOX_DISTANCE_MM = 4000.0
DEBUG_MAX_LABEL_DISTANCE_MM = 4000.0
DEBUG_MAX_SEED_X_OFFSET_MM = 2000.0
DEBUG_Y_BELOW_HEADER_MM = 12000.0
DEBUG_Y_ABOVE_HEADER_MM = 2000.0
RECOVERY_SEED_BBOX_DISTANCE_MM = 8000.0
RECOVERY_MAX_LABEL_DISTANCE_MM = 8000.0
RECOVERY_MAX_SEED_X_OFFSET_MM = 3500.0


@dataclass(frozen=True)
class HeaderOccurrence:
    beam_mark: str
    x: float
    y: float
    handle: str


@contextmanager
def _recovery_geometry_search():
    saved = (
        gg.SEED_BBOX_DISTANCE_MM,
        gg.MAX_LABEL_DISTANCE_MM,
        gg.MAX_SEED_X_OFFSET_MM,
    )
    gg.SEED_BBOX_DISTANCE_MM = RECOVERY_SEED_BBOX_DISTANCE_MM
    gg.MAX_LABEL_DISTANCE_MM = RECOVERY_MAX_LABEL_DISTANCE_MM
    gg.MAX_SEED_X_OFFSET_MM = RECOVERY_MAX_SEED_X_OFFSET_MM
    try:
        yield
    finally:
        gg.SEED_BBOX_DISTANCE_MM = saved[0]
        gg.MAX_LABEL_DISTANCE_MM = saved[1]
        gg.MAX_SEED_X_OFFSET_MM = saved[2]


@contextmanager
def _debug_geometry_search():
    saved = (
        gg.SEED_BBOX_DISTANCE_MM,
        gg.MAX_LABEL_DISTANCE_MM,
        gg.MAX_SEED_X_OFFSET_MM,
    )
    gg.SEED_BBOX_DISTANCE_MM = DEBUG_SEED_BBOX_DISTANCE_MM
    gg.MAX_LABEL_DISTANCE_MM = DEBUG_MAX_LABEL_DISTANCE_MM
    gg.MAX_SEED_X_OFFSET_MM = DEBUG_MAX_SEED_X_OFFSET_MM
    try:
        yield
    finally:
        gg.SEED_BBOX_DISTANCE_MM = saved[0]
        gg.MAX_LABEL_DISTANCE_MM = saved[1]
        gg.MAX_SEED_X_OFFSET_MM = saved[2]


def _bbox_key(bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    return tuple(round(value, 0) for value in bbox)


def _bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _bbox_intersects_cell(
    bbox: Tuple[float, float, float, float],
    cell: dict[str, float],
) -> bool:
    xmin, ymin, xmax, ymax = bbox
    return not (
        xmax < cell["xmin"]
        or xmin > cell["xmax"]
        or ymax < cell["ymin"]
        or ymin > cell["ymax"]
    )


def _expanded_column(
    header: HeaderOccurrence,
    cell: dict[str, float],
) -> dict[str, float]:
    """Expand ownership cell for sketch search (debug only — sections sit below headers)."""
    x_pad = DEBUG_MAX_SEED_X_OFFSET_MM
    return {
        "xmin": min(cell["xmin"], header.x - x_pad),
        "xmax": max(cell["xmax"], header.x + x_pad),
        "ymin": min(cell["ymin"], header.y - DEBUG_Y_ABOVE_HEADER_MM),
        "ymax": max(cell["ymax"], header.y + DEBUG_Y_BELOW_HEADER_MM),
    }


def _sketch_near_header(
    sketch: SketchComponent,
    header: HeaderOccurrence,
    cell: dict[str, float] | None,
) -> bool:
    center_x, center_y = _bbox_center(sketch.bbox)
    if abs(center_x - header.x) <= DEBUG_MAX_SEED_X_OFFSET_MM:
        distance = math.hypot(center_x - header.x, center_y - header.y)
        if distance <= DEBUG_MAX_LABEL_DISTANCE_MM:
            return True
    if cell is not None:
        return _bbox_intersects_cell(
            sketch.bbox, _expanded_column(header, cell)
        )
    return False


class BeamSketchDebugDetector:
    """Detect independent reinforcement sketches per beam header occurrence."""

    def __init__(self) -> None:
        self._builder = GeometryGraphBuilder()

    def detect(
        self,
        doc: Drawing,
        headers: List[HeaderOccurrence],
        cell_lookup: Dict[str, dict[str, float]] | None = None,
    ) -> List[dict[str, Any]]:
        cell_lookup = cell_lookup or {}

        with _debug_geometry_search():
            records: List[dict[str, Any]] = []
            counters: Dict[str, int] = {}
            seen_per_mark: Dict[str, Set[Tuple[float, float, float, float]]] = {}

            for header in sorted(
                headers,
                key=lambda item: (-item.y, item.x, beam_mark_sort_key(item.beam_mark)),
            ):
                cell = cell_lookup.get(header.beam_mark)
                sketches = self._sketches_for_header(doc, header, cell)
                mark = header.beam_mark
                seen_per_mark.setdefault(mark, set())

                for sketch in sketches:
                    if not _sketch_near_header(sketch, header, cell):
                        continue

                    key = _bbox_key(sketch.bbox)
                    if key in seen_per_mark[mark]:
                        continue
                    seen_per_mark[mark].add(key)

                    counters[mark] = counters.get(mark, 0) + 1
                    sketch_id = f"{mark}_S{counters[mark]}"
                    records.append(
                        self._to_record(sketch_id, mark, header, sketch)
                    )

            for mark, cell in cell_lookup.items():
                if any(record["beam_mark"] == mark for record in records):
                    continue
                mark_headers = [h for h in headers if h.beam_mark == mark]
                if not mark_headers:
                    continue
                existing_keys = {
                    _bbox_key(
                        (
                            record["bbox"]["xmin"],
                            record["bbox"]["ymin"],
                            record["bbox"]["xmax"],
                            record["bbox"]["ymax"],
                        )
                    )
                    for record in records
                    if record["beam_mark"] == mark
                }
                recovered = self._recover_sketches_for_mark(
                    doc,
                    mark_headers,
                    cell,
                    set(existing_keys),
                )
                for sketch, source_header in recovered:
                    key = _bbox_key(sketch.bbox)
                    if key in existing_keys:
                        continue
                    existing_keys.add(key)
                    counters[mark] = counters.get(mark, 0) + 1
                    sketch_id = f"{mark}_S{counters[mark]}"
                    records.append(
                        self._to_record(sketch_id, mark, source_header, sketch)
                    )

            records.sort(
                key=lambda item: (
                    beam_mark_sort_key(item["beam_mark"]),
                    item["sketch_id"],
                )
            )
            logger.info(
                "Detected {} reinforcement sketch(s) across {} beam mark(s)",
                len(records),
                len(counters),
            )
            return records

    def _header_for_mark(
        self, headers: List[HeaderOccurrence], mark: str
    ) -> HeaderOccurrence | None:
        matches = [header for header in headers if header.beam_mark == mark]
        if not matches:
            return None
        return min(matches, key=lambda item: (item.x, item.y))

    def _sketches_for_header(
        self,
        doc: Drawing,
        header: HeaderOccurrence,
        cell: dict[str, float] | None,
    ) -> List[SketchComponent]:
        search_cell = _expanded_column(header, cell) if cell else None
        sketches = self._builder.build_sketches(doc, header.x, header.y)
        if not sketches:
            merged = self._builder.build_merged_sketch(doc, header.x, header.y)
            if merged:
                sketches = [merged]

        if sketches:
            return sketches

        if search_cell:
            return self._sketches_in_cell(doc, header, search_cell)
        return []

    def _sketches_in_cell(
        self,
        doc: Drawing,
        header: HeaderOccurrence,
        cell: dict[str, float],
    ) -> List[SketchComponent]:
        xmin = float(cell["xmin"])
        ymin = float(cell["ymin"])
        xmax = float(cell["xmax"])
        ymax = float(cell["ymax"])

        _, polyline_bboxes = self._builder._extract_segments(doc)
        if not polyline_bboxes:
            return []

        sketches: List[SketchComponent] = []
        seen: Set[Tuple[float, float, float, float]] = set()

        for poly in polyline_bboxes:
            px_min, py_min, px_max, py_max = poly[0], poly[1], poly[2], poly[3]
            center_x = (px_min + px_max) / 2.0
            center_y = (py_min + py_max) / 2.0
            if not (xmin <= center_x <= xmax and ymin <= center_y <= ymax):
                continue

            found = self._builder.build_sketches(doc, center_x, center_y)
            if not found:
                merged = self._builder.build_merged_sketch(doc, center_x, center_y)
                found = [merged] if merged else []

            for sketch in found:
                if not _bbox_intersects_cell(sketch.bbox, cell):
                    continue
                key = _bbox_key(sketch.bbox)
                if key in seen:
                    continue
                seen.add(key)
                sketches.append(sketch)

        if sketches:
            logger.debug(
                "Cell fallback for {} found {} sketch(es)",
                header.beam_mark,
                len(sketches),
            )
        return sketches

    def _recover_sketches_for_mark(
        self,
        doc: Drawing,
        mark_headers: List[HeaderOccurrence],
        cell: dict[str, float],
        seen: Set[Tuple[float, float, float, float]],
    ) -> List[Tuple[SketchComponent, HeaderOccurrence]]:
        """Last-resort recovery for beam marks with no sketches (debug only)."""
        recovered: List[Tuple[SketchComponent, HeaderOccurrence]] = []

        with _recovery_geometry_search():
            for occurrence in mark_headers:
                column = _expanded_column(occurrence, cell)
                sketches = self._sketches_in_cell(doc, occurrence, column)
                for sketch in sketches:
                    key = _bbox_key(sketch.bbox)
                    if key in seen:
                        continue
                    seen.add(key)
                    recovered.append((sketch, occurrence))

                if not sketches:
                    loose = self._builder.build_sketches(
                        doc, occurrence.x, occurrence.y
                    )
                    if not loose:
                        merged = self._builder.build_merged_sketch(
                            doc, occurrence.x, occurrence.y
                        )
                        loose = [merged] if merged else []
                    for sketch in loose:
                        center_x, center_y = _bbox_center(sketch.bbox)
                        if abs(center_x - occurrence.x) > RECOVERY_MAX_SEED_X_OFFSET_MM:
                            continue
                        key = _bbox_key(sketch.bbox)
                        if key in seen:
                            continue
                        seen.add(key)
                        recovered.append((sketch, occurrence))

        if recovered:
            logger.debug(
                "Recovered {} sketch(es) for {}",
                len(recovered),
                mark_headers[0].beam_mark,
            )
        return recovered

    def _to_record(
        self,
        sketch_id: str,
        beam_mark: str,
        header: HeaderOccurrence,
        sketch: SketchComponent,
    ) -> dict[str, Any]:
        xmin, ymin, xmax, ymax = sketch.bbox
        width = xmax - xmin
        height = ymax - ymin
        return {
            "beam_mark": beam_mark,
            "sketch_id": sketch_id,
            "header_x": round(header.x, 3),
            "header_y": round(header.y, 3),
            "bbox": {
                "xmin": round(xmin, 3),
                "ymin": round(ymin, 3),
                "xmax": round(xmax, 3),
                "ymax": round(ymax, 3),
            },
            "width": round(width, 3),
            "height": round(height, 3),
            "area": round(width * height, 3),
        }
