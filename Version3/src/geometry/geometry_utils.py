"""Shared geometry helpers for Phase D.4.2 rebar resolution."""

import math
from typing import Literal, Tuple

Point = Tuple[float, float]
Bbox = dict[str, float]
BeamAxis = Literal["X", "Y"]

_EXCLUDED_LAYER_SUBSTRINGS = frozenset(
    {
        "DIM",
        "TEXT",
        "ANNO",
        "GRID",
        "TITLE",
        "SLAB",
        "IDEN",
        "CONSTR",
        "HATCH",
        "DEFPOINTS",
    }
)


def expand_bbox(bbox: Bbox, margin: float) -> Bbox:
    return {
        "xmin": float(bbox["xmin"]) - margin,
        "ymin": float(bbox["ymin"]) - margin,
        "xmax": float(bbox["xmax"]) + margin,
        "ymax": float(bbox["ymax"]) + margin,
    }


def segment_intersects_bbox(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    bbox: Bbox,
) -> bool:
    """True when line segment overlaps expanded sketch bbox."""
    xmin = float(bbox["xmin"])
    ymin = float(bbox["ymin"])
    xmax = float(bbox["xmax"])
    ymax = float(bbox["ymax"])
    seg_xmin, seg_xmax = min(x1, x2), max(x1, x2)
    seg_ymin, seg_ymax = min(y1, y2), max(y1, y2)
    if seg_xmax < xmin or seg_xmin > xmax:
        return False
    if seg_ymax < ymin or seg_ymin > ymax:
        return False
    return True


def point_in_bbox(x: float, y: float, bbox: Bbox) -> bool:
    return (
        float(bbox["xmin"]) <= x <= float(bbox["xmax"])
        and float(bbox["ymin"]) <= y <= float(bbox["ymax"])
    )


def bbox_midpoint(bbox: Bbox) -> Point:
    return (
        (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0,
        (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0,
    )


def beam_span(bbox: Bbox, axis: BeamAxis) -> float:
    if axis == "X":
        return max(0.0, float(bbox["xmax"]) - float(bbox["xmin"]))
    return max(0.0, float(bbox["ymax"]) - float(bbox["ymin"]))


def beam_axis_from_bbox(bbox: Bbox) -> BeamAxis:
    width = float(bbox["xmax"]) - float(bbox["xmin"])
    height = float(bbox["ymax"]) - float(bbox["ymin"])
    return "X" if width >= height else "Y"


def segment_length(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def segment_angle_degrees(x1: float, y1: float, x2: float, y2: float) -> float:
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    if dx == 0.0 and dy == 0.0:
        return 0.0
    return abs(math.degrees(math.atan2(dy, dx)))


def span_along_axis(
    x1: float, y1: float, x2: float, y2: float, axis: BeamAxis
) -> Tuple[float, float]:
    if axis == "X":
        lo, hi = min(x1, x2), max(x1, x2)
        perp = abs(y2 - y1)
    else:
        lo, hi = min(y1, y2), max(y1, y2)
        perp = abs(x2 - x1)
    return hi - lo, perp


def point_to_segment_distance(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> Tuple[float, float, float]:
    """Return distance, closest point x, closest point y."""
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - x1, py - y1), x1, y1
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx = x1 + t * dx
    cy = y1 + t * dy
    return math.hypot(px - cx, py - cy), cx, cy


def coverage_ratio(bar_length: float, beam_length: float) -> float:
    if beam_length <= 0.0:
        return 0.0
    return min(1.0, bar_length / beam_length)


def continuity_from_coverage(
    ratio: float, threshold: float
) -> Literal["CONTINUOUS", "PARTIAL", "UNKNOWN"]:
    if ratio >= threshold:
        return "CONTINUOUS"
    if ratio > 0.0:
        return "PARTIAL"
    return "UNKNOWN"


def position_from_coordinate(
    value: float, bbox: Bbox, axis: BeamAxis, band_ratio: float
) -> Literal["TOP", "BOTTOM", "UNKNOWN"]:
    if axis == "X":
        ymin, ymax = float(bbox["ymin"]), float(bbox["ymax"])
        height = ymax - ymin
        if height <= 0.0:
            return "UNKNOWN"
        mid = ymin + height / 2.0
        band = height * band_ratio
    else:
        xmin, xmax = float(bbox["xmin"]), float(bbox["xmax"])
        width = xmax - xmin
        if width <= 0.0:
            return "UNKNOWN"
        mid = xmin + width / 2.0
        band = width * band_ratio

    if value > mid + band:
        return "TOP"
    if value < mid - band:
        return "BOTTOM"
    if value >= mid:
        return "TOP"
    return "BOTTOM"


def is_excluded_layer(layer: str) -> bool:
    upper = layer.upper()
    return any(token in upper for token in _EXCLUDED_LAYER_SUBSTRINGS)


def is_reinforcement_layer(layer: str) -> bool:
    upper = layer.upper()
    if is_excluded_layer(layer):
        return False
    return "REINF" in upper or "REBAR" in upper
