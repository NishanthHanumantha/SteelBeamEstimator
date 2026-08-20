"""Bounded context candidates. At most three. No combinatorial search. No beam-ID rules."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from PhaseP2610B2_render_quality_directional_recovery.geometry import as_extent, clamp_to_limits, height, union, width
from PhaseP2610B2_render_quality_directional_recovery.orientation import HORIZONTAL, VERTICAL
from PhaseP2610B2_render_quality_directional_recovery.quality import STATUS_BLACK, STATUS_EMPTY, STATUS_LOW_INFO, STATUS_MISSING

from .config import DIRECTION_EXTRA_FRAC, DIRECTION_EXTRA_MAX_MM, EXTENT_DUP_MM, MAX_CANDIDATES, OCCUPANCY_PAD_MM

_BLANK = {STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING}


def _key(extent: Sequence[float]) -> tuple:
    e = as_extent(extent)
    return tuple(round(v / EXTENT_DUP_MM) * EXTENT_DUP_MM for v in e)


def _clamp(extent: Sequence[float], anchor: Dict[str, Any]) -> tuple:
    core = as_extent(anchor["core"])
    barriers = list(anchor.get("x_barriers") or [-1e12, 1e12])
    mark = anchor.get("mark") or {"x": 0.5 * (core[0] + core[2]), "y": 0.5 * (core[1] + core[3])}
    return clamp_to_limits(
        extent,
        x_left=float(barriers[0]),
        x_right=float(barriers[1]),
        y_floor=float(anchor.get("y_floor") or core[1] - 4000.0),
        y_cap=float(anchor.get("y_cap") or core[3] + 4000.0),
        max_w=16000.0,
        max_h=11000.0,
        min_w=900.0,
        min_h=700.0,
        anchor=(float(mark["x"]), float(mark["y"])),
    )


def generate_candidates(
    *,
    anchor: Dict[str, Any],
    context_envelope: Dict[str, Any],
    baseline_extent: Optional[Sequence[float]],
    baseline_quality: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    core = as_extent(anchor["core"])
    orient = str(anchor.get("orientation") or "")
    geo = as_extent(context_envelope["extent"])
    out: List[Dict[str, Any]] = []
    seen = set()

    def _add(reason: str, extent: Sequence[float]) -> None:
        ext = _clamp(extent, anchor)
        k = _key(ext)
        if k in seen:
            return
        seen.add(k)
        out.append({"reason": reason, "extent": list(ext)})

    _add("GEOMETRY_BOUNDED_BASELINE", geo)

    extra = min(DIRECTION_EXTRA_MAX_MM, max(width(core), height(core)) * DIRECTION_EXTRA_FRAC)
    if orient == VERTICAL:
        _add(
            "VERTICAL_CONTEXT_UNDERSCALE",
            (geo[0], geo[1] - extra, geo[2], geo[3] + extra),
        )
    else:
        _add(
            "HORIZONTAL_CONTEXT_UNDERSCALE",
            (geo[0] - extra, geo[1], geo[2] + extra, geo[3]),
        )

    q = baseline_quality or {}
    crushed = str(q.get("primary_status") or "") in _BLANK or bool(q.get("empty_sides"))
    content = q.get("content_bbox_dxf")
    if crushed or (float(q.get("coverage_x") or 1.0) < 0.45):
        occ = core
        if content and len(content) == 4:
            occ = union(core, content)
        _add(
            "UNUSED_CANVAS_CRUSH",
            (
                occ[0] - OCCUPANCY_PAD_MM,
                occ[1] - OCCUPANCY_PAD_MM,
                occ[2] + OCCUPANCY_PAD_MM,
                occ[3] + OCCUPANCY_PAD_MM,
            ),
        )

    if baseline_extent is not None:
        b = as_extent(baseline_extent)
        if _key(b) not in seen and len(out) < MAX_CANDIDATES:
            pass
    return out[:MAX_CANDIDATES]


__all__ = ["generate_candidates"]
