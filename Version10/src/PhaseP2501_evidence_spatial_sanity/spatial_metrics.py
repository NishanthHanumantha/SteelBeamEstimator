"""Spatial distance / crop ratio metrics (diagnostic only)."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

BBox = Tuple[float, float, float, float]


def as_bbox(seq: Optional[Sequence[float]]) -> Optional[BBox]:
    if not seq or len(seq) < 4:
        return None
    return (float(seq[0]), float(seq[1]), float(seq[2]), float(seq[3]))


def bbox_center(b: BBox) -> Tuple[float, float]:
    return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)


def bbox_wh(b: BBox) -> Tuple[float, float]:
    return (max(b[2] - b[0], 0.0), max(b[3] - b[1], 0.0))


def bbox_area(b: BBox) -> float:
    w, h = bbox_wh(b)
    return w * h


def x_gap(a: BBox, b: BBox) -> float:
    if a[2] < b[0]:
        return b[0] - a[2]
    if b[2] < a[0]:
        return a[0] - b[2]
    return 0.0


def y_gap(a: BBox, b: BBox) -> float:
    if a[3] < b[1]:
        return b[1] - a[3]
    if b[3] < a[1]:
        return a[1] - b[3]
    return 0.0


def center_distance(a: BBox, b: BBox) -> float:
    ca, cb = bbox_center(a), bbox_center(b)
    return math.hypot(ca[0] - cb[0], ca[1] - cb[1])


def evidence_object_metrics(
    *,
    obj_id: str,
    obj_kind: str,
    obj_bbox: Optional[BBox],
    beam_bbox: BBox,
) -> Dict[str, Any]:
    if not obj_bbox:
        return {
            "object_id": obj_id,
            "object_kind": obj_kind,
            "has_bbox": False,
            "spatial_distance_mm": None,
            "center_to_center_mm": None,
            "x_gap_mm": None,
            "y_gap_mm": None,
            "evidence_to_beam_size_ratio": None,
        }
    bw, bh = bbox_wh(beam_bbox)
    ew, eh = bbox_wh(obj_bbox)
    beam_diag = math.hypot(bw, bh) or 1.0
    ev_diag = math.hypot(ew, eh)
    return {
        "object_id": obj_id,
        "object_kind": obj_kind,
        "has_bbox": True,
        "bbox": list(obj_bbox),
        "spatial_distance_mm": round(math.hypot(x_gap(beam_bbox, obj_bbox), y_gap(beam_bbox, obj_bbox)), 3),
        "center_to_center_mm": round(center_distance(beam_bbox, obj_bbox), 3),
        "x_gap_mm": round(x_gap(beam_bbox, obj_bbox), 3),
        "y_gap_mm": round(y_gap(beam_bbox, obj_bbox), 3),
        "evidence_to_beam_size_ratio": round(ev_diag / beam_diag, 4),
    }


def crop_beam_ratios(beam_bbox: BBox, crop_bbox: BBox) -> Dict[str, Any]:
    bw, bh = bbox_wh(beam_bbox)
    cw, ch = bbox_wh(crop_bbox)
    ba = bbox_area(beam_bbox) or 1.0
    ca = bbox_area(crop_bbox)
    return {
        "beam_width_mm": round(bw, 3),
        "beam_height_mm": round(bh, 3),
        "crop_width_mm": round(cw, 3),
        "crop_height_mm": round(ch, 3),
        "crop_width_to_beam_width_ratio": round(cw / bw, 4) if bw else None,
        "crop_height_to_beam_height_ratio": round(ch / bh, 4) if bh else None,
        "crop_area_to_beam_area_ratio": round(ca / ba, 4),
        "crop_aspect_wh": round(cw / ch, 4) if ch else None,
    }


def collect_beam_spatial_metrics(evidence: Dict[str, Any]) -> Dict[str, Any]:
    beam = as_bbox((evidence.get("target_beam") or {}).get("bbox"))
    crop = as_bbox(((evidence.get("evidence_window") or {}).get("bbox")))
    if not beam or not crop:
        return {"beam_id": evidence.get("beam_id"), "error": "missing_bbox"}

    objects: List[Dict[str, Any]] = []
    for a in evidence.get("annotations") or []:
        objects.append(
            evidence_object_metrics(
                obj_id=str(a.get("annotation_id")),
                obj_kind="annotation",
                obj_bbox=as_bbox(a.get("bbox")),
                beam_bbox=beam,
            )
        )
    for l in evidence.get("leaders") or []:
        objects.append(
            evidence_object_metrics(
                obj_id=str(l.get("leader_id")),
                obj_kind="leader",
                obj_bbox=as_bbox(l.get("bbox")),
                beam_bbox=beam,
            )
        )
    for r in evidence.get("reinforcement") or []:
        objects.append(
            evidence_object_metrics(
                obj_id=str(r.get("reinforcement_id")),
                obj_kind="reinforcement",
                obj_bbox=as_bbox(r.get("bbox")),
                beam_bbox=beam,
            )
        )

    ratios = crop_beam_ratios(beam, crop)
    max_y = max((o.get("y_gap_mm") or 0.0) for o in objects) if objects else 0.0
    max_dist = max((o.get("spatial_distance_mm") or 0.0) for o in objects) if objects else 0.0
    dominant = None
    if objects:
        dominant = max(
            objects,
            key=lambda o: (o.get("y_gap_mm") or 0.0, o.get("spatial_distance_mm") or 0.0),
        )

    return {
        "beam_id": evidence.get("beam_id"),
        "beam_bbox": list(beam),
        "crop_bbox": list(crop),
        "ratios": ratios,
        "max_y_gap_mm": round(max_y, 3),
        "max_spatial_distance_mm": round(max_dist, 3),
        "dominant_expander": dominant,
        "objects": objects,
        "object_count": len(objects),
    }
