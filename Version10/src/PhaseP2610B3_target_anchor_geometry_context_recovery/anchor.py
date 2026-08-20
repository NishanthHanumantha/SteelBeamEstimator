"""Target-anchor truth from frozen geometry envelope + owned evidence. No beam-ID crop rules."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from PhaseP2610B_adaptive_beam_detail_crop.evidence import (
    collect_dimension_points,
    collect_text_evidence,
    next_row_y_cap,
    owned_by_mark,
    prev_row_y_floor,
    x_barriers,
)
from PhaseP2610B2_render_quality_directional_recovery.geometry import as_extent, height, union, width
from PhaseP2610B2_render_quality_directional_recovery.orientation import dominant_orientation
from PhaseT1_geometric_stirrup_evidence.geometry_envelope import build_geometry_envelope


def build_target_anchor(
    *,
    msp: Any,
    beam_id: str,
    mark: Dict[str, Any],
    titles: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    depth = float(mark.get("depth_mm") or 600.0)
    env = build_geometry_envelope(
        beam_id,
        msp,
        mark=mark,
        geometry={"depth_mm": depth},
        physical_bars=None,
    )
    core = as_extent(env.get("extent") or (
        float(mark["x"]) - 1800.0,
        float(mark["y"]) - 900.0,
        float(mark["x"]) + 1800.0,
        float(mark["y"]) + 900.0,
    ))
    y_cap = next_row_y_cap(mark, titles)
    y_floor = prev_row_y_floor(mark, titles)
    x_left, x_right = x_barriers(mark, titles)
    texts = collect_text_evidence(msp, mark, list(titles), y_cap=y_cap, x_left=x_left, x_right=x_right)
    dims = collect_dimension_points(msp, mark, list(titles), y_cap=y_cap, x_left=x_left, x_right=x_right)
    owned: List[Dict[str, Any]] = []
    for row in list(texts) + list(dims):
        try:
            x, y = float(row["x"]), float(row["y"])
        except (TypeError, ValueError, KeyError):
            continue
        if owned_by_mark(x, y, mark, titles):
            owned.append(row)
            core = union(core, (x, y, x, y))
    outline = None
    meta = env.get("meta") or {}
    if meta.get("outline_y_mm") and len(meta["outline_y_mm"]) >= 2:
        outline = meta["outline_y_mm"]
    orientation = dominant_orientation(mark=mark, extent=core, outline=outline, evidence=owned)
    return {
        "core": list(as_extent(core)),
        "orientation": orientation,
        "start": [core[0], core[1]],
        "end": [core[2], core[3]],
        "x_barriers": [x_left, x_right],
        "y_floor": y_floor,
        "y_cap": y_cap,
        "owned_evidence_count": len(owned),
        "owned_evidence": owned,
        "outline": outline,
        "envelope_signals": env.get("signals_used") or [],
        "geometry_confidence": env.get("geometry_confidence"),
        "mark": {"x": float(mark["x"]), "y": float(mark["y"]), "depth_mm": depth},
        "span_x": width(core),
        "span_y": height(core),
    }


def endpoints_inside(core: Sequence[float], crop: Sequence[float], *, tol: float) -> Tuple[bool, bool]:
    c = as_extent(core)
    e = as_extent(crop)
    start_ok = c[0] >= e[0] - tol and c[1] >= e[1] - tol
    end_ok = c[2] <= e[2] + tol and c[3] <= e[3] + tol
    return start_ok, end_ok


__all__ = ["build_target_anchor", "endpoints_inside"]
