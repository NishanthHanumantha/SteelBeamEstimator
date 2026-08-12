"""Target-beam completeness refinement loop."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PhaseP250_beam_evidence_crop_qa.renderer import render_engineering_crop

from .completeness import assess_beam_completeness, classify_final
from .config import MAX_RENDER_COMPLETENESS_ITERS, BBox
from .geometry_complete import expand_with_guardrails, is_extreme

MODEL_VERSION = "10.6.8"


def refine_target_beam_complete(
    *,
    initial_extent: BBox,
    out_path: Path,
    engine_root: Path,
    dxf_path: Path,
    critical_beam_bbox: Optional[BBox],
    annotation_bbox: Optional[BBox],
    leader_bboxes: Optional[Sequence[BBox]],
    owned_bboxes: Optional[Sequence[BBox]],
    reinforcement_bboxes: Optional[Sequence[BBox]],
    beam_bbox: Optional[BBox],
    owned_geometry: Optional[List[Dict[str, Any]]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    rejected_included: bool = False,
    max_iters: int = MAX_RENDER_COMPLETENESS_ITERS,
) -> Dict[str, Any]:
    extent = tuple(float(x) for x in initial_extent)  # type: ignore[assignment]
    extent = (extent[0], extent[1], extent[2], extent[3])
    history: List[Dict[str, Any]] = []
    final_render: Dict[str, Any] = {}
    final_assess: Dict[str, Any] = {}
    total_expand = {"left_mm": 0.0, "right_mm": 0.0, "top_mm": 0.0, "bottom_mm": 0.0}
    expanded = False
    hit_max = False
    capped = False

    for i in range(1, max_iters + 1):
        if is_extreme(extent):
            final_assess = {
                "success": True,
                "completeness_status": "FAIL",
                "reason_codes": ["EXCESSIVE_CONTEXT"],
                "unsafe_sides": [],
                "deficits_px": {"left": 0, "right": 0, "top": 0, "bottom": 0},
                "rejected_physical_bar_excluded": not rejected_included,
            }
            history.append({"iteration": i, "extent": list(extent), "extreme": True})
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
                "completeness_status": "FAIL",
                "reason_codes": ["RENDER_FAILED"],
                "unsafe_sides": [],
                "deficits_px": {"left": 0, "right": 0, "top": 0, "bottom": 0},
                "rejected_physical_bar_excluded": not rejected_included,
            }
            history.append({"iteration": i, "extent": list(extent), "render_error": render.get("error")})
            break

        xlim = render.get("dxf_xlim") or (extent[0], extent[2])
        ylim = render.get("dxf_ylim") or (extent[1], extent[3])
        assess = assess_beam_completeness(
            image_path=Path(out_path),
            extent=extent,
            critical_beam_bbox=critical_beam_bbox,
            annotation_bbox=annotation_bbox,
            leader_bboxes=list(leader_bboxes or []),
            owned_bboxes=list(owned_bboxes or []),
            reinforcement_bboxes=list(reinforcement_bboxes or []),
            beam_bbox=beam_bbox,
            dxf_xlim=xlim,
            dxf_ylim=ylim,
            img_w=render.get("img_w"),
            img_h=render.get("img_h"),
            rejected_included=rejected_included,
        )
        final_assess = assess
        history.append(
            {
                "iteration": i,
                "extent": list(extent),
                "unsafe_sides": assess.get("unsafe_sides"),
                "deficits_px": assess.get("deficits_px"),
                "status": assess.get("completeness_status"),
                "beam_margins": assess.get("beam_edge_margins_px"),
            }
        )

        unsafe = assess.get("unsafe_sides") or []
        if not unsafe and assess.get("completeness_status") in ("PASS", "PARTIAL"):
            # Prefer PASS; if PARTIAL with no unsafe sides, accept
            if assess.get("completeness_status") == "PASS" or not unsafe:
                if assess.get("completeness_status") == "PASS":
                    break
                if not unsafe:
                    break

        if not unsafe:
            break

        if i >= max_iters:
            hit_max = True
            break

        new_ext, expands, was_capped = expand_with_guardrails(
            extent,
            deficits_px=assess.get("deficits_px") or {},
            dxf_xlim=(float(xlim[0]), float(xlim[1])),
            dxf_ylim=(float(ylim[0]), float(ylim[1])),
            img_w=int(render.get("img_w") or 1),
            img_h=int(render.get("img_h") or 1),
            total_expand_so_far=total_expand,
        )
        capped = capped or was_capped
        if new_ext == extent or sum(expands.values()) <= 1e-9:
            hit_max = True
            capped = True
            break
        total_expand["left_mm"] += expands["expand_left_mm"]
        total_expand["right_mm"] += expands["expand_right_mm"]
        total_expand["top_mm"] += expands["expand_top_mm"]
        total_expand["bottom_mm"] += expands["expand_bottom_mm"]
        extent = new_ext
        expanded = True
        history[-1]["expansion_mm"] = expands

    status, reasons = classify_final(
        assessment=final_assess,
        extreme=is_extreme(extent),
        hit_max=hit_max or capped,
        expanded=expanded,
        render_ok=bool(final_render.get("success")),
    )
    final_assess = dict(final_assess)
    final_assess["completeness_status"] = status
    final_assess["reason_codes"] = reasons

    return {
        "success": bool(final_render.get("success")),
        "crop_bbox": list(extent),
        "initial_crop_bbox": list(initial_extent),
        "iterations_used": len(history),
        "hit_max_iterations": hit_max or capped,
        "completeness_refined": expanded,
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
        "completeness_status": status,
        "is_extreme": is_extreme(extent),
        "history": history,
    }


__all__ = ["refine_target_beam_complete"]
