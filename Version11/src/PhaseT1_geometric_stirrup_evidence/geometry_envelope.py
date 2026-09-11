"""
Phase T1.5 — Geometry Envelope Builder.
MODEL_VERSION: 9.3.5

Deterministic beam rendering windows from physical geometry signals:
  1. Beam axis / validated span (longitudinal)
  2. Support widths at ends
  3. Stirrup DIMENSION bands (-S-STIRUP / -STR-RF-DIM) near the mark
  4. Beam-outline horizontal LINE clusters bracketing the mark
  5. Spatially-filtered PhysicalBars (near mark Y AND inside X window)

Annotations identify WHICH beam (mark disambiguation only).
Geometry determines WHERE the envelope sits.

Does NOT implement entity ownership or DXF-handle maps.
Does NOT size the envelope from R.1 annotation bounding boxes.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .beam_extent import find_beam_mark

MODEL_VERSION = "9.3.5"
PHASE_ID = "T1.5"

ROW_Y_BAND_MM = 2000.0
SUPPORT_PAD_MM = 200.0
ENVELOPE_PAD_MM = 150.0
STIRRUP_Y_SEARCH_MM = 4000.0
OUTLINE_Y_SEARCH_MM = 4000.0
OUTLINE_MIN_LEN_MM = 1200.0
BAR_Y_NEAR_DEPTH_FACTOR = 4.0
DEPTH_FLOOR_FACTOR = 1.5
DEFAULT_DEPTH_MM = 600.0
DEFAULT_SPAN_MM = 3000.0


def _cluster_y(ys: List[float], tol: float = 50.0) -> List[Tuple[float, int]]:
    ys = sorted(ys)
    if not ys:
        return []
    clusters: List[List[float]] = [[ys[0]]]
    for y in ys[1:]:
        if y - clusters[-1][-1] <= tol:
            clusters[-1].append(y)
        else:
            clusters.append([y])
    return [(sum(c) / len(c), len(c)) for c in clusters]


def _merge_bands(
    bands: List[Tuple[float, float]], merge_gap: float = 250.0
) -> List[Tuple[float, float]]:
    if not bands:
        return []
    ordered = sorted(bands)
    out = [list(ordered[0])]
    for lo, hi in ordered[1:]:
        if lo <= out[-1][1] + merge_gap:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(a, b) for a, b in out]


def _ann_centroid(items: List[Dict[str, Any]]) -> Optional[Tuple[float, float]]:
    pts = []
    for a in items:
        if a.get("x") is None or a.get("y") is None:
            continue
        try:
            pts.append((float(a["x"]), float(a["y"])))
        except Exception:
            continue
    if not pts:
        return None
    return (
        sum(p[0] for p in pts) / len(pts),
        sum(p[1] for p in pts) / len(pts),
    )


def _stirup_bands(
    msp: Any,
    mx: float,
    my: float,
    x0: float,
    x1: float,
    depth_mm: float,
    outline: Optional[Tuple[float, float]] = None,
) -> List[Tuple[float, float]]:
    """Independent stirrup/tick Y-bands from DIMENSION geometry near mark.

    A band is kept only if its Y-mid is near the mark / outline (own elevation)
    and its X-mid lies inside the beam's longitudinal window — this rejects
    stacked-neighbor DIMENSION bands that merely X-overlap the window.
    """
    try:
        from ezdxf import bbox as ezbbox
    except ImportError:
        return []

    cache = ezbbox.Cache()
    x_half = max((x1 - x0) / 2.0 + 500.0, 1500.0)
    y_keep = max(2.8 * depth_mm, 1600.0)
    if outline:
        y_keep = max(y_keep, 0.55 * (outline[1] - outline[0]) + depth_mm)

    raw: List[Tuple[float, float]] = []
    for e in msp.query("DIMENSION"):
        try:
            layer = str(e.dxf.layer or "").upper()
        except Exception:
            continue
        is_stirup = "STIRUP" in layer or "STIRRUP" in layer
        is_rf = "STR-RF-DIM" in layer or layer.endswith("RF-DIM")
        if not (is_stirup or is_rf):
            continue
        if is_rf and not is_stirup:
            try:
                t = str(e.dxf.text or "")
            except Exception:
                t = ""
            if not re.search(r"@|C/C|STIR", t, re.I):
                continue
        try:
            ext = ezbbox.extents([e], cache=cache, fast=True)
            if not ext.has_data:
                continue
            bb = (
                float(ext.extmin.x),
                float(ext.extmin.y),
                float(ext.extmax.x),
                float(ext.extmax.y),
            )
        except Exception:
            continue
        # Require X-mid inside beam window (stricter than bbox overlap).
        mid_x = 0.5 * (bb[0] + bb[2])
        mid_y = 0.5 * (bb[1] + bb[3])
        if mid_x < x0 or mid_x > x1:
            continue
        if abs(mid_y - my) > STIRRUP_Y_SEARCH_MM:
            continue
        near_mark = abs(mid_y - my) <= y_keep
        near_outline = False
        if outline:
            near_outline = (outline[0] - depth_mm) <= mid_y <= (outline[1] + depth_mm)
        if not (near_mark or near_outline):
            continue
        raw.append((bb[1], bb[3]))
    return _merge_bands(raw)


def _outline_bracket(
    msp: Any,
    mx: float,
    my: float,
    x_half: float,
    depth_mm: float,
) -> Optional[Tuple[float, float]]:
    """Long horizontal LINE clusters bracketing the beam mark (outline proxy)."""
    ys: List[float] = []
    for e in msp:
        if e.dxftype() != "LINE":
            continue
        try:
            x1, y1 = float(e.dxf.start.x), float(e.dxf.start.y)
            x2, y2 = float(e.dxf.end.x), float(e.dxf.end.y)
        except Exception:
            continue
        if abs(y2 - y1) > 8.0:
            continue
        length = abs(x2 - x1)
        if length < OUTLINE_MIN_LEN_MM:
            continue
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        if abs(cx - mx) > x_half or abs(cy - my) > OUTLINE_Y_SEARCH_MM:
            continue
        ys.append(cy)
    clusters = _cluster_y(ys, tol=50.0)
    below = [y for y, _n in clusters if y < my]
    above = [y for y, _n in clusters if y > my]
    if not below or not above:
        return None
    # Prefer a pair whose separation is in a plausible elevation height range.
    best: Optional[Tuple[float, float, float]] = None
    for yb in below:
        for ya in above:
            sep = ya - yb
            if sep < depth_mm * 0.6 or sep > depth_mm * 8.0:
                continue
            score = -abs(sep - 3.0 * depth_mm)
            if best is None or score > best[0]:
                best = (score, yb, ya)
    if best is None:
        return (min(below), max(above))
    return (best[1], best[2])


def _filter_physical_bars(
    bars: List[Dict[str, Any]],
    mx: float,
    my: float,
    x0: float,
    x1: float,
    depth_mm: float,
) -> List[Dict[str, Any]]:
    """Keep bars near mark Y whose midpoint lies inside the beam X window.

    Does NOT trust R.3.1 beam_id assignment (known mis-assignments exist);
    spatial filter only.
    """
    out: List[Dict[str, Any]] = []
    y_tol = depth_mm * BAR_Y_NEAR_DEPTH_FACTOR
    for b in bars:
        try:
            y = float(b["y_position"])
            sx = float(b["start_x"])
            ex = float(b["end_x"])
        except Exception:
            continue
        if abs(y - my) > y_tol:
            continue
        mid = 0.5 * (sx + ex)
        if mid < x0 or mid > x1:
            continue
        out.append(b)
    return out


def _resolve_mark(
    beam_id: str,
    msp: Any,
    annotations: Optional[List[Dict[str, Any]]],
    axis: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Locate elevation beam-mark. Annotations used only for disambiguation."""
    near: Optional[Tuple[float, float]] = None
    if annotations:
        near = _ann_centroid(annotations)
    if near is None and axis:
        try:
            near = (
                float(axis["dxf_centroid_x"]),
                float(axis["dxf_centroid_y"]),
            )
        except Exception:
            near = None
    if near is None:
        return None
    return find_beam_mark(msp, beam_id, near)


