"""Deterministic bbox helpers for P2.5.2.1 — reuse T1.8.2 primitives."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from PhaseT182_adaptive_render_extent.adaptive_bbox import (
    inflate_bbox,
    union_bbox,
)

from .config import BBox

MODEL_VERSION = "10.6.6"


def as_bbox(seq: Optional[Sequence[float]]) -> Optional[BBox]:
    if not seq or len(seq) < 4:
        return None
    return (float(seq[0]), float(seq[1]), float(seq[2]), float(seq[3]))


def bbox_area(b: Optional[BBox]) -> float:
    if not b:
        return 0.0
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def bbox_dims(b: Optional[BBox]) -> Tuple[float, float]:
    if not b:
        return 0.0, 0.0
    return max(0.0, b[2] - b[0]), max(0.0, b[3] - b[1])


def intersect_bbox(a: Optional[BBox], b: Optional[BBox]) -> Optional[BBox]:
    if not a or not b:
        return None
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def contains_bbox(outer: BBox, inner: Optional[BBox], eps: float = 1e-3) -> bool:
    if not inner:
        return False
    return (
        inner[0] >= outer[0] - eps
        and inner[1] >= outer[1] - eps
        and inner[2] <= outer[2] + eps
        and inner[3] <= outer[3] + eps
    )


def clip_bbox_to_max_span(
    b: BBox,
    *,
    center_x: float,
    center_y: float,
    max_w: float,
    max_h: float,
) -> BBox:
    """Keep bbox centered near (center_x, center_y) within max span."""
    w = b[2] - b[0]
    h = b[3] - b[1]
    x0, y0, x1, y1 = b
    if w > max_w:
        half = max_w / 2.0
        # Prefer keeping center; clamp to original
        cx = min(max(center_x, b[0] + half), b[2] - half)
        x0 = cx - half
        x1 = cx + half
    if h > max_h:
        half = max_h / 2.0
        cy = min(max(center_y, b[1] + half), b[3] - half)
        y0 = cy - half
        y1 = cy + half
    return (x0, y0, x1, y1)


def enforce_min_size(b: BBox, *, min_w: float, min_h: float) -> BBox:
    w = b[2] - b[0]
    h = b[3] - b[1]
    cx = 0.5 * (b[0] + b[2])
    cy = 0.5 * (b[1] + b[3])
    if w < min_w:
        half = min_w / 2.0
        b = (cx - half, b[1], cx + half, b[3])
    if h < min_h:
        half = min_h / 2.0
        b = (b[0], cy - half, b[2], cy + half)
    return b


def local_beam_snippet(
    beam: BBox,
    *,
    center_x: float,
    center_y: float,
    half_span_x: float,
    half_span_y: float,
) -> BBox:
    """
    Portion of the target beam near the annotation.
    Falls back to full beam if intersection is empty (degenerate).
    """
    window = (
        center_x - half_span_x,
        center_y - half_span_y,
        center_x + half_span_x,
        center_y + half_span_y,
    )
    hit = intersect_bbox(beam, window)
    if hit and bbox_area(hit) > 1.0:
        return hit
    # Prefer x-local strip across full beam height (common for long beams)
    strip = (center_x - half_span_x, beam[1], center_x + half_span_x, beam[3])
    hit2 = intersect_bbox(beam, strip)
    if hit2 and bbox_area(hit2) > 1.0:
        return hit2
    return beam


def collect_evidence_boxes(
    evidence: Dict[str, Any],
    *,
    annotation_id: str,
) -> Dict[str, Any]:
    """Gather annotation / leader / owned / described-bar bboxes for one candidate."""
    anns = evidence.get("annotations") or []
    ann = next((a for a in anns if str(a.get("annotation_id")) == str(annotation_id)), None)
    ann_bbox = as_bbox((ann or {}).get("bbox"))
    pos = (ann or {}).get("position") or {}
    cx = float(pos.get("x") or (ann_bbox[0] + ann_bbox[2]) / 2.0 if ann_bbox else 0.0)
    cy = float(pos.get("y") or (ann_bbox[1] + ann_bbox[3]) / 2.0 if ann_bbox else 0.0)

    # Leaders linked via accepted chains for this annotation
    chain_leader_ids = set()
    for c in ((evidence.get("leader_chains") or {}).get("accepted") or []):
        if str(c.get("annotation_id")) == str(annotation_id):
            for lid in c.get("leaders") or []:
                chain_leader_ids.add(str(lid))

    leader_boxes: List[BBox] = []
    for ldr in evidence.get("leaders") or []:
        lid = str(ldr.get("leader_id") or "")
        bb = as_bbox(ldr.get("bbox"))
        if not bb:
            continue
        if chain_leader_ids:
            if lid in chain_leader_ids:
                leader_boxes.append(bb)
            continue
        # No chain ids: keep leaders near annotation
        mid = ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0)
        if abs(mid[0] - cx) <= 2500 and abs(mid[1] - cy) <= 2500:
            leader_boxes.append(bb)

    # If chain ids existed but none matched geometry list, fall back to proximity
    if chain_leader_ids and not leader_boxes and ann_bbox:
        for ldr in evidence.get("leaders") or []:
            bb = as_bbox(ldr.get("bbox"))
            if not bb:
                continue
            mid = ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0)
            if abs(mid[0] - cx) <= 2500 and abs(mid[1] - cy) <= 2500:
                leader_boxes.append(bb)

    owned_boxes: List[BBox] = []
    for og in evidence.get("owned_geometry") or []:
        bb = as_bbox(og.get("bbox"))
        if not bb:
            continue
        mid = ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0)
        if abs(mid[0] - cx) <= 4000 and abs(mid[1] - cy) <= 4000:
            owned_boxes.append(bb)

    # Described PhysicalBars from chains (accepted only)
    described_ids = set()
    for c in ((evidence.get("leader_chains") or {}).get("accepted") or []):
        if str(c.get("annotation_id")) == str(annotation_id):
            for did in c.get("describes") or []:
                described_ids.add(str(did))

    reinf_boxes: List[BBox] = []
    for bar in evidence.get("reinforcement") or []:
        rid = str(bar.get("reinforcement_id") or bar.get("bar_id") or "")
        bb = as_bbox(bar.get("bbox"))
        if not bb:
            continue
        if described_ids and rid in described_ids:
            reinf_boxes.append(bb)
            continue
        mid = ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0)
        if abs(mid[0] - cx) <= 2000 and abs(mid[1] - cy) <= 2000:
            reinf_boxes.append(bb)

    beam = as_bbox((evidence.get("target_beam") or {}).get("bbox"))
    original_crop = as_bbox(((evidence.get("evidence_window") or {}).get("bbox")))

    core_parts: List[Optional[BBox]] = [ann_bbox, *leader_boxes, *owned_boxes, *reinf_boxes]
    evidence_core = union_bbox(core_parts)

    return {
        "annotation": ann,
        "annotation_bbox": ann_bbox,
        "center_x": cx,
        "center_y": cy,
        "leader_bboxes": leader_boxes,
        "owned_bboxes": owned_boxes,
        "reinforcement_bboxes": reinf_boxes,
        "beam_bbox": beam,
        "original_crop_bbox": original_crop,
        "evidence_core_bbox": evidence_core,
        "described_ids": sorted(described_ids),
    }


__all__ = [
    "as_bbox",
    "bbox_area",
    "bbox_dims",
    "clip_bbox_to_max_span",
    "collect_evidence_boxes",
    "contains_bbox",
    "enforce_min_size",
    "inflate_bbox",
    "intersect_bbox",
    "local_beam_snippet",
    "union_bbox",
]
