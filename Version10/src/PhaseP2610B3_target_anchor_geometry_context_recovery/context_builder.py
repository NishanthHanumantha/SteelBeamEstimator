"""Geometry-bounded context envelope. Direction-aware. No beam-ID crop rules."""
from __future__ import annotations

from typing import Any, Dict, Sequence

from PhaseP2610B2_render_quality_directional_recovery.geometry import as_extent, clamp_to_limits, height, width
from PhaseP2610B2_render_quality_directional_recovery.orientation import COMPACT, HORIZONTAL, VERTICAL

from .config import (
    CONTEXT_PAD_FRAC_MAJOR,
    CONTEXT_PAD_FRAC_MINOR,
    CONTEXT_PAD_MAJOR_MAX_MM,
    CONTEXT_PAD_MAJOR_MIN_MM,
    CONTEXT_PAD_MINOR_MAX_MM,
    CONTEXT_PAD_MINOR_MIN_MM,
)


def _pad(v: float, frac: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v * frac))


def build_context_envelope(anchor: Dict[str, Any]) -> Dict[str, Any]:
    core = as_extent(anchor["core"])
    orient = str(anchor.get("orientation") or COMPACT)
    w, h = width(core), height(core)
    if orient == VERTICAL:
        pad_y = _pad(h, CONTEXT_PAD_FRAC_MAJOR, CONTEXT_PAD_MAJOR_MIN_MM, CONTEXT_PAD_MAJOR_MAX_MM)
        pad_x = _pad(w, CONTEXT_PAD_FRAC_MINOR, CONTEXT_PAD_MINOR_MIN_MM, CONTEXT_PAD_MINOR_MAX_MM)
    elif orient == HORIZONTAL:
        pad_x = _pad(w, CONTEXT_PAD_FRAC_MAJOR, CONTEXT_PAD_MAJOR_MIN_MM, CONTEXT_PAD_MAJOR_MAX_MM)
        pad_y = _pad(h, CONTEXT_PAD_FRAC_MINOR, CONTEXT_PAD_MINOR_MIN_MM, CONTEXT_PAD_MINOR_MAX_MM)
    else:
        pad_x = _pad(max(w, h), 0.22, CONTEXT_PAD_MINOR_MIN_MM, CONTEXT_PAD_MAJOR_MAX_MM)
        pad_y = pad_x
    raw = (core[0] - pad_x, core[1] - pad_y, core[2] + pad_x, core[3] + pad_y)
    barriers = list(anchor.get("x_barriers") or [-1e12, 1e12])
    mark = anchor.get("mark") or {"x": 0.5 * (core[0] + core[2]), "y": 0.5 * (core[1] + core[3])}
    extent = clamp_to_limits(
        raw,
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
    return {
        "extent": list(extent),
        "orientation": orient,
        "pad_x": pad_x,
        "pad_y": pad_y,
        "reason": "GEOMETRY_BOUNDED_BASELINE",
    }


__all__ = ["build_context_envelope"]
