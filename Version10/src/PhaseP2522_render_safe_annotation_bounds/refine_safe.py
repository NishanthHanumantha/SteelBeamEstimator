"""Render-safe crop refinement loop (side-specific expansion)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PhaseP250_beam_evidence_crop_qa.renderer import render_engineering_crop

from .config import (
    MAX_RENDER_SAFETY_ITERATIONS,
    MIN_RENDER_SAFE_MARGIN_PX,
    READABILITY_FAIL,
    READABILITY_PASS,
    READABILITY_PARTIAL,
    READABILITY_REVIEW,
    BBox,
)
from .geometry_safe import (
    as_bbox,
    expand_extent_sides,
    geometric_contained,
    is_extreme,
)
from .pixel_safety import assess_render_safety

MODEL_VERSION = "10.6.7"


def _classify(
    *,
    assessment: Dict[str, Any],
    extreme: bool,
    render_ok: bool,
    rejected_included: bool,
    missing_beam: bool,
    missing_ann: bool,
) -> str:
    if rejected_included or missing_beam or missing_ann or not render_ok:
        return READABILITY_FAIL
    if extreme:
        return READABILITY_REVIEW
    if assessment.get("render_safe") and assessment.get("geometric_containment"):
        return READABILITY_PASS
    flags = assessment.get("flags") or []
    if "ANNOTATION_RENDER_CLIPPED" in flags:
        return READABILITY_REVIEW
    if assessment.get("geometric_containment") and not assessment.get("render_safe"):
        # Usable but not margin-safe after max iters handled by caller
        return READABILITY_PARTIAL
    return READABILITY_FAIL


def refine_render_safe_crop(
    *,
    initial_extent: BBox,
    out_path: Path,
    engine_root: Path,
    dxf_path: Path,
    annotation_bbox: Optional[BBox],
    leader_bboxes: Optional[Sequence[BBox]],
    beam_bbox: Optional[BBox],
    owned_geometry: Optional[List[Dict[str, Any]]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    rejected_included: bool = False,
    max_iters: int = MAX_RENDER_SAFETY_ITERATIONS,
    min_margin_px: int = MIN_RENDER_SAFE_MARGIN_PX,
) -> Dict[str, Any]:
    """
    Render → pixel-check → side-expand → re-render loop.
    Returns final crop metadata + iteration history.
    """
    extent = (
        float(initial_extent[0]),
        float(initial_extent[1]),
        float(initial_extent[2]),
        float(initial_extent[3]),
    )
    history: List[Dict[str, Any]] = []
    final_render: Dict[str, Any] = {}
    final_assess: Dict[str, Any] = {}
    refined = False
    hit_max = False
    total_expand = {"left_mm": 0.0, "right_mm": 0.0, "top_mm": 0.0, "bottom_mm": 0.0}

    missing_ann = annotation_bbox is None
    missing_beam = beam_bbox is None

    for i in range(1, max_iters + 1):
        if is_extreme(extent):
            final_assess = {
                "success": True,
                "geometric_containment": geometric_contained(extent, annotation_bbox),
                "render_safe": False,
                "flags": ["EXTREME_CROP"],
                "margins_px": None,
                "deficits_px": {"left": 0, "right": 0, "top": 0, "bottom": 0},
            }
            history.append(
                {
                    "iteration": i,
                    "extent": list(extent),
                    "extreme": True,
                    "assessment": final_assess,
                }
            )
            hit_max = True
            break

        render = render_engineering_crop(
            engine_root=Path(engine_root),
            dxf_path=Path(dxf_path),
            extent=extent,
            out_path=Path(out_path),
            owned_geometry=owned_geometry,
            evidence=evidence,
        )
        final_render = render
        if not render.get("success"):
            final_assess = {
                "success": False,
                "geometric_containment": geometric_contained(extent, annotation_bbox),
                "render_safe": False,
                "flags": ["RENDER_FAILED"],
                "error": render.get("error"),
                "deficits_px": {"left": min_margin_px, "right": min_margin_px, "top": min_margin_px, "bottom": min_margin_px},
            }
            history.append({"iteration": i, "extent": list(extent), "render": render, "assessment": final_assess})
            break

        xlim = render.get("dxf_xlim") or (extent[0], extent[2])
        ylim = render.get("dxf_ylim") or (extent[1], extent[3])
        assess = assess_render_safety(
            image_path=Path(out_path),
            extent=extent,
            annotation_bbox=annotation_bbox,
            leader_bboxes=list(leader_bboxes or []),
            beam_bbox=beam_bbox,
            dxf_xlim=xlim,
            dxf_ylim=ylim,
            img_w=render.get("img_w"),
            img_h=render.get("img_h"),
            min_margin_px=min_margin_px,
        )
        final_assess = assess
        history.append(
            {
                "iteration": i,
                "extent": list(extent),
                "assessment_flags": assess.get("flags"),
                "margins_px": assess.get("margins_px"),
                "deficits_px": assess.get("deficits_px"),
                "render_safe": assess.get("render_safe"),
            }
        )

        if assess.get("render_safe") and assess.get("geometric_containment"):
            break

        deficits = assess.get("deficits_px") or {}
        need_l = float(deficits.get("left") or 0)
        need_r = float(deficits.get("right") or 0)
        need_t = float(deficits.get("top") or 0)
        need_b = float(deficits.get("bottom") or 0)
        if need_l <= 0 and need_r <= 0 and need_t <= 0 and need_b <= 0:
            # Unsafe for other reasons (e.g. missing ink) — stop
            if i >= max_iters:
                hit_max = True
            break

        if i >= max_iters:
            hit_max = True
            break

        new_extent, expands = expand_extent_sides(
            extent,
            need_left_px=need_l,
            need_right_px=need_r,
            need_top_px=need_t,
            need_bottom_px=need_b,
            dxf_xlim=(float(xlim[0]), float(xlim[1])),
            dxf_ylim=(float(ylim[0]), float(ylim[1])),
            img_w=int(render.get("img_w") or 1),
            img_h=int(render.get("img_h") or 1),
        )
        if new_extent == extent:
            hit_max = True
            break
        total_expand["left_mm"] += expands["expand_left_mm"]
        total_expand["right_mm"] += expands["expand_right_mm"]
        total_expand["top_mm"] += expands["expand_top_mm"]
        total_expand["bottom_mm"] += expands["expand_bottom_mm"]
        extent = new_extent
        refined = True
        history[-1]["expansion_mm"] = expands

    extreme = is_extreme(extent)
    status = _classify(
        assessment=final_assess,
        extreme=extreme,
        render_ok=bool(final_render.get("success")),
        rejected_included=rejected_included,
        missing_beam=missing_beam,
        missing_ann=missing_ann,
    )
    if hit_max and status == READABILITY_PARTIAL:
        status = READABILITY_REVIEW
    if hit_max and not final_assess.get("render_safe"):
        status = READABILITY_REVIEW

    return {
        "success": bool(final_render.get("success")),
        "crop_bbox": list(extent),
        "initial_crop_bbox": list(initial_extent),
        "iterations_used": len(history),
        "hit_max_iterations": hit_max,
        "render_safety_refined": refined,
        "total_expansion_mm": total_expand,
        "max_side_expansion_mm": max(total_expand.values()) if total_expand else 0.0,
        "assessment": final_assess,
        "render": {
            "success": final_render.get("success"),
            "path": final_render.get("path") or str(out_path),
            "img_w": final_render.get("img_w"),
            "img_h": final_render.get("img_h"),
            "dxf_xlim": final_render.get("dxf_xlim"),
            "dxf_ylim": final_render.get("dxf_ylim"),
            "error": final_render.get("error"),
        },
        "readability_status": status,
        "is_extreme": extreme,
        "history": history,
        "geometric_containment": bool(final_assess.get("geometric_containment")),
        "render_safe": bool(final_assess.get("render_safe")),
    }


__all__ = ["refine_render_safe_crop"]
