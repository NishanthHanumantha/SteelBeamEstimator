"""Geometry helpers for framing-plan beam matching."""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Point2D:
  x: float
  y: float

  def as_dict(self) -> dict[str, float]:
    return {"x": round(self.x, 3), "y": round(self.y, 3)}


@dataclass(frozen=True)
class LineSegment:
    """Angled or axis-aligned beam centreline segment."""

    x1: float
    y1: float
    x2: float
    y2: float
    layer: str
    handle: str
    entity_ids: Tuple[str, ...] = ()

    @property
    def length_mm(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2.0

    @property
    def start(self) -> Point2D:
        return Point2D(self.x1, self.y1)

    @property
    def end(self) -> Point2D:
        return Point2D(self.x2, self.y2)

    @property
    def angle_deg(self) -> float:
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1)) % 180.0

    @property
    def orientation(self) -> str:
        return classify_orientation(self.angle_deg)

    @property
    def bbox(self) -> dict[str, float]:
        return {
            "min_x": round(min(self.x1, self.x2), 3),
            "min_y": round(min(self.y1, self.y2), 3),
            "max_x": round(max(self.x1, self.x2), 3),
            "max_y": round(max(self.y1, self.y2), 3),
        }

    def as_centerline_dict(self) -> dict:
        return {
            "start_point": self.start.as_dict(),
            "end_point": self.end.as_dict(),
            "length_mm": round(self.length_mm, 3),
            "orientation": self.orientation,
            "angle_deg": round(self.angle_deg, 3),
        }


def classify_orientation(angle_deg: float, orthogonal_tol: float = 5.0) -> str:
    """Classify beam orientation without assuming orthogonal geometry only."""
    normalized = angle_deg % 180.0
    if normalized <= orthogonal_tol or normalized >= 180.0 - orthogonal_tol:
        return "horizontal"
    if abs(normalized - 90.0) <= orthogonal_tol:
        return "vertical"
    return "angled"


def point_to_segment_distance(
    px: float, py: float, segment: LineSegment
) -> float:
    """Shortest distance from point (px, py) to segment."""
    return point_to_line_distance(px, py, segment.x1, segment.y1, segment.x2, segment.y2)


def point_to_line_distance(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    qx = x1 + t * dx
    qy = y1 + t * dy
    return math.hypot(px - qx, py - qy)


def assign_segments_greedy(
    labels: List[Tuple[str, float, float]],
    segments: List[LineSegment],
    max_distance_mm: float,
) -> dict[str, LineSegment]:
    """
    One-to-one greedy assignment of labels to beam segments by proximity.

    labels: (beam_mark, label_x, label_y)
    """
    pairs: List[Tuple[float, str, int]] = []
    for mark, lx, ly in labels:
        for index, segment in enumerate(segments):
            distance = point_to_segment_distance(lx, ly, segment)
            pairs.append((distance, mark, index))

    pairs.sort(key=lambda item: item[0])

    used_marks: set[str] = set()
    used_segments: set[int] = set()
    assignment: dict[str, LineSegment] = {}

    for distance, mark, index in pairs:
        if mark in used_marks or index in used_segments:
            continue
        if distance > max_distance_mm:
            continue
        used_marks.add(mark)
        used_segments.add(index)
        assignment[mark] = segments[index]

    return assignment


def estimate_text_half_width(text: str, height_mm: float = 350.0) -> float:
    """Approximate horizontal half-width of a TEXT/MTEXT header label."""
    char_count = max(len(text.strip()), 1)
    return max(height_mm * char_count * 0.35, height_mm * 2.0)


def beam_mark_sort_key(mark: str) -> Tuple[int, str]:
    if mark.startswith("B") and mark[1:].isdigit():
        return (int(mark[1:]), mark)
    return (10_000, mark)
