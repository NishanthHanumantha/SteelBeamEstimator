"""Spatial metrics for beam / bar / annotation relationships."""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence, Tuple

BBox = Tuple[float, float, float, float]


def as_bbox(seq: Optional[Sequence[float]]) -> Optional[BBox]:
    if not seq or len(seq) < 4:
        return None
    return (float(seq[0]), float(seq[1]), float(seq[2]), float(seq[3]))


def y_offset(beam_y0: float, beam_y1: float, bar_y: float) -> float:
    if beam_y0 <= bar_y <= beam_y1:
        return 0.0
    if bar_y < beam_y0:
        return beam_y0 - bar_y
    return bar_y - beam_y1


def x_overlap(beam_x0: float, beam_x1: float, bar_x0: float, bar_x1: float) -> float:
    a0, a1 = (bar_x0, bar_x1) if bar_x0 <= bar_x1 else (bar_x1, bar_x0)
    return max(0.0, min(a1, beam_x1) - max(a0, beam_x0))


def euclid(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def bar_spatial_vs_beam(
    *,
    bar_y: float,
    bar_sx: float,
    bar_ex: float,
    concrete: Dict[str, float],
    depth_mm: float,
) -> Dict[str, Any]:
    y0, y1 = concrete["y0"], concrete["y1"]
    x0, x1 = concrete["x0"], concrete["x1"]
    yo = y_offset(y0, y1, bar_y)
    xo = x_overlap(x0, x1, bar_sx, bar_ex)
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    bx = (bar_sx + bar_ex) / 2.0
    dist = euclid(cx, cy, bx, bar_y)
    inside = yo == 0.0 and xo > 0.0
    position = "inside" if yo == 0.0 else ("above" if bar_y > y1 else "below")
    return {
        "beam_to_bar_y_offset_mm": round(yo, 3),
        "beam_to_bar_x_overlap_mm": round(xo, 3),
        "beam_to_bar_euclidean_mm": round(dist, 3),
        "beam_depth_mm": depth_mm,
        "bar_to_beam_depth_ratio": round(yo / depth_mm, 4) if depth_mm else None,
        "intersects_or_overlaps_envelope": inside or (xo > 80 and yo < 50),
        "bar_vs_envelope_position": position,
    }