def _longitudinal_x(
    mark: Dict[str, Any],
    axis: Optional[Dict[str, Any]],
    geometry: Optional[Dict[str, Any]],
) -> Tuple[float, float, List[str], Dict[str, Any]]:
    """X window from validated span (preferred) or BeamAxis dxf start/end."""
    signals: List[str] = []
    meta: Dict[str, Any] = {}
    mx = float(mark["x"])
    span = None
    if geometry:
        span = geometry.get("effective_span_mm") or geometry.get("clear_span_mm")
    if span:
        try:
            span = float(span)
        except Exception:
            span = None
    if span and span > 100:
        x0 = mx - span / 2.0 - SUPPORT_PAD_MM
        x1 = mx + span / 2.0 + SUPPORT_PAD_MM
        signals.extend(["axis", "support"])
        meta["span_source"] = "validated_beam_geometry"
        meta["span_mm"] = round(span, 2)
        return x0, x1, signals, meta

    if axis:
        try:
            x0 = float(axis["dxf_start_x"]) - SUPPORT_PAD_MM
            x1 = float(axis["dxf_end_x"]) + SUPPORT_PAD_MM
            if x1 > x0:
                signals.extend(["axis", "support"])
                meta["span_source"] = "beam_axis"
                meta["span_mm"] = round(x1 - x0 - 2 * SUPPORT_PAD_MM, 2)
                return x0, x1, signals, meta
        except Exception:
            pass

    # Last resort: default half-span around mark
    x0 = mx - DEFAULT_SPAN_MM / 2.0 - SUPPORT_PAD_MM
    x1 = mx + DEFAULT_SPAN_MM / 2.0 + SUPPORT_PAD_MM
    signals.extend(["axis_fallback", "support"])
    meta["span_source"] = "default_span"
    meta["span_mm"] = DEFAULT_SPAN_MM
    return x0, x1, signals, meta


