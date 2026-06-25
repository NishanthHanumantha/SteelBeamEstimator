"""Bounding-box helpers for beam grouping and annotation ownership."""

import math
from typing import Any, Dict, List, Optional, Tuple

BBox = Dict[str, float]


def union_bbox(bboxes: List[BBox]) -> BBox:
    if not bboxes:
        return {"xmin": 0.0, "ymin": 0.0, "xmax": 0.0, "ymax": 0.0}
    return {
        "xmin": min(b["xmin"] for b in bboxes),
        "ymin": min(b["ymin"] for b in bboxes),
        "xmax": max(b["xmax"] for b in bboxes),
        "ymax": max(b["ymax"] for b in bboxes),
    }


def expand_bbox(bbox: BBox, margin_mm: float) -> BBox:
    return {
        "xmin": bbox["xmin"] - margin_mm,
        "ymin": bbox["ymin"] - margin_mm,
        "xmax": bbox["xmax"] + margin_mm,
        "ymax": bbox["ymax"] + margin_mm,
    }


def bbox_centroid(bbox: BBox) -> Tuple[float, float]:
    return (
        (bbox["xmin"] + bbox["xmax"]) / 2.0,
        (bbox["ymin"] + bbox["ymax"]) / 2.0,
    )


def point_in_bbox(
    x: float,
    y: float,
    bbox: BBox,
    margin_mm: float = 0.0,
) -> bool:
    if margin_mm > 0.0:
        bbox = expand_bbox(bbox, margin_mm)
    return (
        bbox["xmin"] <= x <= bbox["xmax"]
        and bbox["ymin"] <= y <= bbox["ymax"]
    )


def bbox_width(bbox: BBox) -> float:
    return max(0.0, bbox["xmax"] - bbox["xmin"])


def bbox_height(bbox: BBox) -> float:
    return max(0.0, bbox["ymax"] - bbox["ymin"])


def horizontal_overlap_ratio(bbox_a: BBox, bbox_b: BBox) -> float:
    overlap = min(bbox_a["xmax"], bbox_b["xmax"]) - max(bbox_a["xmin"], bbox_b["xmin"])
    if overlap <= 0.0:
        return 0.0
    min_width = min(bbox_width(bbox_a), bbox_width(bbox_b))
    if min_width <= 0.0:
        return 0.0
    return overlap / min_width


def vertical_band_overlap_ratio(band_a: BBox, band_b: BBox) -> float:
    overlap = min(band_a["ymax"], band_b["ymax"]) - max(band_a["ymin"], band_b["ymin"])
    if overlap <= 0.0:
        return 0.0
    min_height = min(bbox_height(band_a), bbox_height(band_b))
    if min_height <= 0.0:
        return 0.0
    return overlap / min_height


def distance_point_to_bbox(x: float, y: float, bbox: BBox) -> float:
    cx = max(bbox["xmin"], min(x, bbox["xmax"]))
    cy = max(bbox["ymin"], min(y, bbox["ymax"]))
    return math.hypot(x - cx, y - cy)


def sketches_for_beam(
    beam_mark: str, sketches: List[dict[str, Any]]
) -> List[dict[str, Any]]:
    mark = beam_mark.upper()
    return [s for s in sketches if str(s["beam_mark"]).upper() == mark]


def detail_band_for_beam(
    beam_mark: str, sketches: List[dict[str, Any]]
) -> Optional[BBox]:
    beam_sketches = sketches_for_beam(beam_mark, sketches)
    if not beam_sketches:
        return None
    return union_bbox([s["bbox"] for s in beam_sketches])

