"""DXF ↔ pixel transforms and side-specific crop expansion."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import (
    EXPAND_BUFFER_PX,
    EXTREME_CROP_HEIGHT_MM,
    EXTREME_CROP_WIDTH_MM,
    GLYPH_OVERRUN_PAD_MM,
    MAX_REFINED_HEIGHT_MM,
    MAX_REFINED_WIDTH_MM,
    MAX_SIDE_EXPAND_MM,
    MIN_RENDER_SAFE_MARGIN_PX,
    BBox,
)

MODEL_VERSION = "10.6.7"


def as_bbox(seq: Optional[Sequence[float]]) -> Optional[BBox]:
    if not seq or len(seq) < 4:
        return None
    return (float(seq[0]), float(seq[1]), float(seq[2]), float(seq[3]))


def dxf_to_px(
    x: float,
    y: float,
    *,
    dxf_xlim: Tuple[float, float],
    dxf_ylim: Tuple[float, float],
    img_w: int,
    img_h: int,
) -> Tuple[float, float]:
    """Model mm → PNG pixel (origin top-left). Matches matplotlib savefig mapping."""
    xmin, xmax = dxf_xlim
    ymin, ymax = dxf_ylim
    xspan = max(xmax - xmin, 1e-9)
    yspan = max(ymax - ymin, 1e-9)
    px = (x - xmin) / xspan * float(img_w)
    py = (ymax - y) / yspan * float(img_h)
    return px, py


def px_to_dxf_delta(
    dpx: float,
    dpy: float,
    *,
    dxf_xlim: Tuple[float, float],
    dxf_ylim: Tuple[float, float],
    img_w: int,
    img_h: int,
) -> Tuple[float, float]:
    """Convert pixel deltas to DXF mm deltas (absolute magnitudes)."""
    xmin, xmax = dxf_xlim
    ymin, ymax = dxf_ylim
    xspan = max(xmax - xmin, 1e-9)
    yspan = max(ymax - ymin, 1e-9)
    return abs(dpx) * xspan / max(img_w, 1), abs(dpy) * yspan / max(img_h, 1)


def project_bbox_to_px(
    bbox: BBox,
    *,
    dxf_xlim: Tuple[float, float],
    dxf_ylim: Tuple[float, float],
    img_w: int,
    img_h: int,
) -> Tuple[int, int, int, int]:
    """Return inclusive-ish pixel bbox (x0,y0,x1,y1) with y downward."""
    corners = [
        dxf_to_px(bbox[0], bbox[1], dxf_xlim=dxf_xlim, dxf_ylim=dxf_ylim, img_w=img_w, img_h=img_h),
        dxf_to_px(bbox[0], bbox[3], dxf_xlim=dxf_xlim, dxf_ylim=dxf_ylim, img_w=img_w, img_h=img_h),
        dxf_to_px(bbox[2], bbox[1], dxf_xlim=dxf_xlim, dxf_ylim=dxf_ylim, img_w=img_w, img_h=img_h),
        dxf_to_px(bbox[2], bbox[3], dxf_xlim=dxf_xlim, dxf_ylim=dxf_ylim, img_w=img_w, img_h=img_h),
    ]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    x0 = int(max(0, math_floor(min(xs))))
    y0 = int(max(0, math_floor(min(ys))))
    x1 = int(min(img_w, math_ceil(max(xs))))
    y1 = int(min(img_h, math_ceil(max(ys))))
    return x0, y0, x1, y1


def math_floor(v: float) -> int:
    import math

    return int(math.floor(v))


def math_ceil(v: float) -> int:
    import math

    return int(math.ceil(v))


def inflate_bbox_mm(b: BBox, pad: float) -> BBox:
    return (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)


def annotation_vertical_side(
    *,
    annotation_bbox: Optional[BBox],
    beam_bbox: Optional[BBox],
) -> str:
    """TOP / BOTTOM / OTHER — crop-safety only, not semantic role."""
    if not annotation_bbox:
        return "OTHER"
    ay = 0.5 * (annotation_bbox[1] + annotation_bbox[3])
    if beam_bbox:
        by = 0.5 * (beam_bbox[1] + beam_bbox[3])
        if ay >= by:
            return "TOP"
        return "BOTTOM"
    return "OTHER"


def expand_extent_sides(
    extent: BBox,
    *,
    need_left_px: float,
    need_right_px: float,
    need_top_px: float,
    need_bottom_px: float,
    dxf_xlim: Tuple[float, float],
    dxf_ylim: Tuple[float, float],
    img_w: int,
    img_h: int,
) -> Tuple[BBox, Dict[str, float]]:
    """
    Expand only required sides. Image top ↔ DXF ymax; image bottom ↔ DXF ymin.
    """
    xmin, ymin, xmax, ymax = extent
    dx_left, _ = px_to_dxf_delta(
        need_left_px + (EXPAND_BUFFER_PX if need_left_px > 0 else 0),
        0,
        dxf_xlim=dxf_xlim,
        dxf_ylim=dxf_ylim,
        img_w=img_w,
        img_h=img_h,
    )
    dx_right, _ = px_to_dxf_delta(
        need_right_px + (EXPAND_BUFFER_PX if need_right_px > 0 else 0),
        0,
        dxf_xlim=dxf_xlim,
        dxf_ylim=dxf_ylim,
        img_w=img_w,
        img_h=img_h,
    )
    _, dy_top = px_to_dxf_delta(
        0,
        need_top_px + (EXPAND_BUFFER_PX if need_top_px > 0 else 0),
        dxf_xlim=dxf_xlim,
        dxf_ylim=dxf_ylim,
        img_w=img_w,
        img_h=img_h,
    )
    _, dy_bottom = px_to_dxf_delta(
        0,
        need_bottom_px + (EXPAND_BUFFER_PX if need_bottom_px > 0 else 0),
        dxf_xlim=dxf_xlim,
        dxf_ylim=dxf_ylim,
        img_w=img_w,
        img_h=img_h,
    )

    dx_left = min(dx_left, MAX_SIDE_EXPAND_MM)
    dx_right = min(dx_right, MAX_SIDE_EXPAND_MM)
    dy_top = min(dy_top, MAX_SIDE_EXPAND_MM)
    dy_bottom = min(dy_bottom, MAX_SIDE_EXPAND_MM)

    new_ext = (
        xmin - dx_left,
        ymin - dy_bottom,
        xmax + dx_right,
        ymax + dy_top,
    )
    # Soft size caps (not extreme thresholds)
    w = new_ext[2] - new_ext[0]
    h = new_ext[3] - new_ext[1]
    cx = 0.5 * (new_ext[0] + new_ext[2])
    cy = 0.5 * (new_ext[1] + new_ext[3])
    if w > MAX_REFINED_WIDTH_MM:
        half = MAX_REFINED_WIDTH_MM / 2.0
        new_ext = (cx - half, new_ext[1], cx + half, new_ext[3])
    if h > MAX_REFINED_HEIGHT_MM:
        half = MAX_REFINED_HEIGHT_MM / 2.0
        new_ext = (new_ext[0], cy - half, new_ext[2], cy + half)

    return new_ext, {
        "expand_left_mm": dx_left,
        "expand_right_mm": dx_right,
        "expand_top_mm": dy_top,
        "expand_bottom_mm": dy_bottom,
    }


def is_extreme(extent: BBox) -> bool:
    w = extent[2] - extent[0]
    h = extent[3] - extent[1]
    return bool(w >= EXTREME_CROP_WIDTH_MM or h >= EXTREME_CROP_HEIGHT_MM)


def geometric_contained(outer: BBox, inner: Optional[BBox], eps: float = 1e-3) -> bool:
    if not inner:
        return False
    return (
        inner[0] >= outer[0] - eps
        and inner[1] >= outer[1] - eps
        and inner[2] <= outer[2] + eps
        and inner[3] <= outer[3] + eps
    )


def deficit_px(margin: float, required: float = MIN_RENDER_SAFE_MARGIN_PX) -> float:
    return max(0.0, required - float(margin))


__all__ = [
    "annotation_vertical_side",
    "as_bbox",
    "deficit_px",
    "dxf_to_px",
    "expand_extent_sides",
    "geometric_contained",
    "inflate_bbox_mm",
    "is_extreme",
    "project_bbox_to_px",
    "px_to_dxf_delta",
]