def _ranges_overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return not (a1 < b0 or b1 < a0)


def _apply_row_splits(
    envelopes: Dict[str, Dict[str, Any]],
    marks: Dict[str, Dict[str, Any]],
) -> None:
    """Hard non-overlap X split between beams sharing an elevation row."""
    remaining = [b for b in envelopes if marks.get(b)]
    while remaining:
        seed = remaining[0]
        sy = float(marks[seed]["y"])
        row = [
            b
            for b in remaining
            if abs(float(marks[b]["y"]) - sy) <= ROW_Y_BAND_MM
        ]
        remaining = [b for b in remaining if b not in row]
        row_sorted = sorted(row, key=lambda b: float(marks[b]["x"]))
        for i in range(len(row_sorted) - 1):
            left_id = row_sorted[i]
            right_id = row_sorted[i + 1]
            split = 0.5 * (
                float(marks[left_id]["x"]) + float(marks[right_id]["x"])
            )
            left = envelopes[left_id]
            right = envelopes[right_id]
            if left["xmax"] is None or right["xmax"] is None:
                continue
            if left["xmax"] > split:
                left["xmax"] = split
                left.setdefault("notes", []).append(
                    f"row_split_right_at={split:.1f}_vs_{right_id}"
                )
            if right["xmin"] < split:
                right["xmin"] = split
                right.setdefault("notes", []).append(
                    f"row_split_left_at={split:.1f}_vs_{left_id}"
                )


