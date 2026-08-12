"""Critical beam-evidence geometry helpers for P2.5.2.3."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from PhaseT182_adaptive_render_extent.adaptive_bbox import inflate_bbox, union_bbox
from PhaseP2521_crop_readability_refinement.geometry import local_beam_snippet
from PhaseP2522_render_safe_annotation_bounds.geometry_safe import (
    as_bbox,
    expand_extent_sides,
    geometric_contained,
    is_extreme,
    project_bbox_to_px,
    px_to_dxf_delta,
)

from .config import (
    CRITICAL_BEAM_HALF_SPAN_CONTEXT_MM,
    CRITICAL_BEAM_HALF_SPAN_MM,
    EXPAND_BUFFER_PX,
    GEOMETRY_PAD_MM,
    MAX_REFINED_HEIGHT_MM,
    MAX_REFINED_WIDTH_MM,
    MAX_SINGLE_SIDE_EXPANSION_MM,
    MAX_TOTAL_EXPANSION_MM,
    BBox,
)

MODEL_VERSION = "10.6.8"


def collect_critical_geometry(
    *,
    annotation_bbox: Optional[BBox],
    beam_bbox: Optional[BBox],
    leader_bboxes: Optional[Sequence[BBox]],
    owned_bboxes: Optional[Sequence[BBox]],
    reinforcement_bboxes: Optional[Sequence[BBox]],
    center_x: float,
    center_y: float,
    context: bool = False,
) -> Dict[str, Any]:
    """
    Build the minimum sufficient target-beam evidence region near the annotation.
    Does NOT require the entire beam span for long beams.
    """
    half = CRITICAL_BEAM_HALF_SPAN_CONTEXT_MM if context else CRITICAL_BEAM_HALF_SPAN_MM
    snippet = None
    if beam_bbox:
        snippet = local_beam_snippet(
            beam_bbox,
            center_x=center_x,
            center_y=center_y,
            half_span_x=half,
            half_span_y=half * 0.85,
        )
    parts: List[Optional[BBox]] = [
        annotation_bbox,
        snippet,
        *(leader_bboxes or []),
        *(owned_bboxes or []),
        *(reinforcement_bboxes or []),
    ]
    critical = union_bbox(parts)
    if critical:
        critical = inflate_bbox(critical, GEOMETRY_PAD_MM, GEOMETRY_PAD_MM)
    return {
        "critical_beam_bbox": critical,
        "local_beam_snippet": snippet,
        "beam_bbox": beam_bbox,
        "annotation_bbox": annotation_bbox,
        "leader_bboxes": list(leader_bboxes or []),
        "owned_bboxes": list(owned_bboxes or []),
        "reinforcement_bboxes": list(reinforcement_bboxes or []),
    }


def geometric_side_deficits(
    crop: BBox,
    inner: Optional[BBox],
    *,
    dxf_xlim: tuple,
    dxf_ylim: tuple,
    img_w: int,
    img_h: int,
    margin_px: int,
) -> Dict[str, float]:
    """
    If inner extends outside crop (or within margin_px of edge in DXF→px space),
    return pixel deficits per side to bring inner fully inside with margin.
    """
    deficits = {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0}
    if not inner:
        return deficits
    # Geometric protrusion in mm
    left_mm = max(0.0, crop[0] - inner[0])
    right_mm = max(0.0, inner[2] - crop[2])
    bottom_mm = max(0.0, crop[1] - inner[1])
    top_mm = max(0.0, inner[3] - crop[3])

    # Convert mm protrusion → px, then add required margin
    xspan = max(float(dxf_xlim[1]) - float(dxf_xlim[0]), 1e-9)
    yspan = max(float(dxf_ylim[1]) - float(dxf_ylim[0]), 1e-9)
    mm_per_px_x = xspan / max(img_w, 1)
    mm_per_px_y = yspan / max(img_h, 1)

    if left_mm > 0:
        deficits["left"] = left_mm / mm_per_px_x + float(margin_px)
    else:
        # Inside but check margin: distance from crop left to inner left in px
        dist_mm = inner[0] - crop[0]
        dist_px = dist_mm / mm_per_px_x
        if dist_px < margin_px:
            deficits["left"] = float(margin_px) - dist_px

    if right_mm > 0:
        deficits["right"] = right_mm / mm_per_px_x + float(margin_px)
    else:
        dist_mm = crop[2] - inner[2]
        dist_px = dist_mm / mm_per_px_x
        if dist_px < margin_px:
            deficits["right"] = float(margin_px) - dist_px

    if bottom_mm > 0:
        deficits["bottom"] = bottom_mm / mm_per_px_y + float(margin_px)
    else:
        dist_mm = inner[1] - crop[1]
        dist_px = dist_mm / mm_per_px_y
        if dist_px < margin_px:
            deficits["bottom"] = float(margin_px) - dist_px

    if top_mm > 0:
        deficits["top"] = top_mm / mm_per_px_y + float(margin_px)
    else:
        dist_mm = crop[3] - inner[3]
        dist_px = dist_mm / mm_per_px_y
        if dist_px < margin_px:
            deficits["top"] = float(margin_px) - dist_px

    return deficits


def expand_with_guardrails(
    extent: BBox,
    *,
    deficits_px: Dict[str, float],
    dxf_xlim: tuple,
    dxf_ylim: tuple,
    img_w: int,
    img_h: int,
    total_expand_so_far: Dict[str, float],
) -> tuple:
    """
    Side-specific expansion with per-side and total expansion caps.
    Returns (new_extent, expands_mm, capped).
    """
    # Cap requested px by remaining mm budget
    xspan = max(float(dxf_xlim[1]) - float(dxf_xlim[0]), 1e-9)
    yspan = max(float(dxf_ylim[1]) - float(dxf_ylim[0]), 1e-9)
    mm_per_px_x = xspan / max(img_w, 1)
    mm_per_px_y = yspan / max(img_h, 1)

    used = sum(total_expand_so_far.values())
    remaining_total = max(0.0, MAX_TOTAL_EXPANSION_MM - used)

    def _cap_side(need_px: float, axis: str, used_side: float) -> float:
        if need_px <= 0:
            return 0.0
        mm = need_px * (mm_per_px_x if axis == "x" else mm_per_px_y)
        # include buffer in px already outside; clamp
        room_side = max(0.0, MAX_SINGLE_SIDE_EXPANSION_MM - used_side)
        mm = min(mm, room_side, remaining_total)
        return mm / (mm_per_px_x if axis == "x" else mm_per_px_y)

    need_l = _cap_side(
        float(deficits_px.get("left") or 0) + (EXPAND_BUFFER_PX if deficits_px.get("left") else 0),
        "x",
        total_expand_so_far.get("left_mm", 0.0),
    )
    need_r = _cap_side(
        float(deficits_px.get("right") or 0) + (EXPAND_BUFFER_PX if deficits_px.get("right") else 0),
        "x",
        total_expand_so_far.get("right_mm", 0.0),
    )
    need_t = _cap_side(
        float(deficits_px.get("top") or 0) + (EXPAND_BUFFER_PX if deficits_px.get("top") else 0),
        "y",
        total_expand_so_far.get("top_mm", 0.0),
    )
    need_b = _cap_side(
        float(deficits_px.get("bottom") or 0) + (EXPAND_BUFFER_PX if deficits_px.get("bottom") else 0),
        "y",
        total_expand_so_far.get("bottom_mm", 0.0),
    )

    capped = False
    raw_need = sum(
        float(deficits_px.get(k) or 0) for k in ("left", "right", "top", "bottom")
    )
    if raw_need > 0 and (need_l + need_r + need_t + need_b) <= 1e-6:
        capped = True

    new_ext, expands = expand_extent_sides(
        extent,
        need_left_px=need_l,
        need_right_px=need_r,
        need_top_px=need_t,
        need_bottom_px=need_b,
        dxf_xlim=dxf_xlim,
        dxf_ylim=dxf_ylim,
        img_w=img_w,
        img_h=img_h,
    )
    # Hard-clamp expand_extent's internal MAX_SIDE if it exceeded our totals
    # Re-apply refined size caps already in expand_extent_sides
    w = new_ext[2] - new_ext[0]
    h = new_ext[3] - new_ext[1]
    if w > MAX_REFINED_WIDTH_MM or h > MAX_REFINED_HEIGHT_MM:
        capped = True
    return new_ext, expands, capped


__all__ = [
    "as_bbox",
    "collect_critical_geometry",
    "expand_with_guardrails",
    "geometric_contained",
    "geometric_side_deficits",
    "is_extreme",
    "project_bbox_to_px",
    "px_to_dxf_delta",
]
