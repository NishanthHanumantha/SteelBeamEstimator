"""
Read-only geometry helpers for QA.4.1 dropped-entity audit.
MODEL_VERSION: 10.5.0

Uses existing T18 envelope constants as diagnostic bands only.
Does NOT change production thresholds.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Existing T18 beam_envelope constants (exposed for diagnostic banding only)
SUPPORT_EXT_MM = 350.0
ANN_REACH_DEPTH_FACTOR = 4.0

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]


def as_bbox(extent: Any) -> Optional[BBox]:
    if not extent:
        return None
    if isinstance(extent, dict):
        try:
            return (
                float(extent["x0"] if "x0" in extent else extent["xmin"]),
                float(extent["y0"] if "y0" in extent else extent["ymin"]),
                float(extent["x1"] if "x1" in extent else extent["xmax"]),
                float(extent["y1"] if "y1" in extent else extent["ymax"]),
            )
        except Exception:
            return None
    if isinstance(extent, (list, tuple)) and len(extent) >= 4:
        try:
            x0, y0, x1, y1 = map(float, extent[:4])
            if x1 < x0:
                x0, x1 = x1, x0
            if y1 < y0:
                y0, y1 = y1, y0
            return (x0, y0, x1, y1)
        except Exception:
            return None
    return None


def point_in_bbox(pt: Optional[Point], bbox: Optional[BBox], pad: float = 0.0) -> bool:
    if not pt or not bbox:
        return False
    x, y = pt
    return (
        bbox[0] - pad <= x <= bbox[2] + pad
        and bbox[1] - pad <= y <= bbox[3] + pad
    )


def dist_point_to_bbox(pt: Optional[Point], bbox: Optional[BBox]) -> Optional[float]:
    if not pt or not bbox:
        return None
    x, y = pt
    dx = 0.0 if bbox[0] <= x <= bbox[2] else min(abs(x - bbox[0]), abs(x - bbox[2]))
    dy = 0.0 if bbox[1] <= y <= bbox[3] else min(abs(y - bbox[1]), abs(y - bbox[3]))
    if dx == 0.0 and dy == 0.0:
        return 0.0
    return round((dx * dx + dy * dy) ** 0.5, 3)


def bbox_center(bbox: BBox) -> Point:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def entity_point_from_attrs(attrs: Dict[str, Any]) -> Optional[Point]:
    a = attrs or {}
    for kx, ky in (("x", "y"), ("tip_x", "tip_y"), ("cx", "cy"), ("tail_x", "tail_y")):
        if kx in a and ky in a:
            try:
                return (float(a[kx]), float(a[ky]))
            except Exception:
                pass
    if "start_x" in a and "y_position" in a:
        try:
            sx = float(a["start_x"])
            ex = float(a.get("end_x", sx))
            return (0.5 * (sx + ex), float(a["y_position"]))
        except Exception:
            pass
    if "extent" in a:
        bb = as_bbox(a["extent"])
        if bb:
            return bbox_center(bb)
    return None


def entity_bounds_from_attrs(attrs: Dict[str, Any]) -> Optional[BBox]:
    a = attrs or {}
    if "extent" in a:
        return as_bbox(a["extent"])
    if "tip_x" in a and "tail_x" in a:
        try:
            xs = [float(a["tip_x"]), float(a["tail_x"])]
            ys = [float(a["tip_y"]), float(a["tail_y"])]
            return (min(xs), min(ys), max(xs), max(ys))
        except Exception:
            return None
    if "start_x" in a and "end_x" in a and "y_position" in a:
        try:
            y = float(a["y_position"])
            return (float(a["start_x"]), y, float(a["end_x"]), y)
        except Exception:
            return None
    pt = entity_point_from_attrs(a)
    if pt:
        return (pt[0], pt[1], pt[0], pt[1])
    return None


def spatial_class(
    dist: Optional[float],
    *,
    inside: bool,
    on_boundary: bool,
    depth_mm: float,
) -> str:
    if inside and not on_boundary:
        return "INSIDE"
    if on_boundary or (dist is not None and dist <= 1e-6):
        return "BOUNDARY"
    if dist is None:
        return "UNKNOWN"
    near = SUPPORT_EXT_MM  # existing support extension constant
    moderate = max(near, float(depth_mm or 600.0) * ANN_REACH_DEPTH_FACTOR)
    if dist <= near:
        return "NEAR_OUTSIDE"
    if dist <= moderate:
        return "MODERATE_OUTSIDE"
    return "FAR_OUTSIDE"


def axis_metrics(
    pt: Optional[Point], centreline: Optional[Dict[str, Any]], crop: Optional[BBox]
) -> Dict[str, Any]:
    if not pt:
        return {
            "beam_axis_distance": None,
            "longitudinal_projection": None,
            "transverse_projection": None,
        }
    try:
        if centreline:
            x0 = float(centreline.get("x0"))
            x1 = float(centreline.get("x1"))
            y = float(centreline.get("y") or centreline.get("mark_y") or 0.0)
        elif crop:
            x0, y0, x1, y1 = crop
            y = 0.5 * (y0 + y1)
        else:
            return {
                "beam_axis_distance": None,
                "longitudinal_projection": None,
                "transverse_projection": None,
            }
        longi = pt[0] - min(x0, x1)
        trans = abs(pt[1] - y)
        return {
            "beam_axis_distance": round(trans, 3),
            "longitudinal_projection": round(longi, 3),
            "transverse_projection": round(trans, 3),
            "axis_y": y,
            "span_x0": min(x0, x1),
            "span_x1": max(x0, x1),
        }
    except Exception:
        return {
            "beam_axis_distance": None,
            "longitudinal_projection": None,
            "transverse_projection": None,
        }


def longitudinal_overlap(pt: Optional[Point], crop: Optional[BBox], pad: float = 200.0) -> bool:
    if not pt or not crop:
        return False
    return crop[0] - pad <= pt[0] <= crop[2] + pad