def _apply_vertical_neighbor_splits(
    envelopes: Dict[str, Dict[str, Any]],
    marks: Dict[str, Dict[str, Any]],
    depths: Dict[str, float],
) -> None:
    """Clamp Y so stacked beams (same X column) do not swallow each other."""
    ids = [b for b in envelopes if marks.get(b) and envelopes[b].get("xmin") is not None]
    for bid in ids:
        env = envelopes[bid]
        my = float(marks[bid]["y"])
        depth = depths.get(bid, DEFAULT_DEPTH_MM)
        for oid in ids:
            if oid == bid:
                continue
            other = envelopes[oid]
            if not _ranges_overlap(
                float(env["xmin"]),
                float(env["xmax"]),
                float(other["xmin"]),
                float(other["xmax"]),
            ):
                continue
            oy = float(marks[oid]["y"])
            odepth = depths.get(oid, DEFAULT_DEPTH_MM)
            if oy < my - 200.0:
                # Neighbor below — keep above neighbor's depth floor.
                limit = oy + DEPTH_FLOOR_FACTOR * odepth
                if float(env["ymin"]) < limit:
                    env["ymin"] = limit
                    env.setdefault("notes", []).append(
                        f"vert_split_bottom_vs_{oid}_ymin={limit:.1f}"
                    )
            elif oy > my + 200.0:
                limit = oy - DEPTH_FLOOR_FACTOR * depth
                if float(env["ymax"]) > limit:
                    env["ymax"] = limit
                    env.setdefault("notes", []).append(
                        f"vert_split_top_vs_{oid}_ymax={limit:.1f}"
                    )


def build_geometry_envelope(
    beam_id: str,
    msp: Any,
    *,
    mark: Dict[str, Any],
    axis: Optional[Dict[str, Any]] = None,
    geometry: Optional[Dict[str, Any]] = None,
    physical_bars: Optional[List[Dict[str, Any]]] = None,
    pad_mm: float = ENVELOPE_PAD_MM,
) -> Dict[str, Any]:
    """Build one beam's geometry envelope (no neighbor split)."""
    depth = DEFAULT_DEPTH_MM
    if geometry and geometry.get("depth_mm"):
        try:
            depth = float(geometry["depth_mm"])
        except Exception:
            depth = DEFAULT_DEPTH_MM

    mx, my = float(mark["x"]), float(mark["y"])
    x0, x1, signals, meta = _longitudinal_x(mark, axis, geometry)
    x_half = max((x1 - x0) / 2.0 + 500.0, 1500.0)

    y_pts: List[float] = []
    fallbacks: List[str] = []

    outline = _outline_bracket(msp, mx, my, x_half, depth)
    if outline:
        signals.append("beam_outline")
        y_pts.extend([outline[0], outline[1]])
        meta["outline_y_mm"] = [round(outline[0], 2), round(outline[1], 2)]
    else:
        fallbacks.append("no_outline_bracket")

    bands = _stirup_bands(msp, mx, my, x0, x1, depth, outline=outline)
    if bands:
        signals.append("stirrup")
        for lo, hi in bands:
            y_pts.extend([lo, hi])
        meta["stirrup_bands_mm"] = [[round(a, 2), round(b, 2)] for a, b in bands]
    else:
        fallbacks.append("no_stirrup_dimension_bands")

    near_bars = _filter_physical_bars(
        physical_bars or [], mx, my, x0, x1, depth
    )
    if near_bars:
        if any(b.get("vertical_placement") == "TOP_FACE" for b in near_bars):
            signals.append("top_bar")
        if any(b.get("vertical_placement") == "BOTTOM_FACE" for b in near_bars):
            signals.append("bottom_bar")
        # If placement unknown, still count as bar signal
        if "top_bar" not in signals and "bottom_bar" not in signals:
            signals.append("top_bar")
        for b in near_bars:
            y_pts.append(float(b["y_position"]))
        meta["n_physical_bars_used"] = len(near_bars)
    else:
        fallbacks.append("no_spatial_physical_bars")

    # Depth floor around mark — ensures a minimum vertical window even if
    # stirrup/outline signals are sparse.
    y_pts.extend([my - DEPTH_FLOOR_FACTOR * depth, my + DEPTH_FLOOR_FACTOR * depth])
    if "depth_floor" not in signals:
        signals.append("depth_floor")

    ymin = min(y_pts) - pad_mm
    ymax = max(y_pts) + pad_mm

    # Deduplicate signals preserving order
    seen = set()
    signals_ordered = []
    for s in signals:
        if s not in seen:
            seen.add(s)
            signals_ordered.append(s)

    conf = _confidence(signals_ordered, bands, outline, near_bars)

    orientation = "HORIZONTAL"
    if axis and axis.get("orientation"):
        orientation = str(axis["orientation"])

    return {
        "beam_id": beam_id,
        "xmin": round(x0, 2),
        "ymin": round(ymin, 2),
        "xmax": round(x1, 2),
        "ymax": round(ymax, 2),
        "axis": {
            "mark_x": round(mx, 2),
            "mark_y": round(my, 2),
            "dxf_start_x": round(x0 + SUPPORT_PAD_MM, 2),
            "dxf_end_x": round(x1 - SUPPORT_PAD_MM, 2),
            "centroid_x": round(mx, 2),
            "centroid_y": round(my, 2),
        },
        "orientation": orientation,
        "geometry_confidence": conf,
        "signals_used": signals_ordered,
        "fallbacks_used": fallbacks,
        "extent": (round(x0, 2), round(ymin, 2), round(x1, 2), round(ymax, 2)),
        "depth_mm": depth,
        "meta": meta,
        "notes": [],
        "model_version": MODEL_VERSION,
        "phase_id": PHASE_ID,
    }


