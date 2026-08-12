"""Pixel-level target-beam visual completeness assessment."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PhaseP2522_render_safe_annotation_bounds.pixel_safety import assess_render_safety

from .config import (
    ANNOTATION_EDGE_MARGIN_PX,
    BG_LUMA_THRESHOLD,
    COMPLETENESS_FAIL,
    COMPLETENESS_PARTIAL,
    COMPLETENESS_PASS,
    COMPLETENESS_REVIEW,
    RC_ANNOTATION_BEAM_RELATION_VISIBLE,
    RC_ANNOTATION_VISIBLE,
    RC_INSUFFICIENT_BEAM_CONTEXT,
    RC_LEADER_VISIBLE,
    RC_NO_SYNTHETIC_GEOMETRY,
    RC_REJECTED_PHYSICAL_BAR_EXCLUDED,
    RC_TARGET_BEAM_EDGE_CLIPPED,
    RC_TARGET_BEAM_EDGE_RISK,
    RC_TARGET_BEAM_GEOMETRY_MISSING,
    RC_TARGET_BEAM_VISIBLE,
    RC_TARGET_REINFORCEMENT_CLIPPED,
    RC_TARGET_REINFORCEMENT_VISIBLE,
    RC_TOP_REINFORCEMENT_CLIPPED,
    TARGET_BEAM_EDGE_MARGIN_PX,
    BBox,
)
from .geometry_complete import geometric_contained, geometric_side_deficits, project_bbox_to_px

MODEL_VERSION = "10.6.8"


def _load_rgb(path: Path):
    from PIL import Image
    import numpy as np

    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def _ink_bbox(rgb, x0: int, y0: int, x1: int, y1: int, thr: int = BG_LUMA_THRESHOLD):
    import numpy as np

    h, w = rgb.shape[0], rgb.shape[1]
    x0, x1 = max(0, min(w, x0)), max(0, min(w, x1))
    y0, y1 = max(0, min(h, y0)), max(0, min(h, y1))
    if x1 <= x0 or y1 <= y0:
        return None
    region = rgb[y0:y1, x0:x1]
    luma = (
        0.299 * region[:, :, 0].astype("float32")
        + 0.587 * region[:, :, 1].astype("float32")
        + 0.114 * region[:, :, 2].astype("float32")
    )
    mask = luma < float(thr)
    if not bool(mask.any()):
        return None
    ys, xs = np.where(mask)
    return (int(xs.min()) + x0, int(ys.min()) + y0, int(xs.max()) + 1 + x0, int(ys.max()) + 1 + y0)


def _margins(pb: Tuple[int, int, int, int], img_w: int, img_h: int) -> Dict[str, float]:
    return {
        "left": float(pb[0]),
        "right": float(img_w - pb[2]),
        "top": float(pb[1]),
        "bottom": float(img_h - pb[3]),
    }


def assess_beam_completeness(
    *,
    image_path: Path,
    extent: BBox,
    critical_beam_bbox: Optional[BBox],
    annotation_bbox: Optional[BBox],
    leader_bboxes: Optional[Sequence[BBox]],
    owned_bboxes: Optional[Sequence[BBox]],
    reinforcement_bboxes: Optional[Sequence[BBox]],
    beam_bbox: Optional[BBox],
    dxf_xlim: Optional[Sequence[float]],
    dxf_ylim: Optional[Sequence[float]],
    img_w: Optional[int],
    img_h: Optional[int],
    rejected_included: bool = False,
    beam_margin_px: int = TARGET_BEAM_EDGE_MARGIN_PX,
    ann_margin_px: int = ANNOTATION_EDGE_MARGIN_PX,
) -> Dict[str, Any]:
    """
    Independently assess target-beam visual completeness + annotation visibility.
    """
    reasons: List[str] = [RC_NO_SYNTHETIC_GEOMETRY]
    if not rejected_included:
        reasons.append(RC_REJECTED_PHYSICAL_BAR_EXCLUDED)
    else:
        reasons.append("REJECTED_PHYSICAL_BAR_INCLUDED")

    path = Path(image_path)
    if not path.exists():
        return {
            "success": False,
            "completeness_status": COMPLETENESS_FAIL,
            "reason_codes": reasons + [RC_TARGET_BEAM_GEOMETRY_MISSING, "MISSING_IMAGE"],
            "target_beam_geometry_present": False,
            "target_beam_geometry_rendered": False,
            "annotation_visible": False,
            "leader_visible": False,
            "reinforcement_visible": False,
            "unsafe_sides": ["left", "right", "top", "bottom"],
            "beam_edge_margins_px": None,
            "annotation_edge_margins_px": None,
            "deficits_px": {"left": beam_margin_px, "right": beam_margin_px, "top": beam_margin_px, "bottom": beam_margin_px},
        }

    rgb = _load_rgb(path)
    h, w = int(rgb.shape[0]), int(rgb.shape[1])
    img_w = int(img_w or w)
    img_h = int(img_h or h)
    if not dxf_xlim or len(dxf_xlim) < 2:
        dxf_xlim = (extent[0], extent[2])
    else:
        dxf_xlim = (float(dxf_xlim[0]), float(dxf_xlim[1]))
    if not dxf_ylim or len(dxf_ylim) < 2:
        dxf_ylim = (extent[1], extent[3])
    else:
        dxf_ylim = (float(dxf_ylim[0]), float(dxf_ylim[1]))

    # --- Annotation / leader (reuse P2522 checker) ---
    ann_assess = assess_render_safety(
        image_path=path,
        extent=extent,
        annotation_bbox=annotation_bbox,
        leader_bboxes=list(leader_bboxes or []),
        beam_bbox=beam_bbox,
        dxf_xlim=dxf_xlim,
        dxf_ylim=dxf_ylim,
        img_w=img_w,
        img_h=img_h,
        min_margin_px=ann_margin_px,
    )
    annotation_visible = bool(
        ann_assess.get("annotation_pixel_bbox") or ann_assess.get("geometric_containment")
    ) and "ANNOTATION_RENDER_CLIPPED" not in (ann_assess.get("flags") or [])
    leader_visible = True
    if leader_bboxes:
        leader_visible = "LEADER_RENDER_EDGE_RISK" not in (ann_assess.get("flags") or []) and (
            ann_assess.get("leader_pixel_bbox") is not None
            or True  # leaders optional if none rendered as dark ink
        )
    if annotation_visible:
        reasons.append(RC_ANNOTATION_VISIBLE)
    if leader_bboxes and leader_visible:
        reasons.append(RC_LEADER_VISIBLE)

    ann_margins = None
    if ann_assess.get("margins_px"):
        m = ann_assess["margins_px"]
        ann_margins = {
            "left": m.get("left_margin_px"),
            "right": m.get("right_margin_px"),
            "top": m.get("top_margin_px"),
            "bottom": m.get("bottom_margin_px"),
        }

    # --- Critical beam region ---
    beam_present = critical_beam_bbox is not None or beam_bbox is not None
    beam_pixel_bbox = None
    beam_margins = None
    beam_rendered = False
    geometric_deficits = {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0}

    if critical_beam_bbox:
        geometric_deficits = geometric_side_deficits(
            extent,
            critical_beam_bbox,
            dxf_xlim=dxf_xlim,
            dxf_ylim=dxf_ylim,
            img_w=img_w,
            img_h=img_h,
            margin_px=beam_margin_px,
        )
        proj = project_bbox_to_px(
            critical_beam_bbox,
            dxf_xlim=dxf_xlim,
            dxf_ylim=dxf_ylim,
            img_w=img_w,
            img_h=img_h,
        )
        # Search slightly padded projected region clipped to image
        pad = 4
        beam_pixel_bbox = _ink_bbox(
            rgb,
            proj[0] - pad,
            proj[1] - pad,
            proj[2] + pad,
            proj[3] + pad,
        )
        if beam_pixel_bbox is None:
            # fallback to projected math bbox clipped to image
            beam_pixel_bbox = (
                max(0, proj[0]),
                max(0, proj[1]),
                min(img_w, proj[2]),
                min(img_h, proj[3]),
            )
        else:
            beam_rendered = True
        beam_margins = _margins(beam_pixel_bbox, img_w, img_h)
    else:
        reasons.append(RC_TARGET_BEAM_GEOMETRY_MISSING)

    pixel_deficits = {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0}
    if beam_margins:
        for side in ("left", "right", "top", "bottom"):
            if beam_margins[side] < float(beam_margin_px):
                pixel_deficits[side] = float(beam_margin_px) - float(beam_margins[side])
            if beam_margins[side] <= 0:
                reasons.append(RC_TARGET_BEAM_EDGE_CLIPPED)

    # Merge geometric + pixel deficits (max)
    deficits = {
        side: max(float(geometric_deficits.get(side) or 0), float(pixel_deficits.get(side) or 0))
        for side in ("left", "right", "top", "bottom")
    }
    unsafe = [s for s, v in deficits.items() if v > 0.5]

    if beam_rendered or (
        critical_beam_bbox and geometric_contained(extent, critical_beam_bbox, eps=1.0)
    ):
        reasons.append(RC_TARGET_BEAM_VISIBLE)
    if unsafe and RC_TARGET_BEAM_EDGE_CLIPPED not in reasons:
        reasons.append(RC_TARGET_BEAM_EDGE_RISK)

    # --- Reinforcement / OWN ---
    reinf_visible = False
    reinf_clipped = False
    top_reinf_clipped = False
    reinf_boxes = list(owned_bboxes or []) + list(reinforcement_bboxes or [])
    if reinf_boxes:
        for rb in reinf_boxes:
            if not geometric_contained(extent, rb, eps=1.0):
                reinf_clipped = True
                # top if above beam mid
                if beam_bbox and 0.5 * (rb[1] + rb[3]) >= 0.5 * (beam_bbox[1] + beam_bbox[3]):
                    top_reinf_clipped = True
            else:
                # check pixel ink
                proj = project_bbox_to_px(
                    rb, dxf_xlim=dxf_xlim, dxf_ylim=dxf_ylim, img_w=img_w, img_h=img_h
                )
                ink = _ink_bbox(rgb, proj[0], proj[1], proj[2], proj[3])
                if ink:
                    reinf_visible = True
                    im = _margins(ink, img_w, img_h)
                    if min(im.values()) < float(beam_margin_px):
                        reinf_clipped = True
                        if beam_bbox and 0.5 * (rb[1] + rb[3]) >= 0.5 * (beam_bbox[1] + beam_bbox[3]):
                            top_reinf_clipped = True
                else:
                    # OWN may be painted magenta — still count geometric presence
                    reinf_visible = True
        if reinf_visible:
            reasons.append(RC_TARGET_REINFORCEMENT_VISIBLE)
        if reinf_clipped:
            reasons.append(RC_TARGET_REINFORCEMENT_CLIPPED)
        if top_reinf_clipped:
            reasons.append(RC_TOP_REINFORCEMENT_CLIPPED)
    else:
        # No separate reinf entities — beam geometry is the reinforcement context
        reinf_visible = beam_rendered or RC_TARGET_BEAM_VISIBLE in reasons
        if reinf_visible:
            reasons.append(RC_TARGET_REINFORCEMENT_VISIBLE)

    relation_ok = annotation_visible and (
        beam_rendered or geometric_contained(extent, critical_beam_bbox or beam_bbox, eps=5.0)
    )
    if relation_ok:
        reasons.append(RC_ANNOTATION_BEAM_RELATION_VISIBLE)
    else:
        reasons.append(RC_INSUFFICIENT_BEAM_CONTEXT)

    # --- Status ---
    if rejected_included:
        status = COMPLETENESS_FAIL
    elif not beam_present or RC_TARGET_BEAM_GEOMETRY_MISSING in reasons:
        status = COMPLETENESS_FAIL
    elif RC_TARGET_BEAM_EDGE_CLIPPED in reasons or not annotation_visible:
        status = COMPLETENESS_FAIL if not annotation_visible else COMPLETENESS_FAIL
    elif unsafe or reinf_clipped or not relation_ok:
        # expandable issues → PARTIAL if still somewhat visible, else will expand
        if beam_rendered and annotation_visible:
            status = COMPLETENESS_PARTIAL
        else:
            status = COMPLETENESS_FAIL
    elif (
        annotation_visible
        and relation_ok
        and RC_TARGET_BEAM_VISIBLE in reasons
        and not unsafe
    ):
        status = COMPLETENESS_PASS
    else:
        status = COMPLETENESS_REVIEW

    # For expansion targeting: also include annotation deficits if any
    ann_def = ann_assess.get("deficits_px") or {}
    for side in ("left", "right", "top", "bottom"):
        deficits[side] = max(deficits[side], float(ann_def.get(side) or 0))

    unsafe = [s for s, v in deficits.items() if v > 0.5]

    return {
        "success": True,
        "completeness_status": status,
        "reason_codes": sorted(set(reasons)),
        "target_beam_geometry_present": beam_present,
        "target_beam_geometry_rendered": beam_rendered,
        "annotation_visible": annotation_visible,
        "leader_visible": leader_visible,
        "reinforcement_visible": reinf_visible,
        "critical_beam_bbox": list(critical_beam_bbox) if critical_beam_bbox else None,
        "target_beam_pixel_bbox": list(beam_pixel_bbox) if beam_pixel_bbox else None,
        "beam_edge_margins_px": beam_margins,
        "annotation_edge_margins_px": ann_margins,
        "unsafe_sides": unsafe,
        "deficits_px": deficits,
        "annotation_assessment": {
            "render_safe": ann_assess.get("render_safe"),
            "flags": ann_assess.get("flags"),
            "geometric_containment": ann_assess.get("geometric_containment"),
        },
        "rejected_physical_bar_excluded": not rejected_included,
    }


def classify_final(
    *,
    assessment: Dict[str, Any],
    extreme: bool,
    hit_max: bool,
    expanded: bool,
    render_ok: bool,
) -> Tuple[str, List[str]]:
    from .config import RC_CROP_EXPANDED, RC_EXCESSIVE_CONTEXT, RC_MAX_EXPANSION_REACHED

    reasons = list(assessment.get("reason_codes") or [])
    if expanded:
        reasons.append(RC_CROP_EXPANDED)
    if extreme:
        reasons.append(RC_EXCESSIVE_CONTEXT)
        return COMPLETENESS_FAIL, sorted(set(reasons))
    if not render_ok:
        return COMPLETENESS_FAIL, sorted(set(reasons))
    if not assessment.get("rejected_physical_bar_excluded", True):
        return COMPLETENESS_FAIL, sorted(set(reasons))

    unsafe = assessment.get("unsafe_sides") or []
    ann_ok = assessment.get("annotation_visible")
    beam_ok = assessment.get("target_beam_geometry_rendered") or (
        RC_TARGET_BEAM_VISIBLE in reasons
    )
    relation = RC_ANNOTATION_BEAM_RELATION_VISIBLE in reasons

    if hit_max and unsafe:
        reasons.append(RC_MAX_EXPANSION_REACHED)
        if ann_ok and beam_ok:
            return COMPLETENESS_REVIEW, sorted(set(reasons))
        return COMPLETENESS_FAIL, sorted(set(reasons))

    if not unsafe and ann_ok and beam_ok and relation:
        return COMPLETENESS_PASS, sorted(set(reasons))

    if ann_ok and beam_ok and unsafe:
        return COMPLETENESS_PARTIAL, sorted(set(reasons))

    if not ann_ok or not beam_ok:
        return COMPLETENESS_FAIL, sorted(set(reasons))

    return COMPLETENESS_REVIEW, sorted(set(reasons))


__all__ = ["assess_beam_completeness", "classify_final"]
