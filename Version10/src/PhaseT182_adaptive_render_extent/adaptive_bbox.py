"""
T1.8.2 — Axis-aligned bbox helpers for owned graphical objects.
MODEL_VERSION: 9.5.2
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

MODEL_VERSION = "9.5.2"

BBox = Tuple[float, float, float, float]  # xmin, ymin, xmax, ymax


def empty_bbox() -> Optional[BBox]:
    return None


def union_bbox(boxes: Iterable[Optional[BBox]]) -> Optional[BBox]:
    xs0: List[float] = []
    ys0: List[float] = []
    xs1: List[float] = []
    ys1: List[float] = []
    for b in boxes:
        if not b:
            continue
        xs0.append(b[0])
        ys0.append(b[1])
        xs1.append(b[2])
        ys1.append(b[3])
    if not xs0:
        return None
    return (min(xs0), min(ys0), max(xs1), max(ys1))


def inflate_bbox(b: BBox, margin_x: float, margin_y: float) -> BBox:
    return (b[0] - margin_x, b[1] - margin_y, b[2] + margin_x, b[3] + margin_y)


def point_bbox(x: float, y: float, pad: float = 0.0) -> BBox:
    return (x - pad, y - pad, x + pad, y + pad)


def segment_bbox(x0: float, y0: float, x1: float, y1: float, pad: float = 0.0) -> BBox:
    return (
        min(x0, x1) - pad,
        min(y0, y1) - pad,
        max(x0, x1) + pad,
        max(y0, y1) + pad,
    )


def contains(outer: BBox, inner: BBox, eps: float = 1e-6) -> bool:
    return (
        inner[0] >= outer[0] - eps
        and inner[1] >= outer[1] - eps
        and inner[2] <= outer[2] + eps
        and inner[3] <= outer[3] + eps
    )


def touches_border(outer: BBox, inner: BBox, tol: float = 1.0) -> bool:
    """True if inner touches or crosses the outer border within tol."""
    if not contains(outer, inner, eps=tol):
        return True
    return (
        abs(inner[0] - outer[0]) <= tol
        or abs(inner[1] - outer[1]) <= tol
        or abs(inner[2] - outer[2]) <= tol
        or abs(inner[3] - outer[3]) <= tol
    )


def estimate_text_bbox(
    x: float,
    y: float,
    text: str,
    *,
    char_width_mm: float = 48.0,
    text_height_mm: float = 110.0,
    above_pad_mm: float = 160.0,
) -> BBox:
    """
    Deterministic annotation text rectangle in drawing units.
    Labels are drawn above the anchor in the ownership renderer.
    """
    n = max(len(text or ""), 1)
    half_w = 0.5 * n * char_width_mm
    # Anchor near bottom of text block; extend upward for label + pad
    return (
        x - half_w,
        y - 0.35 * text_height_mm,
        x + half_w,
        y + above_pad_mm + text_height_mm,
    )


def object_record(
    obj_id: str, kind: str, bbox: BBox, meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return {
        "id": obj_id,
        "kind": kind,
        "bbox": list(bbox),
        **(meta or {}),
    }