def _confidence(
    signals: List[str],
    bands: List[Tuple[float, float]],
    outline: Optional[Tuple[float, float]],
    bars: List[Dict[str, Any]],
) -> str:
    score = 0
    if bands:
        score += 2
    if outline:
        score += 1
    if any(s in signals for s in ("top_bar", "bottom_bar")):
        score += 1
    if "axis" in signals:
        score += 1
    if score >= 4:
        return "HIGH"
    if score >= 2:
        return "MEDIUM"
    return "LOW"


def compute_geometry_envelopes(
    beam_ids: List[str],
    msp: Any,
    *,
    annotations_by_beam: Dict[str, List[Dict[str, Any]]],
    axes_by_beam: Optional[Dict[str, Dict[str, Any]]] = None,
    geometries_by_beam: Optional[Dict[str, Dict[str, Any]]] = None,
    physical_bars: Optional[List[Dict[str, Any]]] = None,
    pad_mm: float = ENVELOPE_PAD_MM,
) -> Dict[str, Dict[str, Any]]:
    """
    Build geometry envelopes for *beam_ids*, applying row non-overlap X splits
    using marks from the full annotation map (so out-of-scope neighbors still
    constrain bleed).
    """
    axes_by_beam = axes_by_beam or {}
    geometries_by_beam = geometries_by_beam or {}
    physical_bars = physical_bars or []

    # Resolve marks for all annotated beams (neighbor awareness).
    all_marks: Dict[str, Dict[str, Any]] = {}
    for bid, items in annotations_by_beam.items():
        mark = _resolve_mark(bid, msp, items, axes_by_beam.get(bid))
        if mark:
            all_marks[bid] = mark

    envelopes: Dict[str, Dict[str, Any]] = {}
    for bid in beam_ids:
        mark = all_marks.get(bid)
        if mark is None:
            mark = _resolve_mark(
                bid, msp, annotations_by_beam.get(bid), axes_by_beam.get(bid)
            )
        if mark is None:
            envelopes[bid] = {
                "beam_id": bid,
                "xmin": None,
                "ymin": None,
                "xmax": None,
                "ymax": None,
                "extent": None,
                "axis": None,
                "orientation": "UNKNOWN",
                "geometry_confidence": "LOW",
                "signals_used": [],
                "fallbacks_used": ["no_beam_mark"],
                "notes": ["no_beam_mark"],
                "model_version": MODEL_VERSION,
                "phase_id": PHASE_ID,
            }
            continue
        all_marks[bid] = mark
        envelopes[bid] = build_geometry_envelope(
            bid,
            msp,
            mark=mark,
            axis=axes_by_beam.get(bid),
            geometry=geometries_by_beam.get(bid),
            physical_bars=physical_bars,
            pad_mm=pad_mm,
        )

    # Row splits need marks for every envelope we built.
    split_marks = {b: all_marks[b] for b in envelopes if b in all_marks}
    # Also include neighbor marks outside beam_ids so splits see full rows.
    for bid, mark in all_marks.items():
        if bid not in envelopes:
            # Build a lightweight X-only neighbor stub for split participation
            # without full Y work — use longitudinal X only.
            x0, x1, _sigs, _meta = _longitudinal_x(
                mark, axes_by_beam.get(bid), geometries_by_beam.get(bid)
            )
            envelopes[bid] = {
                "beam_id": bid,
                "xmin": x0,
                "ymin": 0.0,
                "xmax": x1,
                "ymax": 0.0,
                "extent": (x0, 0.0, x1, 0.0),
                "axis": {"mark_x": mark["x"], "mark_y": mark["y"]},
                "orientation": "HORIZONTAL",
                "geometry_confidence": "NEIGHBOR_STUB",
                "signals_used": ["neighbor_stub"],
                "fallbacks_used": [],
                "notes": ["neighbor_stub_for_row_split"],
                "model_version": MODEL_VERSION,
                "phase_id": PHASE_ID,
                "_neighbor_stub": True,
            }
            split_marks[bid] = mark

    _apply_row_splits(envelopes, split_marks)

    depths = {
        bid: float(
            (geometries_by_beam.get(bid) or {}).get("depth_mm") or DEFAULT_DEPTH_MM
        )
        for bid in envelopes
    }
    _apply_vertical_neighbor_splits(envelopes, split_marks, depths)

    # Refresh extent tuples after splits; drop stubs from return.
    out: Dict[str, Dict[str, Any]] = {}
    for bid in beam_ids:
        env = envelopes.get(bid)
        if not env:
            continue
        if env.get("xmin") is not None and env.get("ymin") is not None:
            # Keep xmin/xmax rounded after split
            env["xmin"] = round(float(env["xmin"]), 2)
            env["xmax"] = round(float(env["xmax"]), 2)
            env["ymin"] = round(float(env["ymin"]), 2)
            env["ymax"] = round(float(env["ymax"]), 2)
            if env["xmax"] <= env["xmin"] or env["ymax"] <= env["ymin"]:
                env.setdefault("notes", []).append("degenerate_envelope_after_split")
                env["geometry_confidence"] = "LOW"
            env["extent"] = (
                env["xmin"],
                env["ymin"],
                env["xmax"],
                env["ymax"],
            )
        out[bid] = env
    return out


def envelopes_to_extent_info(
    envelopes: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Adapt T1.5 envelopes to the shape expected by `_opencv_for_beam`."""
    out: Dict[str, Dict[str, Any]] = {}
    for bid, env in envelopes.items():
        extent = env.get("extent")
        out[bid] = {
            "beam_id": bid,
            "extent": extent,
            "core": extent,
            "mark": (
                {
                    "text": None,
                    "x": (env.get("axis") or {}).get("mark_x"),
                    "y": (env.get("axis") or {}).get("mark_y"),
                }
                if env.get("axis")
                else None
            ),
            "pad_used_mm": None,
            "notes": list(env.get("notes") or [])
            + [f"t15_signals={env.get('signals_used')}"],
            "geometry_envelope": env,
            "source": "T1.5_geometry_envelope",
        }
    return out
