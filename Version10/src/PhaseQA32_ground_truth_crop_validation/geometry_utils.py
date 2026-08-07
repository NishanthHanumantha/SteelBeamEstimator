"""
Geometry helpers for QA.3.2 crop validation (read-only).
MODEL_VERSION: 10.0.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

BBox = Tuple[float, float, float, float]


def as_bbox(extent: Any) -> Optional[BBox]:
    if not extent or not isinstance(extent, (list, tuple)) or len(extent) < 4:
        return None
    try:
        x0, y0, x1, y1 = map(float, extent[:4])
    except Exception:
        return None
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    if (x1 - x0) <= 1e-9 or (y1 - y0) <= 1e-9:
        return None
    return (x0, y0, x1, y1)


def bbox_area(b: Optional[BBox]) -> float:
    if not b:
        return 0.0
    return abs((b[2] - b[0]) * (b[3] - b[1]))


def bbox_center(b: BBox) -> Tuple[float, float]:
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def bbox_size(b: BBox) -> Tuple[float, float]:
    return (b[2] - b[0], b[3] - b[1])


def expand_bbox(b: BBox, pad_frac: float = 0.15, pad_abs: float = 0.0) -> BBox:
    w, h = bbox_size(b)
    pad_x = max(pad_abs, w * pad_frac)
    pad_y = max(pad_abs, h * pad_frac)
    return (b[0] - pad_x, b[1] - pad_y, b[2] + pad_x, b[3] + pad_y)


def expand_bbox_margin(
    b: BBox, margin: Optional[Dict[str, Any]] = None, default_frac: float = 0.15
) -> BBox:
    if not margin:
        return expand_bbox(b, pad_frac=default_frac)
    fx = float(margin.get("frac_x") or default_frac)
    fy = float(margin.get("frac_y") or default_frac)
    min_mm = float(margin.get("min_margin_mm") or 0.0)
    w, h = bbox_size(b)
    pad_x = max(min_mm, w * fx, float(margin.get("horizontal_mm") or 0.0) * 0.5)
    pad_y = max(min_mm, h * fy, float(margin.get("vertical_mm") or 0.0) * 0.5)
    # If absolute margins already represent full expansion from T182, prefer frac
    if margin.get("horizontal_mm") and margin.get("vertical_mm"):
        # T182 stores applied margins; reconstruct loosely via frac if present
        pad_x = max(min_mm, w * fx)
        pad_y = max(min_mm, h * fy)
    return (b[0] - pad_x, b[1] - pad_y, b[2] + pad_x, b[3] + pad_y)


def intersection(a: Optional[BBox], b: Optional[BBox]) -> Optional[BBox]:
    if not a or not b:
        return None
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def iou(a: Optional[BBox], b: Optional[BBox]) -> float:
    inter = intersection(a, b)
    if not inter:
        return 0.0
    union = bbox_area(a) + bbox_area(b) - bbox_area(inter)
    return round(bbox_area(inter) / union, 4) if union > 0 else 0.0


def overlap_pct(a: Optional[BBox], b: Optional[BBox]) -> float:
    """Intersection over area of a (manual coverage of expected)."""
    inter = intersection(a, b)
    if not a or not inter:
        return 0.0
    aa = bbox_area(a)
    return round(100.0 * bbox_area(inter) / aa, 2) if aa else 0.0


def alignment_metrics(expected: BBox, actual: BBox) -> Dict[str, Any]:
    ecx, ecy = bbox_center(expected)
    acx, acy = bbox_center(actual)
    ew, eh = bbox_size(expected)
    aw, ah = bbox_size(actual)
    return {
        "delta_x": round(acx - ecx, 3),
        "delta_y": round(acy - ecy, 3),
        "centroid_error": round(((acx - ecx) ** 2 + (acy - ecy) ** 2) ** 0.5, 3),
        "width_diff": round(aw - ew, 3),
        "height_diff": round(ah - eh, 3),
        "scale_x": round(aw / ew, 4) if ew else None,
        "scale_y": round(ah / eh, 4) if eh else None,
        "rotation_diff": 0.0,  # axis-aligned crops only in current pipeline
        "iou": iou(expected, actual),
        "overlap_pct_actual_in_expected": overlap_pct(actual, expected),
        "overlap_pct_expected_in_actual": overlap_pct(expected, actual),
        "crop_similarity_pct": round(100.0 * iou(expected, actual), 2),
    }


def entity_in_bbox(entity_bbox: Optional[BBox], crop: BBox, tol: float = 0.0) -> bool:
    if not entity_bbox:
        return False
    inter = intersection(
        entity_bbox,
        (crop[0] - tol, crop[1] - tol, crop[2] + tol, crop[3] + tol),
    )
    return inter is not None
