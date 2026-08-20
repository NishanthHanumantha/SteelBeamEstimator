"""Meaningful vs harmless crop-border contact. No beam-ID logic."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from PhaseP2610B_adaptive_beam_detail_crop.evidence import KIND_OTHER, classify_text, owned_by_mark
from PhaseP2610A_beam_region_crop_audit.title_localizer import iter_text_inserts

from .geometry import as_extent
from .orientation import HORIZONTAL, VERTICAL, axis_sides

BAND_MM = 140.0


def _point_near_side(x: float, y: float, extent: Sequence[float], side: str, band: float) -> bool:
    xmin, ymin, xmax, ymax = as_extent(extent)
    if side == "left":
        return xmin - band <= x <= xmin + band and ymin - band <= y <= ymax + band
    if side == "right":
        return xmax - band <= x <= xmax + band and ymin - band <= y <= ymax + band
    if side == "bottom":
        return ymin - band <= y <= ymin + band and xmin - band <= x <= xmax + band
    if side == "top":
        return ymax - band <= y <= ymax + band and xmin - band <= x <= xmax + band
    return False


def _line_crosses(x0: float, y0: float, x1: float, y1: float, extent: Sequence[float], side: str) -> bool:
    xmin, ymin, xmax, ymax = as_extent(extent)
    inside0 = xmin <= x0 <= xmax and ymin <= y0 <= ymax
    inside1 = xmin <= x1 <= xmax and ymin <= y1 <= ymax
    if inside0 == inside1:
        return False
    if side == "left":
        return min(x0, x1) < xmin < max(x0, x1)
    if side == "right":
        return min(x0, x1) < xmax < max(x0, x1)
    if side == "bottom":
        return min(y0, y1) < ymin < max(y0, y1)
    if side == "top":
        return min(y0, y1) < ymax < max(y0, y1)
    return False


def meaningful_border_contact(
    *,
    msp: Any,
    mark: Dict[str, Any],
    titles: Sequence[Dict[str, Any]],
    extent: Sequence[float],
    image_contact: Optional[Dict[str, bool]] = None,
    orientation: str = "UNKNOWN",
) -> Dict[str, Any]:
    image_contact = image_contact or {}
    priority = set(axis_sides(orientation))
    sides = ("left", "right", "top", "bottom")
    geom = {s: False for s in sides}
    text_hit = {s: False for s in sides}
    if msp is not None:
        for text, x, y in iter_text_inserts(msp):
            kind = classify_text(text)
            if kind == KIND_OTHER:
                continue
            if not owned_by_mark(x, y, mark, titles):
                continue
            for s in sides:
                if _point_near_side(x, y, extent, s, BAND_MM + 80.0):
                    text_hit[s] = True
        for e in msp:
            try:
                dt = e.dxftype()
            except Exception:
                continue
            if dt not in ("LINE", "LWPOLYLINE", "POLYLINE"):
                continue
            pts: List[tuple] = []
            try:
                if dt == "LINE":
                    pts = [(float(e.dxf.start.x), float(e.dxf.start.y)), (float(e.dxf.end.x), float(e.dxf.end.y))]
                else:
                    pts = [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
            except Exception:
                continue
            if len(pts) < 2:
                continue
            mx, my = float(mark["x"]), float(mark["y"])
            if min(abs(p[0] - mx) + abs(p[1] - my) for p in pts) > 5200.0:
                continue
            for i in range(len(pts) - 1):
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                if length < 180.0:
                    continue
                for s in sides:
                    if _line_crosses(x0, y0, x1, y1, extent, s) or _point_near_side(x0, y0, extent, s, 80.0):
                        if orientation == HORIZONTAL and s in ("left", "right"):
                            geom[s] = True
                        elif orientation == VERTICAL and s in ("top", "bottom"):
                            geom[s] = True
                        elif orientation not in (HORIZONTAL, VERTICAL):
                            geom[s] = True
    meaningful = {}
    harmless = {}
    for s in sides:
        img = bool(image_contact.get(s))
        hit = bool(geom[s] or text_hit[s] or (img and s in priority))
        meaningful[s] = hit
        harmless[s] = img and not hit
    return {
        "meaningful_target_clipping_suspect": any(meaningful.values()),
        "harmless_border_contact": any(harmless.values()),
        "sides": meaningful,
        "harmless_sides": harmless,
        "geometry_sides": geom,
        "text_sides": text_hit,
    }


__all__ = ["meaningful_border_contact"]
