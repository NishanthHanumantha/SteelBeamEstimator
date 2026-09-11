"""Build context/detail DXF extents from title + outline geometry. No annotation association."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from PhaseT1_geometric_stirrup_evidence.geometry_envelope import (
    ROW_Y_BAND_MM,
    _apply_row_splits,
    build_geometry_envelope,
)

from .config import (
    CONTEXT_PAD_MM,
    DETAIL_PAD_MM,
    LOCALIZATION_METHOD,
    LOCALIZATION_SOURCE,
    OTHER_ROW_TITLE_MM,
)


def _pad_extent(
    extent: Tuple[float, float, float, float], pad_mm: float
) -> Tuple[float, float, float, float]:
    xmin, ymin, xmax, ymax = extent
    return (xmin - pad_mm, ymin - pad_mm, xmax + pad_mm, ymax + pad_mm)


def _row_neighbor_marks(
    titles: list,
    beam_id: str,
    mark: Dict[str, Any],
    *,
    max_neighbors: int = 8,
) -> Dict[str, Dict[str, Any]]:
    my = float(mark["y"])
    mx = float(mark["x"])
    by_id: Dict[str, Dict[str, Any]] = {}
    for t in titles or []:
        nid = str(t.get("beam_id") or "")
        if not nid or nid.upper() == beam_id.upper():
            continue
        try:
            ty = float(t["y"])
            tx = float(t["x"])
        except (TypeError, ValueError, KeyError):
            continue
        if abs(ty - my) > ROW_Y_BAND_MM:
            continue
        prev = by_id.get(nid)
        if prev is None or abs(tx - mx) < abs(float(prev["x"]) - mx):
            by_id[nid] = t
    ranked = sorted(by_id.items(), key=lambda kv: abs(float(kv[1]["x"]) - mx))
    return {nid: rec for nid, rec in ranked[:max_neighbors]}


def _tighten_detail_y(
    extent: Tuple[float, float, float, float],
    mark: Dict[str, Any],
    titles: list,
    beam_id: str,
) -> Tuple[float, float, float, float]:
    """Keep Type B on the target elevation. Do not let a nearby row steal the beam body."""
    xmin, ymin, xmax, ymax = extent
    my = float(mark["y"])
    depth = float(mark.get("depth_mm") or 600.0)
    keep_below = my - 1.05 * depth - 280.0
    keep_above = my + 2.2 * depth + 500.0
    ymin = max(ymin, keep_below - 200.0)
    ymax = min(ymax, keep_above)
    for t in titles or []:
        nid = str(t.get("beam_id") or "")
        if not nid or nid.upper() == beam_id.upper():
            continue
        try:
            ty = float(t["y"])
            tx = float(t["x"])
        except (TypeError, ValueError, KeyError):
            continue
        if abs(ty - my) < OTHER_ROW_TITLE_MM:
            continue
        if tx < xmin - 400.0 or tx > xmax + 400.0:
            continue
        split = 0.5 * (ty + my)
        if ty < my and split < keep_below:
            ymin = max(ymin, split)
        elif ty > my and split > keep_above:
            ymax = min(ymax, split)
    if ymax <= ymin + 200.0:
        return extent
    return (xmin, ymin, xmax, ymax)


def build_target_regions(
    *,
    msp: Any,
    beam_id: str,
    mark: Dict[str, Any],
    titles: Optional[list] = None,
    neighbor_marks: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    geometry = {
        "depth_mm": mark.get("depth_mm") or 600.0,
        "width_mm": mark.get("width_mm"),
    }
    env = build_geometry_envelope(
        beam_id,
        msp,
        mark=mark,
        axis=None,
        geometry=geometry,
        physical_bars=None,
    )
    envelopes = {beam_id: env}
    marks = {beam_id: mark}
    neighbors = neighbor_marks if neighbor_marks is not None else _row_neighbor_marks(titles or [], beam_id, mark)
    for nid, nmark in (neighbors or {}).items():
        if nid == beam_id or not nmark:
            continue
        ngeom = {"depth_mm": nmark.get("depth_mm") or 600.0}
        envelopes[nid] = build_geometry_envelope(nid, msp, mark=nmark, geometry=ngeom, physical_bars=None)
        marks[nid] = nmark
    _apply_row_splits(envelopes, marks)
    target = envelopes[beam_id]
    if target.get("xmin") is not None:
        target["extent"] = (
            float(target["xmin"]),
            float(target["ymin"]),
            float(target["xmax"]),
            float(target["ymax"]),
        )
    extent = target.get("extent")
    if not extent:
        mx, my = float(mark["x"]), float(mark["y"])
        extent = (mx - 2000.0, my - 1500.0, mx + 2000.0, my + 1500.0)
        target["extent"] = extent
        target.setdefault("notes", []).append("fallback_title_window")
    detail = _tighten_detail_y(
        _pad_extent(tuple(extent), DETAIL_PAD_MM), mark, titles or [], beam_id
    )
    context = _pad_extent(tuple(extent), CONTEXT_PAD_MM)
    return {
        "localization_method": LOCALIZATION_METHOD,
        "localization_source": LOCALIZATION_SOURCE,
        "annotation_association_dependency": False,
        "mark": {"x": mark.get("x"), "y": mark.get("y"), "text": mark.get("text"), "score": mark.get("score")},
        "envelope": target,
        "detail_extent": detail,
        "context_extent": context,
        "geometry_included": True,
        "outline_found": "beam_outline" in (target.get("signals_used") or []),
        "title_included": True,
        "neighbor_split_count": max(0, len(envelopes) - 1),
    }


__all__ = ["build_target_regions"]
