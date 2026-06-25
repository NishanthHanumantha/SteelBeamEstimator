"""Validate reinforcement sketch geometry before annotation extraction."""

from typing import Tuple

from src.geometry.geometry_graph import SketchComponent

# Large merged reinforcement details (e.g. stacked B1 / B11).
MIN_LARGE_SKETCH_AREA_MM2 = 500_000.0
# Typical isolated beam section (~200 x 600 mm).
MIN_COMPACT_SKETCH_AREA_MM2 = 120_000.0
MIN_SEGMENT_COUNT = 5
MIN_BBOX_DIMENSION_MM = 80.0
MAX_COMPACT_SKETCH_WIDTH_MM = 1_200.0
MAX_COMPACT_SKETCH_HEIGHT_MM = 4_000.0
LOWER_DETAIL_LABEL_Y_MM = 12_000.0


def _is_compact_section(width: float, height: float, area: float) -> bool:
    return (
        area >= MIN_COMPACT_SKETCH_AREA_MM2
        and min(width, height) >= MIN_BBOX_DIMENSION_MM
        and width <= MAX_COMPACT_SKETCH_WIDTH_MM
        and height <= MAX_COMPACT_SKETCH_HEIGHT_MM
    )


def validate_sketch(
    sketch: SketchComponent | None,
    label_y: float | None = None,
) -> Tuple[bool, str]:
    if sketch is None:
        return False, "sketch is None"

    segment_count = len(sketch.segments)
    if segment_count < MIN_SEGMENT_COUNT:
        return False, f"segment count {segment_count} below {MIN_SEGMENT_COUNT}"

    xmin, ymin, xmax, ymax = sketch.bbox
    width = xmax - xmin
    height = ymax - ymin
    area = width * height

    if area <= 0:
        return False, f"bbox area {area:.0f} mm² is zero"

    if min(width, height) < MIN_BBOX_DIMENSION_MM:
        return False, (
            f"bbox dimension {min(width, height):.0f} mm below "
            f"{MIN_BBOX_DIMENSION_MM}"
        )

    is_large_detail = area >= MIN_LARGE_SKETCH_AREA_MM2
    is_compact = _is_compact_section(width, height, area)

    if label_y is not None and label_y < LOWER_DETAIL_LABEL_Y_MM:
        if not is_large_detail:
            return False, (
                f"bbox area {area:.0f} mm² below {MIN_LARGE_SKETCH_AREA_MM2} "
                f"for lower-detail row"
            )
        return True, "ok"

    if is_large_detail or is_compact:
        return True, "ok"

    return False, (
        f"bbox area {area:.0f} mm² below compact ({MIN_COMPACT_SKETCH_AREA_MM2}) "
        f"and large ({MIN_LARGE_SKETCH_AREA_MM2}) thresholds"
    )
