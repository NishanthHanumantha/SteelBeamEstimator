"""Phase D.3.3 — match annotations to sketches within a detail region."""

import math
from typing import Any, Dict, List, Optional, Tuple

from src.utils.bbox_utils import (
    bbox_centroid,
    distance_point_to_bbox,
    expand_bbox,
    point_in_bbox,
)

from src.ownership.ownership_types import SKETCH_MARGIN_MM, CELL_MARGIN_MM


class AnnotationSketchMatcher:
    """Score sketches inside a detail region for annotation ownership."""

    def __init__(
        self,
        cell_by_mark: Dict[str, dict[str, Any]],
    ) -> None:
        self._cell_by_mark = cell_by_mark

    def best_sketch(
        self,
        region: dict[str, Any],
        eval_x: float,
        eval_y: float,
        insert_x: float,
        insert_y: float,
        has_leader: bool,
    ) -> Tuple[Optional[dict[str, Any]], float, float]:
        sketches = region.get("member_sketches", [])
        if not sketches:
            return None, 0.0, 0.0

        best: Optional[dict[str, Any]] = None
        best_sketch_score = 0.0
        best_geom_score = 0.0

        for sketch in sketches:
            bbox = sketch["bbox"]
            expanded = expand_bbox(bbox, SKETCH_MARGIN_MM)
            sketch_score = self._sketch_overlap_score(
                bbox, expanded, eval_x, eval_y, insert_x, insert_y, has_leader
            )
            geom_score = self._geometry_score(
                sketch, eval_x, eval_y, has_leader
            )
            combined = sketch_score + geom_score
            if combined > best_sketch_score + best_geom_score:
                best = sketch
                best_sketch_score = sketch_score
                best_geom_score = geom_score

        return best, best_sketch_score, best_geom_score

    def distance_score(self, sketch: dict[str, Any], eval_x: float, eval_y: float) -> float:
        dist = distance_point_to_bbox(eval_x, eval_y, sketch["bbox"])
        if dist <= SKETCH_MARGIN_MM:
            return 5.0
        if dist <= SKETCH_MARGIN_MM * 2:
            return 3.0
        if dist <= SKETCH_MARGIN_MM * 4:
            return 1.0
        return 0.0

    def orientation_score(
        self,
        sketch: dict[str, Any],
        insert_x: float,
        insert_y: float,
        eval_x: float,
        eval_y: float,
    ) -> float:
        cx, cy = bbox_centroid(sketch["bbox"])
        dx = eval_x - insert_x
        dy = eval_y - insert_y
        if abs(dx) < 1.0 and abs(dy) < 1.0:
            return 2.5
        to_sketch_x = cx - insert_x
        to_sketch_y = cy - insert_y
        dot = dx * to_sketch_x + dy * to_sketch_y
        mag = math.hypot(dx, dy) * math.hypot(to_sketch_x, to_sketch_y)
        if mag <= 0.0:
            return 2.5
        alignment = dot / mag
        if alignment > 0.7:
            return 5.0
        if alignment > 0.3:
            return 3.0
        return 1.0

    def _sketch_overlap_score(
        self,
        bbox: dict[str, float],
        expanded: dict[str, float],
        eval_x: float,
        eval_y: float,
        insert_x: float,
        insert_y: float,
        has_leader: bool,
    ) -> float:
        if point_in_bbox(eval_x, eval_y, bbox, 0.0):
            return 20.0
        if has_leader and point_in_bbox(eval_x, eval_y, expanded, 0.0):
            return 18.0
        if point_in_bbox(insert_x, insert_y, expanded, 0.0):
            return 14.0
        dist = distance_point_to_bbox(eval_x, eval_y, bbox)
        if dist <= SKETCH_MARGIN_MM:
            return 12.0
        if dist <= SKETCH_MARGIN_MM * 2:
            return 8.0
        if dist <= SKETCH_MARGIN_MM * 4:
            return 4.0
        return 0.0

    def _geometry_score(
        self,
        sketch: dict[str, Any],
        eval_x: float,
        eval_y: float,
        has_leader: bool,
    ) -> float:
        mark = str(sketch["beam_mark"]).upper()
        cell = self._cell_by_mark.get(mark)
        if cell is None:
            return 5.0 if point_in_bbox(eval_x, eval_y, sketch["bbox"], SKETCH_MARGIN_MM) else 0.0

        cell_box = {
            "xmin": float(cell["xmin"]) - CELL_MARGIN_MM,
            "ymin": float(cell["ymin"]) - CELL_MARGIN_MM,
            "xmax": float(cell["xmax"]) + CELL_MARGIN_MM,
            "ymax": float(cell["ymax"]) + CELL_MARGIN_MM,
        }
        if point_in_bbox(eval_x, eval_y, cell_box, 0.0):
            return 15.0
        if has_leader and point_in_bbox(eval_x, eval_y, sketch["bbox"], SKETCH_MARGIN_MM):
            return 12.0
        cx = (float(cell["xmin"]) + float(cell["xmax"])) / 2.0
        sketch_cx = (sketch["bbox"]["xmin"] + sketch["bbox"]["xmax"]) / 2.0
        if abs(cx - sketch_cx) < CELL_MARGIN_MM:
            return 6.0
        return 0.0
