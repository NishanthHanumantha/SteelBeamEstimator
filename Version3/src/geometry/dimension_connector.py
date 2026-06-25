"""Connect DIMENSION entities to reinforcement sketch geometry."""

import math
from typing import Iterable, Sequence, Tuple

from ezdxf.document import Drawing

from src.geometry.geometry_graph import CONNECT_TOLERANCE_MM, MAX_LABEL_DISTANCE_MM

Bbox = Tuple[float, float, float, float]
Point = Tuple[float, float]
Segment = Tuple[float, float, float, float, str, str]

DIMENSION_LAYERS = frozenset(
    {
        "-S-DIM",
        "-STR-RF-DIM",
        "-S-STIRUP",
    }
)

DIMENSION_CONNECT_TOLERANCE_MM = 250.0
SKETCH_TEXT_X_PAD_MM = 2200.0
SKETCH_TEXT_Y_PAD_ABOVE_MM = 5000.0
SKETCH_TEXT_Y_PAD_BELOW_MM = 800.0


def _distance(px: float, py: float, qx: float, qy: float) -> float:
    return math.hypot(px - qx, py - qy)


def _point_segment_distance(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        return _distance(px, py, x1, y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return _distance(px, py, proj_x, proj_y)


def _dimension_points(entity) -> list[Point]:
    points: list[Point] = []
    for attr in ("defpoint", "defpoint2", "defpoint3", "defpoint4", "text_midpoint"):
        if not hasattr(entity.dxf, attr):
            continue
        point = entity.dxf.get(attr)
        if point is None:
            continue
        points.append((float(point.x), float(point.y)))
    return points


def _segment_endpoints(segments: Sequence[Segment]) -> list[Point]:
    endpoints: list[Point] = []
    for segment in segments:
        endpoints.append((segment[0], segment[1]))
        endpoints.append((segment[2], segment[3]))
    return endpoints


def _point_near_endpoints(
    point: Point,
    endpoints: Sequence[Point],
    tolerance: float,
) -> bool:
    px, py = point
    return any(_distance(px, py, ex, ey) <= tolerance for ex, ey in endpoints)


def _point_near_segments(
    point: Point,
    segments: Sequence[Segment],
    tolerance: float,
) -> bool:
    px, py = point
    return any(
        _point_segment_distance(px, py, segment[0], segment[1], segment[2], segment[3])
        <= tolerance
        for segment in segments
    )


def _point_in_bbox(point: Point, bbox: Bbox, pad: float = 0.0) -> bool:
    px, py = point
    xmin, ymin, xmax, ymax = bbox
    return (
        xmin - pad <= px <= xmax + pad
        and ymin - pad <= py <= ymax + pad
    )


def _merge_bbox(first: Bbox, second: Bbox) -> Bbox:
    return (
        min(first[0], second[0]),
        min(first[1], second[1]),
        max(first[2], second[2]),
        max(first[3], second[3]),
    )


def _bbox_from_points(points: Iterable[Point]) -> Bbox:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _text_near_sketch(
    tx: float,
    ty: float,
    sketch_bbox: Bbox,
) -> bool:
    xmin, ymin, xmax, ymax = sketch_bbox
    if xmin <= tx <= xmax and ymin <= ty <= ymax:
        return True
    return (
        xmin - SKETCH_TEXT_X_PAD_MM <= tx <= xmax + SKETCH_TEXT_X_PAD_MM
        and ymin - SKETCH_TEXT_Y_PAD_BELOW_MM <= ty <= ymax + SKETCH_TEXT_Y_PAD_ABOVE_MM
    )


def expand_bbox_with_dimensions(
    doc: Drawing,
    sketch_bbox: Bbox,
    segments: Sequence[Segment],
    x_column: Bbox,
    label_x: float,
    label_y: float,
    tolerance: float = DIMENSION_CONNECT_TOLERANCE_MM,
    max_passes: int = 8,
) -> Bbox:
    """
    Grow the sketch bbox by chaining DIMENSION entities whose geometry
    touches the sketch or already-linked dimensions.
    """
    endpoints = _segment_endpoints(segments)
    bbox = sketch_bbox
    linked_handles: set[str] = set()
    msp = doc.modelspace()

    for _ in range(max_passes):
        growth_points: list[Point] = []
        for entity in msp.query("DIMENSION"):
            if entity.dxf.layer not in DIMENSION_LAYERS:
                continue
            handle = str(entity.dxf.handle)
            if handle in linked_handles:
                continue

            points = _dimension_points(entity)
            if not points:
                continue

            text_x, text_y = points[-1]
            if not _text_near_sketch(text_x, text_y, sketch_bbox):
                continue

            mid_x = sum(point[0] for point in points) / len(points)
            if not x_column[0] <= mid_x <= x_column[2]:
                continue

            touches_sketch = any(
                _point_near_endpoints(point, endpoints, CONNECT_TOLERANCE_MM)
                or _point_near_segments(point, segments, tolerance)
                or _point_in_bbox(point, bbox, pad=CONNECT_TOLERANCE_MM)
                for point in points
            )
            if not touches_sketch:
                continue

            linked_handles.add(handle)
            growth_points.extend(points)
            endpoints.extend(points)

        if not growth_points:
            break
        bbox = _merge_bbox(bbox, _bbox_from_points(growth_points))

    for entity in msp.query("DIMENSION"):
        if entity.dxf.layer not in {"-STR-RF-DIM", "-S-STIRUP"}:
            continue
        points = _dimension_points(entity)
        if not points:
            continue
        text_x, text_y = points[-1]
        if not x_column[0] <= text_x <= x_column[2]:
            continue
        if _distance(text_x, text_y, label_x, label_y) > MAX_LABEL_DISTANCE_MM:
            continue
        if not _text_near_sketch(text_x, text_y, sketch_bbox):
            continue
        bbox = _merge_bbox(bbox, _bbox_from_points(points))

    return (
        round(bbox[0], 6),
        round(bbox[1], 6),
        round(bbox[2], 6),
        round(bbox[3], 6),
    )
