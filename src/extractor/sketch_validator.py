"""Validate reinforcement sketch geometry before annotation extraction."""

from typing import Tuple

from src.geometry.geometry_graph import SketchComponent

MIN_SKETCH_AREA_MM2 = 500000.0
MIN_SEGMENT_COUNT = 5


def validate_sketch(sketch: SketchComponent | None) -> Tuple[bool, str]:
    if sketch is None:
        return False, "sketch is None"

    xmin, ymin, xmax, ymax = sketch.bbox
    width = xmax - xmin
    height = ymax - ymin
    area = width * height

    if area < MIN_SKETCH_AREA_MM2:
        return False, f"bbox area {area:.0f} mm² below {MIN_SKETCH_AREA_MM2}"

    segment_count = len(sketch.segments)
    if segment_count < MIN_SEGMENT_COUNT:
        return False, f"segment count {segment_count} below {MIN_SEGMENT_COUNT}"

    return True, "ok"
