"""Bounded direction-aware crop recovery. No beam-ID logic. No sheet-wide fallback."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from PhaseP2610B_adaptive_beam_detail_crop.evidence import next_row_y_cap, owned_by_mark, prev_row_y_floor, x_barriers
from PhaseP2610A_beam_region_crop_audit.title_localizer import iter_text_inserts

from .config import (
    EXPAND_STEP_CONTEXT_MM,
    EXPAND_STEP_DETAIL_MM,
    MAX_CONTEXT_ATTEMPTS,
    MAX_CONTEXT_HEIGHT_MM,
    MAX_CONTEXT_WIDTH_MM,
    MAX_DETAIL_ATTEMPTS,
    MAX_DETAIL_HEIGHT_MM,
    MAX_DETAIL_WIDTH_MM,
    MAX_EXPAND_FACTOR,
    MIN_HEIGHT_MM,
    MIN_WIDTH_MM,
    TRIM_PAD_MM,
)
from .geometry import (
    as_extent,
    clamp_to_limits,
    expand_side,
    factor_vs,
    height,
    union,
    width,
)
from .orientation import COMPACT, HORIZONTAL, UNKNOWN, VERTICAL, axis_sides
from .quality import STATUS_BLACK, STATUS_CLIP, STATUS_EMPTY, STATUS_LOW_CTX, STATUS_LOW_INFO, STATUS_MISSING

ACTION_NONE = "NONE"
ACTION_EXPAND_LEFT = "EXPAND_LEFT"
ACTION_EXPAND_RIGHT = "EXPAND_RIGHT"
ACTION_EXPAND_BOTH_X = "EXPAND_BOTH_X"
ACTION_EXPAND_TOP = "EXPAND_TOP"
ACTION_EXPAND_BOTTOM = "EXPAND_BOTTOM"
ACTION_EXPAND_BOTH_Y = "EXPAND_BOTH_Y"
ACTION_TRIM_EMPTY = "TRIM_EMPTY_SIDE"
ACTION_SHIFT_CONTENT = "SHIFT_TO_CONTENT"
ACTION_BALANCED = "EXPAND_BALANCED"


def _limits(mark: Dict[str, Any], titles: Sequence[Dict[str, Any]], crop_type: str) -> Dict[str, float]:
    left, right = x_barriers(mark, titles)
    return {
        "x_left": left,
        "x_right": right,
        "y_floor": prev_row_y_floor(mark, titles),
        "y_cap": next_row_y_cap(mark, titles),
        "max_w": MAX_CONTEXT_WIDTH_MM if crop_type == "context" else MAX_DETAIL_WIDTH_MM,
        "max_h": MAX_CONTEXT_HEIGHT_MM if crop_type == "context" else MAX_DETAIL_HEIGHT_MM,
        "min_w": MIN_WIDTH_MM,
        "min_h": MIN_HEIGHT_MM,
    }


def _apply_limits(extent: Sequence[float], mark: Dict[str, Any], titles: Sequence[Dict[str, Any]], crop_type: str) -> Tuple[float, float, float, float]:
    lim = _limits(mark, titles, crop_type)
    if crop_type == "detail":
        lim["max_w"] = MAX_DETAIL_WIDTH_MM
        lim["max_h"] = MAX_DETAIL_HEIGHT_MM
    return clamp_to_limits(
        extent,
        x_left=lim["x_left"],
        x_right=lim["x_right"],
        y_floor=lim["y_floor"],
        y_cap=lim["y_cap"],
        max_w=lim["max_w"],
        max_h=lim["max_h"],
        min_w=lim["min_w"],
        min_h=lim["min_h"],
        anchor=(float(mark["x"]), float(mark["y"])),
    )


def content_aabb_from_dxf(
    msp: Any,
    mark: Dict[str, Any],
    titles: Sequence[Dict[str, Any]],
    search: Sequence[float],
) -> Optional[Tuple[float, float, float, float]]:
    if msp is None:
        return None
    xmin, ymin, xmax, ymax = as_extent(search)
    xs: List[float] = []
    ys: List[float] = []
    mx, my = float(mark["x"]), float(mark["y"])
    for text, x, y in iter_text_inserts(msp):
        if x < xmin or x > xmax or y < ymin or y > ymax:
            continue
        if not owned_by_mark(x, y, mark, titles):
            continue
        xs.append(x)
        ys.append(y)
    n_line = 0
    for e in msp:
        if n_line > 4000:
            break
        try:
            dt = e.dxftype()
        except Exception:
            continue
        if dt not in ("LINE", "LWPOLYLINE"):
            continue
        n_line += 1
        pts = []
        try:
            if dt == "LINE":
                pts = [(float(e.dxf.start.x), float(e.dxf.start.y)), (float(e.dxf.end.x), float(e.dxf.end.y))]
            else:
                pts = [(float(p[0]), float(p[1])) for p in e.get_points("xy")]
        except Exception:
            continue
        for x, y in pts:
            if x < xmin or x > xmax or y < ymin or y > ymax:
                continue
            if abs(x - mx) > 5200.0 or abs(y - my) > 4200.0:
                continue
            if not owned_by_mark(x, y, mark, titles, max_dist_mm=5200.0):
                continue
            xs.append(x)
            ys.append(y)
    if len(xs) < 3:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def choose_action(
    *,
    diagnostic: Dict[str, Any],
    orientation: str,
    border: Optional[Dict[str, Any]] = None,
) -> str:
    primary = diagnostic.get("primary_status")
    empty_sides = list(diagnostic.get("empty_sides") or [])
    contact = dict(diagnostic.get("meaningful_border_contact") or {})
    if border:
        contact = dict(border.get("sides") or contact)
    bbox = diagnostic.get("content_bbox_dxf")
    if primary in (STATUS_EMPTY, STATUS_BLACK, STATUS_LOW_INFO, STATUS_MISSING):
        if bbox:
            return ACTION_SHIFT_CONTENT
        if empty_sides:
            return ACTION_TRIM_EMPTY
        if orientation == VERTICAL:
            return ACTION_EXPAND_BOTH_Y
        if orientation == HORIZONTAL:
            return ACTION_EXPAND_BOTH_X
        return ACTION_BALANCED
    mean_sides = [s for s, v in contact.items() if v]
    if primary in (STATUS_CLIP, STATUS_LOW_CTX) or mean_sides:
        axis = set(axis_sides(orientation))
        x_hit = [s for s in mean_sides if s in ("left", "right") and s in axis or (orientation in (HORIZONTAL, COMPACT, UNKNOWN) and s in ("left", "right"))]
        y_hit = [s for s in mean_sides if s in ("top", "bottom") and (orientation in (VERTICAL, COMPACT, UNKNOWN) or s in axis)]
        if orientation == HORIZONTAL:
            if "left" in mean_sides and "right" in mean_sides:
                return ACTION_EXPAND_BOTH_X
            if "right" in mean_sides:
                return ACTION_EXPAND_RIGHT
            if "left" in mean_sides:
                return ACTION_EXPAND_LEFT
            if empty_sides:
                return ACTION_TRIM_EMPTY
            return ACTION_EXPAND_BOTH_X
        if orientation == VERTICAL:
            if "top" in mean_sides and "bottom" in mean_sides:
                return ACTION_EXPAND_BOTH_Y
            if "top" in mean_sides:
                return ACTION_EXPAND_TOP
            if "bottom" in mean_sides:
                return ACTION_EXPAND_BOTTOM
            return ACTION_EXPAND_BOTH_Y
        if x_hit and not y_hit:
            if "left" in x_hit and "right" in x_hit:
                return ACTION_EXPAND_BOTH_X
            return ACTION_EXPAND_LEFT if "left" in x_hit else ACTION_EXPAND_RIGHT
        if y_hit and not x_hit:
            if "top" in y_hit and "bottom" in y_hit:
                return ACTION_EXPAND_BOTH_Y
            return ACTION_EXPAND_TOP if "top" in y_hit else ACTION_EXPAND_BOTTOM
        return ACTION_BALANCED
    return ACTION_NONE


def _trim_empty(extent: Sequence[float], diagnostic: Dict[str, Any]) -> Tuple[float, float, float, float]:
    xmin, ymin, xmax, ymax = as_extent(extent)
    bbox = diagnostic.get("content_bbox_dxf")
    empty = set(diagnostic.get("empty_sides") or [])
    if bbox:
        bx0, by0, bx1, by1 = (float(v) for v in bbox)
        if "right" in empty:
            xmax = min(xmax, bx1 + TRIM_PAD_MM)
        if "left" in empty:
            xmin = max(xmin, bx0 - TRIM_PAD_MM)
        if "top" in empty:
            ymax = min(ymax, by1 + TRIM_PAD_MM)
        if "bottom" in empty:
            ymin = max(ymin, by0 - TRIM_PAD_MM)
    else:
        occ = diagnostic.get("column_occupancy") or [1] * 8
        if "right" in empty:
            xmax = xmin + width(extent) * max(0.35, sum(1 for v in occ[:5] if v > 0.01) / 8.0)
        if "left" in empty:
            xmin = xmax - width(extent) * 0.45
    if xmax < xmin + MIN_WIDTH_MM:
        mid = 0.5 * (xmin + xmax)
        xmin, xmax = mid - MIN_WIDTH_MM / 2.0, mid + MIN_WIDTH_MM / 2.0
    if ymax < ymin + MIN_HEIGHT_MM:
        mid = 0.5 * (ymin + ymax)
        ymin, ymax = mid - MIN_HEIGHT_MM / 2.0, mid + MIN_HEIGHT_MM / 2.0
    return as_extent((xmin, ymin, xmax, ymax))


def _shift_to_content(extent: Sequence[float], diagnostic: Dict[str, Any], mark: Dict[str, Any]) -> Tuple[float, float, float, float]:
    bbox = diagnostic.get("content_bbox_dxf")
    if not bbox:
        return as_extent(extent)
    padded = (
        float(bbox[0]) - TRIM_PAD_MM,
        float(bbox[1]) - TRIM_PAD_MM,
        float(bbox[2]) + TRIM_PAD_MM,
        float(bbox[3]) + TRIM_PAD_MM,
    )
    return union(padded, (float(mark["x"]) - 400.0, float(mark["y"]) - 300.0, float(mark["x"]) + 400.0, float(mark["y"]) + 900.0))


def apply_action(
    extent: Sequence[float],
    action: str,
    *,
    diagnostic: Dict[str, Any],
    mark: Dict[str, Any],
    titles: Sequence[Dict[str, Any]],
    crop_type: str,
    step_mm: Optional[float] = None,
    container: Optional[Sequence[float]] = None,
) -> Tuple[float, float, float, float]:
    step = step_mm if step_mm is not None else (
        EXPAND_STEP_CONTEXT_MM if crop_type == "context" else EXPAND_STEP_DETAIL_MM
    )
    cur = as_extent(extent)
    if action == ACTION_TRIM_EMPTY:
        nxt = _trim_empty(cur, diagnostic)
    elif action == ACTION_SHIFT_CONTENT:
        nxt = _shift_to_content(cur, diagnostic, mark)
    elif action == ACTION_EXPAND_LEFT:
        nxt = expand_side(cur, "left", step)
    elif action == ACTION_EXPAND_RIGHT:
        nxt = expand_side(cur, "right", step)
    elif action == ACTION_EXPAND_BOTH_X:
        nxt = expand_side(expand_side(cur, "left", step), "right", step)
    elif action == ACTION_EXPAND_TOP:
        nxt = expand_side(cur, "top", step)
    elif action == ACTION_EXPAND_BOTTOM:
        nxt = expand_side(cur, "bottom", step)
    elif action == ACTION_EXPAND_BOTH_Y:
        nxt = expand_side(expand_side(cur, "top", step), "bottom", step)
    elif action == ACTION_BALANCED:
        nxt = expand_side(expand_side(expand_side(expand_side(cur, "left", step * 0.6), "right", step * 0.6), "top", step * 0.4), "bottom", step * 0.4)
    else:
        nxt = cur
    nxt = _apply_limits(nxt, mark, titles, crop_type)
    if container is not None:
        c = as_extent(container)
        nxt = (
            max(nxt[0], c[0]),
            max(nxt[1], c[1]),
            min(nxt[2], c[2]),
            min(nxt[3], c[3]),
        )
        nxt = as_extent(nxt)
    return nxt


def recover_once(
    *,
    extent: Sequence[float],
    diagnostic: Dict[str, Any],
    orientation: str,
    mark: Dict[str, Any],
    titles: Sequence[Dict[str, Any]],
    crop_type: str,
    initial_extent: Sequence[float],
    attempt: int,
    border: Optional[Dict[str, Any]] = None,
    container: Optional[Sequence[float]] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    max_attempts = MAX_CONTEXT_ATTEMPTS if crop_type == "context" else MAX_DETAIL_ATTEMPTS
    action = choose_action(diagnostic=diagnostic, orientation=orientation, border=border)
    before = as_extent(extent)
    blocked = False
    note = ""
    if attempt >= max_attempts:
        blocked = True
        note = "max_attempts"
        after = before
        action = ACTION_NONE
    elif action == ACTION_NONE:
        after = before
        note = "no_action"
    else:
        after = apply_action(
            before,
            action,
            diagnostic=diagnostic,
            mark=mark,
            titles=titles,
            crop_type=crop_type,
            container=container,
        )
        if factor_vs(initial_extent, after) > MAX_EXPAND_FACTOR + 1e-6:
            blocked = True
            note = "max_expand_factor"
            after = before
            action = ACTION_NONE
        elif after == before:
            note = "clamped_noop"
    return {
        "attempt": attempt,
        "reason": reason or diagnostic.get("primary_status") or "DIAGNOSTIC",
        "orientation": orientation,
        "action": action,
        "before_bounds": list(before),
        "after_bounds": list(after),
        "blocked": blocked,
        "note": note,
        "result": "PENDING",
    }


__all__ = [
    "choose_action",
    "content_aabb_from_dxf",
    "recover_once",
    "apply_action",
]
