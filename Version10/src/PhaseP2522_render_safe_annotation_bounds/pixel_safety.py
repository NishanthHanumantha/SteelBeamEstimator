"""Pixel-level render-safety checks for critical annotation/leader evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .config import (
    BG_LUMA_THRESHOLD,
    FLAG_ANNOTATION_RENDER_CLIPPED,
    FLAG_ANNOTATION_RENDER_EDGE_RISK,
    FLAG_BOTTOM_ANNOTATION_EDGE_RISK,
    FLAG_LEADER_RENDER_EDGE_RISK,
    FLAG_TOP_ANNOTATION_EDGE_RISK,
    GLYPH_OVERRUN_PAD_MM,
    GLYPH_OVERRUN_PAD_PX,
    MIN_RENDER_SAFE_MARGIN_PX,
    BBox,
)
from .geometry_safe import (
    annotation_vertical_side,
    as_bbox,
    deficit_px,
    geometric_contained,
    inflate_bbox_mm,
    project_bbox_to_px,
)

MODEL_VERSION = "10.6.7"


def _load_rgb(path: Path):
    from PIL import Image
    import numpy as np

    with Image.open(path) as im:
        arr = np.asarray(im.convert("RGB"))
    return arr


def _ink_bbox_in_region(
    rgb,
    *,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    luma_threshold: int = BG_LUMA_THRESHOLD,
) -> Optional[Tuple[int, int, int, int]]:
    """Return pixel bbox of non-background ink inside region, or None."""
    import numpy as np

    h, w = rgb.shape[0], rgb.shape[1]
    x0 = max(0, min(w, x0))
    x1 = max(0, min(w, x1))
    y0 = max(0, min(h, y0))
    y1 = max(0, min(h, y1))
    if x1 <= x0 or y1 <= y0:
        return None
    region = rgb[y0:y1, x0:x1]
    # Luma approx
    luma = (
        0.299 * region[:, :, 0].astype("float32")
        + 0.587 * region[:, :, 1].astype("float32")
        + 0.114 * region[:, :, 2].astype("float32")
    )
    mask = luma < float(luma_threshold)
    if not bool(mask.any()):
        return None
    ys, xs = np.where(mask)
    return (
        int(xs.min()) + x0,
        int(ys.min()) + y0,
        int(xs.max()) + 1 + x0,
        int(ys.max()) + 1 + y0,
    )


def _margins(pixel_bbox: Tuple[int, int, int, int], img_w: int, img_h: int) -> Dict[str, float]:
    x0, y0, x1, y1 = pixel_bbox
    return {
        "left_margin_px": float(x0),
        "right_margin_px": float(img_w - x1),
        "top_margin_px": float(y0),
        "bottom_margin_px": float(img_h - y1),
    }


def _union_pixel_boxes(
    boxes: Sequence[Optional[Tuple[int, int, int, int]]],
) -> Optional[Tuple[int, int, int, int]]:
    valid = [b for b in boxes if b]
    if not valid:
        return None
    return (
        min(b[0] for b in valid),
        min(b[1] for b in valid),
        max(b[2] for b in valid),
        max(b[3] for b in valid),
    )


def assess_render_safety(
    *,
    image_path: Path,
    extent: BBox,
    annotation_bbox: Optional[BBox],
    leader_bboxes: Optional[Sequence[BBox]] = None,
    beam_bbox: Optional[BBox] = None,
    dxf_xlim: Optional[Sequence[float]] = None,
    dxf_ylim: Optional[Sequence[float]] = None,
    img_w: Optional[int] = None,
    img_h: Optional[int] = None,
    min_margin_px: int = MIN_RENDER_SAFE_MARGIN_PX,
) -> Dict[str, Any]:
    """
    Pixel-level safety for critical annotation (+ leaders).
    Uses projected DXF search region; final verdict from rendered ink pixels.
    """
    path = Path(image_path)
    flags: List[str] = []
    vertical_side = annotation_vertical_side(
        annotation_bbox=annotation_bbox, beam_bbox=beam_bbox
    )

    geom_ok = geometric_contained(extent, annotation_bbox)
    if not geom_ok:
        flags.append("ANNOTATION_GEOMETRIC_OUTSIDE")

    if not path.exists():
        return {
            "success": False,
            "error": "missing_image",
            "geometric_containment": geom_ok,
            "render_safe": False,
            "flags": flags + ["MISSING_IMAGE"],
            "vertical_side": vertical_side,
            "margins_px": None,
            "annotation_pixel_bbox": None,
            "leader_pixel_bbox": None,
            "deficits_px": {
                "left": float(min_margin_px),
                "right": float(min_margin_px),
                "top": float(min_margin_px),
                "bottom": float(min_margin_px),
            },
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

    # Search region: mathematical ann bbox + glyph overrun pad
    search_boxes_px: List[Tuple[int, int, int, int]] = []
    ann_px_math = None
    if annotation_bbox:
        inflated = inflate_bbox_mm(annotation_bbox, GLYPH_OVERRUN_PAD_MM)
        ann_px_math = project_bbox_to_px(
            inflated,
            dxf_xlim=dxf_xlim,
            dxf_ylim=dxf_ylim,
            img_w=img_w,
            img_h=img_h,
        )
        # Extra pixel pad for glyph overshoot beyond DXF bbox
        x0, y0, x1, y1 = ann_px_math
        search_boxes_px.append(
            (
                max(0, x0 - GLYPH_OVERRUN_PAD_PX),
                max(0, y0 - GLYPH_OVERRUN_PAD_PX),
                min(img_w, x1 + GLYPH_OVERRUN_PAD_PX),
                min(img_h, y1 + GLYPH_OVERRUN_PAD_PX),
            )
        )

    leader_px_boxes: List[Tuple[int, int, int, int]] = []
    for lb in leader_bboxes or []:
        inflated_l = inflate_bbox_mm(lb, 40.0)
        pbox = project_bbox_to_px(
            inflated_l,
            dxf_xlim=dxf_xlim,
            dxf_ylim=dxf_ylim,
            img_w=img_w,
            img_h=img_h,
        )
        leader_px_boxes.append(pbox)
        x0, y0, x1, y1 = pbox
        search_boxes_px.append(
            (
                max(0, x0 - 8),
                max(0, y0 - 8),
                min(img_w, x1 + 8),
                min(img_h, y1 + 8),
            )
        )

    # Ink within annotation search region
    ann_ink = None
    if annotation_bbox and search_boxes_px:
        # Use first (annotation) search box primarily
        sx0, sy0, sx1, sy1 = search_boxes_px[0]
        ann_ink = _ink_bbox_in_region(rgb, x0=sx0, y0=sy0, x1=sx1, y1=sy1)
        if ann_ink is None and ann_px_math is not None:
            # Fallback to projected mathematical bbox
            ann_ink = ann_px_math
            flags.append("ANNOTATION_INK_FALLBACK_MATH_BBOX")

    leader_ink = None
    if leader_px_boxes:
        leader_inks = []
        for pbox in leader_px_boxes:
            ink = _ink_bbox_in_region(rgb, x0=pbox[0], y0=pbox[1], x1=pbox[2], y1=pbox[3])
            leader_inks.append(ink or pbox)
        leader_ink = _union_pixel_boxes(leader_inks)

    critical = _union_pixel_boxes([ann_ink, leader_ink])
    if critical is None:
        flags.append("CRITICAL_PIXELS_NOT_FOUND")
        return {
            "success": True,
            "geometric_containment": geom_ok,
            "render_safe": False,
            "flags": flags,
            "vertical_side": vertical_side,
            "margins_px": None,
            "annotation_pixel_bbox": ann_ink,
            "leader_pixel_bbox": leader_ink,
            "img_w": img_w,
            "img_h": img_h,
            "deficits_px": {
                "left": float(min_margin_px),
                "right": float(min_margin_px),
                "top": float(min_margin_px),
                "bottom": float(min_margin_px),
            },
        }

    margins = _margins(critical, img_w, img_h)
    # Also compute annotation-only margins for diagnostics
    ann_margins = _margins(ann_ink, img_w, img_h) if ann_ink else None
    leader_margins = _margins(leader_ink, img_w, img_h) if leader_ink else None

    clipped = (
        margins["left_margin_px"] <= 0
        or margins["right_margin_px"] <= 0
        or margins["top_margin_px"] <= 0
        or margins["bottom_margin_px"] <= 0
    )
    if clipped:
        flags.append(FLAG_ANNOTATION_RENDER_CLIPPED)

    edge_risk = False
    for side, key in (
        ("left", "left_margin_px"),
        ("right", "right_margin_px"),
        ("top", "top_margin_px"),
        ("bottom", "bottom_margin_px"),
    ):
        if margins[key] < float(min_margin_px):
            edge_risk = True
            flags.append(FLAG_ANNOTATION_RENDER_EDGE_RISK)
            break

    if leader_margins:
        for key in leader_margins:
            if leader_margins[key] < float(min_margin_px):
                flags.append(FLAG_LEADER_RENDER_EDGE_RISK)
                break

    if vertical_side == "TOP" and margins["top_margin_px"] < float(min_margin_px):
        flags.append(FLAG_TOP_ANNOTATION_EDGE_RISK)
    if vertical_side == "BOTTOM" and margins["bottom_margin_px"] < float(min_margin_px):
        flags.append(FLAG_BOTTOM_ANNOTATION_EDGE_RISK)

    # Prefer annotation-only margins for expansion targets when available
    expand_src = ann_margins or margins
    deficits = {
        "left": deficit_px(expand_src["left_margin_px"], min_margin_px),
        "right": deficit_px(expand_src["right_margin_px"], min_margin_px),
        "top": deficit_px(expand_src["top_margin_px"], min_margin_px),
        "bottom": deficit_px(expand_src["bottom_margin_px"], min_margin_px),
    }
    # Also ensure leader deficits are covered
    if leader_margins:
        deficits["left"] = max(
            deficits["left"], deficit_px(leader_margins["left_margin_px"], min_margin_px)
        )
        deficits["right"] = max(
            deficits["right"], deficit_px(leader_margins["right_margin_px"], min_margin_px)
        )
        deficits["top"] = max(
            deficits["top"], deficit_px(leader_margins["top_margin_px"], min_margin_px)
        )
        deficits["bottom"] = max(
            deficits["bottom"], deficit_px(leader_margins["bottom_margin_px"], min_margin_px)
        )

    render_safe = (
        geom_ok
        and not clipped
        and not edge_risk
        and FLAG_LEADER_RENDER_EDGE_RISK not in flags
        and "CRITICAL_PIXELS_NOT_FOUND" not in flags
    )

    return {
        "success": True,
        "geometric_containment": geom_ok,
        "render_safe": render_safe,
        "flags": sorted(set(flags)),
        "vertical_side": vertical_side,
        "margins_px": margins,
        "annotation_margins_px": ann_margins,
        "leader_margins_px": leader_margins,
        "annotation_pixel_bbox": list(ann_ink) if ann_ink else None,
        "leader_pixel_bbox": list(leader_ink) if leader_ink else None,
        "critical_pixel_bbox": list(critical),
        "img_w": img_w,
        "img_h": img_h,
        "deficits_px": deficits,
        "min_margin_px": min_margin_px,
    }


__all__ = ["assess_render_safety"]
