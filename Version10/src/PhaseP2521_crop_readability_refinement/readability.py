"""Readability occupancy metrics for refined crops."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import (
    EXTREME_CROP_HEIGHT_MM,
    EXTREME_CROP_WIDTH_MM,
    MAX_ASPECT,
    MAX_WHITESPACE_RATIO_PARTIAL,
    MAX_WHITESPACE_RATIO_PASS,
    MIN_ANNOTATION_OCCUPANCY_PARTIAL,
    MIN_ANNOTATION_OCCUPANCY_PASS,
    MIN_ASPECT,
    MIN_BEAM_OCCUPANCY_PARTIAL,
    MIN_BEAM_OCCUPANCY_PASS,
    MIN_EVIDENCE_OCCUPANCY_PARTIAL,
    MIN_EVIDENCE_OCCUPANCY_PASS,
    READABILITY_FAIL,
    READABILITY_PARTIAL,
    READABILITY_PASS,
    READABILITY_REVIEW_REQUIRED,
    BBox,
)
from .geometry import as_bbox, bbox_area, bbox_dims, contains_bbox, intersect_bbox, union_bbox

MODEL_VERSION = "10.6.6"


def compute_occupancy_metrics(
    *,
    crop_bbox: BBox,
    target_beam_bbox: Optional[BBox],
    annotation_bbox: Optional[BBox],
    evidence_bbox: Optional[BBox],
) -> Dict[str, Any]:
    crop_area = bbox_area(crop_bbox)
    w, h = bbox_dims(crop_bbox)
    aspect = (w / h) if h > 1e-9 else 0.0

    beam_in = intersect_bbox(crop_bbox, target_beam_bbox) if target_beam_bbox else None
    ann_in = intersect_bbox(crop_bbox, annotation_bbox) if annotation_bbox else None
    evid_in = intersect_bbox(crop_bbox, evidence_bbox) if evidence_bbox else None

    beam_occ = (bbox_area(beam_in) / crop_area) if crop_area > 0 else 0.0
    ann_occ = (bbox_area(ann_in) / crop_area) if crop_area > 0 else 0.0
    evid_occ = (bbox_area(evid_in) / crop_area) if crop_area > 0 else 0.0
    # Approximate whitespace as unoccupied by beam∪evidence (deterministic proxy)
    occupied = union_bbox([beam_in, evid_in])
    whitespace = 1.0 - (bbox_area(occupied) / crop_area if crop_area > 0 else 0.0)
    whitespace = max(0.0, min(1.0, whitespace))

    extreme = bool(h >= EXTREME_CROP_HEIGHT_MM or w >= EXTREME_CROP_WIDTH_MM)
    ann_fully_inside = contains_bbox(crop_bbox, annotation_bbox)
    beam_present = bbox_area(beam_in) > 1.0
    evid_present = bbox_area(evid_in) > 1.0
    target_to_crop = (
        (bbox_area(target_beam_bbox) / crop_area)
        if (target_beam_bbox and crop_area > 0)
        else 0.0
    )

    return {
        "target_beam_bbox": list(target_beam_bbox) if target_beam_bbox else None,
        "annotation_bbox": list(annotation_bbox) if annotation_bbox else None,
        "evidence_bbox": list(evidence_bbox) if evidence_bbox else None,
        "crop_bbox": list(crop_bbox),
        "crop_area": crop_area,
        "crop_width_mm": w,
        "crop_height_mm": h,
        "aspect_ratio": aspect,
        "target_beam_occupancy": beam_occ,
        "annotation_occupancy": ann_occ,
        "evidence_occupancy": evid_occ,
        "whitespace_ratio": whitespace,
        "target_to_crop_area_ratio": target_to_crop,
        "annotation_fully_inside": ann_fully_inside,
        "beam_present_in_crop": beam_present,
        "evidence_present_in_crop": evid_present,
        "is_extreme": extreme,
    }


def classify_readability(metrics: Dict[str, Any], *, critical_clipped: bool = False) -> Dict[str, Any]:
    """
    Deterministic readability classification.
    Does not reinterpret engineering meaning.
    """
    flags = []
    if metrics.get("is_extreme"):
        flags.append("EXTREME_CROP")
    if critical_clipped or not metrics.get("annotation_fully_inside"):
        flags.append("ANNOTATION_CLIPPED")
    if not metrics.get("beam_present_in_crop"):
        flags.append("TARGET_BEAM_MISSING")
    if not metrics.get("evidence_present_in_crop"):
        flags.append("EVIDENCE_MISSING")

    ann_occ = float(metrics.get("annotation_occupancy") or 0.0)
    evid_occ = float(metrics.get("evidence_occupancy") or 0.0)
    beam_occ = float(metrics.get("target_beam_occupancy") or 0.0)
    white = float(metrics.get("whitespace_ratio") or 0.0)
    aspect = float(metrics.get("aspect_ratio") or 0.0)

    if metrics.get("is_extreme"):
        return {
            "readability_status": READABILITY_REVIEW_REQUIRED,
            "flags": flags + ["EXTREME_NOT_FORCED"],
            "reason": "extreme_crop_not_forced",
        }
    if critical_clipped or not metrics.get("annotation_fully_inside"):
        return {
            "readability_status": READABILITY_FAIL,
            "flags": flags,
            "reason": "critical_evidence_clipped",
        }
    if not metrics.get("beam_present_in_crop"):
        return {
            "readability_status": READABILITY_FAIL,
            "flags": flags,
            "reason": "target_beam_not_visible",
        }
    if aspect < MIN_ASPECT or aspect > MAX_ASPECT:
        flags.append("ASPECT_OUT_OF_RANGE")

    pass_ok = (
        ann_occ >= MIN_ANNOTATION_OCCUPANCY_PASS
        and evid_occ >= MIN_EVIDENCE_OCCUPANCY_PASS
        and beam_occ >= MIN_BEAM_OCCUPANCY_PASS
        and white <= MAX_WHITESPACE_RATIO_PASS
        and MIN_ASPECT <= aspect <= MAX_ASPECT
    )
    if pass_ok:
        return {
            "readability_status": READABILITY_PASS,
            "flags": flags,
            "reason": "target_evidence_visually_dominant",
        }

    partial_ok = (
        ann_occ >= MIN_ANNOTATION_OCCUPANCY_PARTIAL
        and evid_occ >= MIN_EVIDENCE_OCCUPANCY_PARTIAL
        and beam_occ >= MIN_BEAM_OCCUPANCY_PARTIAL
        and white <= MAX_WHITESPACE_RATIO_PARTIAL
        and metrics.get("annotation_fully_inside")
        and metrics.get("beam_present_in_crop")
    )
    if partial_ok:
        flags.append("USABLE_BUT_NOT_IDEAL")
        return {
            "readability_status": READABILITY_PARTIAL,
            "flags": flags,
            "reason": "usable_with_excess_context_or_small_target",
        }

    # Too small target / too much whitespace / unrelated dominance
    if ann_occ < MIN_ANNOTATION_OCCUPANCY_PARTIAL:
        flags.append("ANNOTATION_TOO_SMALL")
    if beam_occ < MIN_BEAM_OCCUPANCY_PARTIAL:
        flags.append("BEAM_TOO_SMALL")
    if white > MAX_WHITESPACE_RATIO_PARTIAL:
        flags.append("EXCESSIVE_WHITESPACE")

    return {
        "readability_status": READABILITY_FAIL,
        "flags": flags,
        "reason": "not_readable_for_vision_inspection",
    }


def overall_candidate_readability(local_status: str, context_status: str) -> str:
    order = {
        READABILITY_PASS: 3,
        READABILITY_PARTIAL: 2,
        READABILITY_FAIL: 1,
        READABILITY_REVIEW_REQUIRED: 0,
    }
    # Candidate overall = worse of the two refined crops (conservative)
    if order.get(local_status, -1) <= order.get(context_status, -1):
        return local_status
    return context_status


__all__ = [
    "classify_readability",
    "compute_occupancy_metrics",
    "overall_candidate_readability",
]
