"""Dominant orientation from title/envelope/evidence geometry. No beam-ID logic."""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from .geometry import as_extent, height, width

HORIZONTAL = "HORIZONTAL"
VERTICAL = "VERTICAL"
COMPACT = "COMPACT"
UNKNOWN = "UNKNOWN"


def dominant_orientation(
    *,
    mark: Optional[Dict[str, Any]] = None,
    extent: Optional[Sequence[float]] = None,
    outline: Optional[Sequence[float]] = None,
    evidence: Optional[Sequence[Dict[str, Any]]] = None,
) -> str:
    scores = {HORIZONTAL: 0.0, VERTICAL: 0.0, COMPACT: 0.0}
    if extent is not None:
        e = as_extent(extent)
        ar = width(e) / height(e)
        if ar >= 1.45:
            scores[HORIZONTAL] += 2.0 + min(ar, 4.0)
        elif ar <= 1.0 / 1.45:
            scores[VERTICAL] += 2.0 + min(1.0 / ar, 4.0)
        else:
            scores[COMPACT] += 1.0
    if outline and len(outline) >= 2:
        span_y = abs(float(outline[1]) - float(outline[0]))
        if mark is not None:
            depth = float(mark.get("depth_mm") or 600.0)
            if span_y <= 1.8 * depth:
                scores[HORIZONTAL] += 1.5
            elif span_y >= 3.2 * depth:
                scores[VERTICAL] += 1.2
    xs = []
    ys = []
    if mark is not None:
        try:
            xs.append(float(mark["x"]))
            ys.append(float(mark["y"]))
        except (TypeError, ValueError, KeyError):
            pass
    for row in evidence or []:
        try:
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))
        except (TypeError, ValueError, KeyError):
            continue
    if len(xs) >= 3:
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        if dx > 1.4 * max(dy, 1.0):
            scores[HORIZONTAL] += 2.2
        elif dy > 1.4 * max(dx, 1.0):
            scores[VERTICAL] += 2.2
        else:
            scores[COMPACT] += 0.8
    best = max(scores.items(), key=lambda kv: kv[1])
    if best[1] < 0.8:
        return UNKNOWN
    return best[0]


def axis_sides(orientation: str) -> Sequence[str]:
    if orientation == VERTICAL:
        return ("top", "bottom")
    if orientation == HORIZONTAL:
        return ("left", "right")
    return ("left", "right", "top", "bottom")


__all__ = ["COMPACT", "HORIZONTAL", "UNKNOWN", "VERTICAL", "axis_sides", "dominant_orientation"]
