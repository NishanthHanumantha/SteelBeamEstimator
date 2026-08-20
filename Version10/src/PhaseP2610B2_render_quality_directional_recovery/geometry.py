"""Generic crop-extent helpers. No beam-ID logic."""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

Extent = Tuple[float, float, float, float]


def as_extent(extent: Sequence[float]) -> Extent:
    xmin, ymin, xmax, ymax = (float(extent[0]), float(extent[1]), float(extent[2]), float(extent[3]))
    if xmax < xmin:
        xmin, xmax = xmax, xmin
    if ymax < ymin:
        ymin, ymax = ymax, ymin
    return (xmin, ymin, xmax, ymax)


def width(extent: Sequence[float]) -> float:
    e = as_extent(extent)
    return max(e[2] - e[0], 1e-6)


def height(extent: Sequence[float]) -> float:
    e = as_extent(extent)
    return max(e[3] - e[1], 1e-6)


def area(extent: Sequence[float]) -> float:
    return width(extent) * height(extent)


def expand_side(extent: Sequence[float], side: str, step_mm: float) -> Extent:
    xmin, ymin, xmax, ymax = as_extent(extent)
    if side == "left":
        xmin -= step_mm
    elif side == "right":
        xmax += step_mm
    elif side == "bottom":
        ymin -= step_mm
    elif side == "top":
        ymax += step_mm
    return (xmin, ymin, xmax, ymax)


def intersect(a: Sequence[float], b: Sequence[float]) -> Optional[Extent]:
    ax = as_extent(a)
    bx = as_extent(b)
    xmin = max(ax[0], bx[0])
    ymin = max(ax[1], bx[1])
    xmax = min(ax[2], bx[2])
    ymax = min(ax[3], bx[3])
    if xmax <= xmin + 1.0 or ymax <= ymin + 1.0:
        return None
    return (xmin, ymin, xmax, ymax)


def union(a: Sequence[float], b: Sequence[float]) -> Extent:
    ax = as_extent(a)
    bx = as_extent(b)
    return (min(ax[0], bx[0]), min(ax[1], bx[1]), max(ax[2], bx[2]), max(ax[3], bx[3]))


def clamp_to_limits(
    extent: Sequence[float],
    *,
    x_left: float,
    x_right: float,
    y_floor: float,
    y_cap: float,
    max_w: float,
    max_h: float,
    min_w: float,
    min_h: float,
    anchor: Optional[Sequence[float]] = None,
) -> Extent:
    xmin, ymin, xmax, ymax = as_extent(extent)
    xmin = max(xmin, x_left)
    xmax = min(xmax, x_right)
    ymin = max(ymin, y_floor)
    ymax = min(ymax, y_cap)
    ax = float(anchor[0]) if anchor is not None else 0.5 * (xmin + xmax)
    ay = float(anchor[1]) if anchor is not None else 0.5 * (ymin + ymax)
    if xmax - xmin > max_w:
        extra = (xmax - xmin - max_w) / 2.0
        xmin += extra
        xmax -= extra
        if ax < xmin:
            xmax += xmin - ax
            xmin = ax
        if ax > xmax:
            xmin -= ax - xmax
            xmax = ax
    if ymax - ymin > max_h:
        extra = (ymax - ymin - max_h) / 2.0
        ymin += extra
        ymax -= extra
        if ay < ymin:
            ymax += ymin - ay
            ymin = ay
        if ay > ymax:
            ymin -= ay - ymax
            ymax = ay
    if xmax - xmin < min_w:
        mid = 0.5 * (xmin + xmax)
        xmin, xmax = mid - min_w / 2.0, mid + min_w / 2.0
    if ymax - ymin < min_h:
        mid = 0.5 * (ymin + ymax)
        ymin, ymax = mid - min_h / 2.0, mid + min_h / 2.0
    xmin = max(xmin, x_left)
    xmax = min(xmax, x_right)
    ymin = max(ymin, y_floor)
    ymax = min(ymax, y_cap)
    if xmax <= xmin + min_w * 0.4:
        xmin, xmax = x_left, min(x_left + min_w, x_right)
    if ymax <= ymin + min_h * 0.4:
        ymin, ymax = y_floor, min(y_floor + min_h, y_cap)
    return as_extent((xmin, ymin, xmax, ymax))


def factor_vs(initial: Sequence[float], current: Sequence[float]) -> float:
    return max(width(current) / width(initial), height(current) / height(initial))


def pixel_to_dxf(px: float, py: float, extent: Sequence[float], img_w: int, img_h: int) -> Tuple[float, float]:
    xmin, ymin, xmax, ymax = as_extent(extent)
    x = xmin + (px / max(img_w, 1)) * (xmax - xmin)
    y = ymax - (py / max(img_h, 1)) * (ymax - ymin)
    return (x, y)


def unique_sides(sides: Iterable[str]) -> List[str]:
    out: List[str] = []
    for s in sides:
        if s and s not in out:
            out.append(s)
    return out


__all__ = [
    "Extent",
    "area",
    "as_extent",
    "clamp_to_limits",
    "expand_side",
    "factor_vs",
    "height",
    "intersect",
    "pixel_to_dxf",
    "union",
    "unique_sides",
    "width",
]
