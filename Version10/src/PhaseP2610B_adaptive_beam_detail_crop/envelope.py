"""Adaptive detail envelope from title + outline + spatial evidence. No R.1."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PhaseP2610A_beam_region_crop_audit.region_builder import build_target_regions
from PhaseT1_geometric_stirrup_evidence.geometry_envelope import _outline_bracket

from .config import (
    EVIDENCE_PAD_MM,
    LOCALIZATION_METHOD,
    LOCALIZATION_SOURCE,
    MAX_DETAIL_HEIGHT_MM,
    MAX_DETAIL_WIDTH_MM,
    MIN_STACK_ABOVE_MM,
)
from .evidence import (
    KIND_DIM,
    KIND_REINF,
    KIND_STIRRUP,
    band_for_point,
    collect_dimension_points,
    collect_text_evidence,
    next_row_y_cap,
    prev_row_y_floor,
    x_barriers,
)


def adaptive_detail_extent(
    *,
    msp: Any,
    beam_id: str,
    mark: Dict[str, Any],
    titles: Optional[list] = None,
) -> Dict[str, Any]:
    titles = list(titles or [])
    mx, my = float(mark["x"]), float(mark["y"])
    depth = float(mark.get("depth_mm") or 600.0)
    outline = _outline_bracket(msp, mx, my, 2500.0, depth)
    y_cap = next_row_y_cap(mark, titles)
    y_floor = prev_row_y_floor(mark, titles)
    x_left, x_right = x_barriers(mark, titles)
    texts = collect_text_evidence(msp, mark, titles, y_cap=y_cap, x_left=x_left, x_right=x_right)
    dims = collect_dimension_points(msp, mark, titles, y_cap=y_cap, x_left=x_left, x_right=x_right)
    evidence = texts + dims
    for row in evidence:
        row["band"] = band_for_point(float(row["y"]), mark, outline, str(row.get("kind")))

    ymin = y_floor
    ymax = min(my + max(MIN_STACK_ABOVE_MM, 2.8 * depth + 800.0), y_cap)
    xmin = mx - max(1800.0, 0.55 * (x_right - x_left))
    xmax = mx + max(1800.0, 0.55 * (x_right - x_left))
    if outline:
        ymin = min(ymin, float(outline[0]) - 180.0)
        ymax = max(ymax, min(float(outline[1]) + 420.0, y_cap))
    xs: List[float] = [mx]
    ys: List[float] = [my]
    for row in evidence:
        xs.append(float(row["x"]))
        ys.append(float(row["y"]))
    if xs:
        xmin = min(xmin, min(xs) - EVIDENCE_PAD_MM)
        xmax = max(xmax, max(xs) + EVIDENCE_PAD_MM)
    if ys:
        ymin = min(ymin, min(ys) - EVIDENCE_PAD_MM)
        ymax = max(ymax, max(ys) + EVIDENCE_PAD_MM)

    xmin = max(xmin, x_left)
    xmax = min(xmax, x_right)
    ymax = min(ymax, y_cap)
    ymin = max(ymin, y_floor)

    if xmax - xmin > MAX_DETAIL_WIDTH_MM:
        extra = (xmax - xmin - MAX_DETAIL_WIDTH_MM) / 2.0
        xmin += extra
        xmax -= extra
    if ymax - ymin > MAX_DETAIL_HEIGHT_MM:
        ymax = ymin + MAX_DETAIL_HEIGHT_MM
        if ymax < my + 800.0:
            ymax = my + MAX_DETAIL_HEIGHT_MM * 0.7
            ymin = ymax - MAX_DETAIL_HEIGHT_MM

    if xmax <= xmin + 400.0:
        xmin, xmax = mx - 1800.0, mx + 1800.0
    if ymax <= ymin + 400.0:
        ymin, ymax = my - 500.0, my + 2800.0

    return {
        "detail_extent": (float(xmin), float(ymin), float(xmax), float(ymax)),
        "outline": list(outline) if outline else None,
        "y_cap": y_cap,
        "x_barriers": [x_left, x_right],
        "evidence": evidence,
        "evidence_counts": {
            "stirrup": sum(1 for r in evidence if r.get("kind") == KIND_STIRRUP),
            "reinf": sum(1 for r in evidence if r.get("kind") == KIND_REINF),
            "dim": sum(1 for r in evidence if r.get("kind") == KIND_DIM),
        },
        "localization_method": LOCALIZATION_METHOD,
        "localization_source": LOCALIZATION_SOURCE,
        "annotation_association_dependency": False,
        "outline_found": outline is not None,
    }


def build_adaptive_regions(
    *,
    msp: Any,
    beam_id: str,
    mark: Dict[str, Any],
    titles: Optional[list] = None,
) -> Dict[str, Any]:
    base = build_target_regions(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
    adapted = adaptive_detail_extent(msp=msp, beam_id=beam_id, mark=mark, titles=titles)
    out = dict(base)
    out["p2610a_detail_extent"] = base.get("detail_extent")
    out["detail_extent"] = adapted["detail_extent"]
    out["adaptive"] = adapted
    out["localization_method"] = LOCALIZATION_METHOD
    out["localization_source"] = LOCALIZATION_SOURCE
    out["annotation_association_dependency"] = False
    return out


__all__ = ["adaptive_detail_extent", "build_adaptive_regions"]
