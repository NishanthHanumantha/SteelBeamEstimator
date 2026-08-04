"""
T1.6 Steps 2–4 — Candidate ownership, scoring, exclusive assignment.
MODEL_VERSION: 9.3.6

Deterministic engineering-geometry rules only. Every decision carries reasons.
"""
from __future__ import annotations

import math
import re
import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple

MODEL_VERSION = "9.3.6"

OWNERSHIP_HIGH = "HIGH"
OWNERSHIP_MEDIUM = "MEDIUM"
OWNERSHIP_LOW = "LOW"
OWNERSHIP_NONE = "NONE"
OWNERSHIP_UNKNOWN = "UNKNOWN"

# Render gate (Step 5): only HIGH is drawn.
RENDERABLE = frozenset({OWNERSHIP_HIGH})

ANN_MATCH_TOL_MM = 120.0
LEADER_MATCH_TOL_MM = 80.0
BAR_MATCH_TOL_MM = 40.0
AXIS_PARALLEL_SLOPE = 0.08
AXIS_PERP_MIN_SLOPE = 8.0  # nearly vertical
ENVELOPE_EXPAND_MM = 80.0
# Beam body half-height for ownership (T1.5 envelope may be taller due to
# annotation/stirrup padding — do not treat that full height as the body).
BODY_HALF_DEPTH_FACTOR = 1.35
BAR_BAND_DEPTH_FACTOR = 1.50


def _overlap_1d(a0: float, a1: float, b0: float, b1: float) -> float:
    lo, hi = (a0, a1) if a0 <= a1 else (a1, a0)
    # Degenerate (point) interval: treat containment as full unit overlap.
    if abs(hi - lo) < 1e-9:
        return 1.0 if b0 - 1e-9 <= lo <= b1 + 1e-9 else 0.0
    return max(0.0, min(hi, b1) - max(lo, b0))


def _bbox_overlap_pct(
    bb: List[float], env: Tuple[float, float, float, float]
) -> float:
    """
    Fraction of entity bbox that lies inside envelope.

    Degenerate (zero-height / zero-width) bboxes — typical of pure
    horizontal/vertical LINE entities — use interval containment rather
    than area, otherwise overlap collapses to 0.0.
    """
    ex0, ey0, ex1, ey1 = env
    w = max(bb[2] - bb[0], 0.0)
    h = max(bb[3] - bb[1], 0.0)
    ox = _overlap_1d(bb[0], bb[2], ex0, ex1)
    oy = _overlap_1d(bb[1], bb[3], ey0, ey1)

    if w < 1e-6 and h < 1e-6:
        # Point entity
        return 1.0 if (ox > 0 and oy > 0) else 0.0
    if w < 1e-6:
        # Vertical line / zero-width: length-fraction of Y inside
        return oy / max(h, 1e-6) if ox > 0 else 0.0
    if h < 1e-6:
        # Horizontal line / zero-height: length-fraction of X inside
        return ox / max(w, 1e-6) if oy > 0 else 0.0
    return (ox * oy) / (w * h)


def _point_in_env(x: float, y: float, env: Tuple[float, float, float, float]) -> bool:
    return env[0] <= x <= env[2] and env[1] <= y <= env[3]


def _segment_env_overlap_pct(
    ent: Dict[str, Any], env: Tuple[float, float, float, float]
) -> Optional[float]:
    """
    For LINE-like entities: fraction of sampled segment points inside the
    envelope. Handles multi-beam spanning bars. Returns None if not applicable.
    """
    sp, ep = ent.get("start_point"), ent.get("end_point")
    if not sp or not ep:
        return None
    x0, y0 = float(sp[0]), float(sp[1])
    x1, y1 = float(ep[0]), float(ep[1])
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 1e-6:
        return 1.0 if _point_in_env(x0, y0, env) else 0.0
    n = max(8, min(64, int(length / 50.0) + 1))
    inside = 0
    for i in range(n + 1):
        t = i / n
        x = x0 + t * (x1 - x0)
        y = y0 + t * (y1 - y0)
        if _point_in_env(x, y, env):
            inside += 1
    return inside / (n + 1)


def _dist_point_to_axis_y(y: float, axis_y: float) -> float:
    return abs(y - axis_y)


def _line_slope(ent: Dict[str, Any]) -> Optional[float]:
    sp, ep = ent.get("start_point"), ent.get("end_point")
    if not sp or not ep:
        return None
    dx = ep[0] - sp[0]
    dy = ep[1] - sp[1]
    if abs(dx) < 1e-9:
        return float("inf")
    return abs(dy / dx)


def _layer_flags(layer: str) -> Dict[str, bool]:
    u = (layer or "").upper()
    return {
        "layer_reinf": "REINF" in u or u.endswith("-RF") or "REIN" in u,
        "layer_stirup": "STIRUP" in u or "STIRRUP" in u,
        "layer_dim": "DIM" in u,
        "layer_arrow": "ARROW" in u or "LEADER" in u,
        "layer_text": "TEXT" in u or "ANNO" in u,
    }


def _role_guess(
    ent: Dict[str, Any],
    evidence: Dict[str, Any],
    axis_y: float,
) -> str:
    dtype = ent.get("entity_type") or ""
    text = (ent.get("text") or ent.get("dimension_text") or "").upper()
    if dtype in ("TEXT", "MTEXT"):
        if re.search(r"B\d+", text):
            return "BEAM_MARK"
        if "@" in text or "C/C" in text:
            return "STIRRUP_LABEL"
        if re.search(r"\d\s*-?\s*Y\d+", text):
            cy = (ent.get("centroid") or [0, axis_y])[1]
            return "TOP_BAR_LABEL" if cy >= axis_y else "BOTTOM_BAR_LABEL"
        return "ANNOTATION"
    if dtype == "DIMENSION":
        return "STIRRUP_DIMENSION" if evidence.get("layer_stirup") else "DIMENSION"
    if dtype == "LEADER":
        return "LEADER"
    if dtype in ("LINE", "LWPOLYLINE"):
        if evidence.get("parallel_to_axis"):
            cy = (ent.get("centroid") or [0, axis_y])[1]
            if evidence.get("inside_top_bar_band"):
                return "TOP_BAR"
            if evidence.get("inside_bottom_bar_band"):
                return "BOTTOM_BAR"
            return "LONGITUDINAL_BAR" if cy >= axis_y else "LONGITUDINAL_BAR"
        if evidence.get("perpendicular_to_axis"):
            return "STIRRUP_OR_SUPPORT"
        if evidence.get("layer_stirup") or evidence.get("inside_stirrup_band"):
            return "STIRRUP_GEOMETRY"
        return "GEOMETRY"
    if dtype == "INSERT":
        return "BLOCK_INSERT"
    if dtype in ("CIRCLE", "ARC"):
        return "NODE_OR_SYMBOL"
    return "OTHER"


def _cluster_ys(ys: Sequence[float], gap: float) -> List[List[float]]:
    if not ys:
        return []
    ordered = sorted(ys)
    clusters: List[List[float]] = [[ordered[0]]]
    for y in ordered[1:]:
        if y - clusters[-1][-1] > gap:
            clusters.append([y])
        else:
            clusters[-1].append(y)
    return clusters


def _resolve_body_band(
    env: Tuple[float, float, float, float],
    axis_y: float,
    depth_mm: float,
    ann_pts: List[Tuple[float, float, str]],
    entities: Optional[List[Dict[str, Any]]],
    outline_y: Optional[List[float]],
) -> Tuple[float, float, str]:
    """
    Stacked beam rows share one tall T1.5 envelope. Pick the Y-cluster of
    horizontal geometry nearest this beam's R.1 annotation cloud (not the
    mark Y alone — the mark often sits in the whitespace between rows).
    """
    geom_ys: List[float] = []
    for e in entities or []:
        dtype = e.get("entity_type") or ""
        if dtype not in ("LINE", "LWPOLYLINE"):
            continue
        layer = (e.get("layer") or "").upper()
        if not any(k in layer for k in ("REINF", "BEAM", "SLAB", "STIRUP", "STIRRUP")):
            continue
        sp, ep = e.get("start_point"), e.get("end_point")
        if not sp or not ep:
            continue
        if abs(ep[1] - sp[1]) > 80:  # near-horizontal only
            continue
        cy = 0.5 * (sp[1] + ep[1])
        x0, x1 = min(sp[0], ep[0]), max(sp[0], ep[0])
        if x1 < env[0] or x0 > env[2]:
            continue
        if cy < env[1] - 80 or cy > env[3] + 80:
            continue
        # Require some X overlap with the beam window
        if _overlap_1d(x0, x1, env[0], env[2]) < 80:
            continue
        geom_ys.append(cy)

    ann_ys = [
        ay
        for ax, ay, _txt in ann_pts
        if env[0] - 300 <= ax <= env[2] + 300 and env[1] - 200 <= ay <= env[3] + 200
    ]
    target = statistics.median(ann_ys) if ann_ys else axis_y

    clusters = _cluster_ys(geom_ys, gap=max(450.0, 0.75 * depth_mm))
    if clusters:
        def _score(c: List[float]) -> float:
            med = statistics.median(c)
            # Prefer cluster near annotation median; slight preference for denser
            return abs(med - target) - 0.01 * len(c)

        best = min(clusters, key=_score)
        best_med = statistics.median(best)
        # Absorb sibling bar stacks on the same side of the mark as the
        # winning cluster (stacked neighbour rows sit on the opposite side).
        absorb: List[float] = list(best)
        for y in geom_ys:
            if abs(y - target) > 2.4 * depth_mm and abs(y - best_med) > 1.6 * depth_mm:
                continue
            same_side = (y - axis_y) * (best_med - axis_y) >= 0
            near_best = abs(y - best_med) <= 1.6 * depth_mm
            if same_side or near_best:
                absorb.append(y)
        pad = 60.0
        y0, y1 = min(absorb) - pad, max(absorb) + pad
        # Expand toward annotations that sit just outside the bar stack
        for ay in ann_ys:
            if abs(ay - best_med) <= 1.6 * depth_mm or (
                (ay - axis_y) * (best_med - axis_y) >= 0
                and abs(ay - target) <= 2.0 * depth_mm
            ):
                y0 = min(y0, ay - 40.0)
                y1 = max(y1, ay + 40.0)
        # Never cross the mark into the opposite neighbour row by more than
        # a small pad — mark sits in the whitespace between stacked beams.
        if best_med >= axis_y:
            y0 = max(y0, axis_y - 80.0)
        else:
            y1 = min(y1, axis_y + 80.0)
        reason = "annotation_nearest_geometry_cluster"
    elif outline_y and len(outline_y) >= 2:
        # Fall back: choose the outline half closest to annotations
        o0, o1 = float(min(outline_y)), float(max(outline_y))
        mid = 0.5 * (o0 + o1)
        if target >= mid:
            y0, y1 = mid - 40.0, o1 + 40.0
        else:
            y0, y1 = o0 - 40.0, mid + 40.0
        reason = "outline_half_near_annotations"
    else:
        half = BODY_HALF_DEPTH_FACTOR * depth_mm
        y0, y1 = target - half, target + half
        reason = "annotation_median_depth_band"

    y0 = max(y0, env[1] - 40.0)
    y1 = min(y1, env[3] + 40.0)
    if y1 <= y0:
        y0, y1 = env[1], env[3]
        reason = "envelope_fallback"
    return y0, y1, reason


def _build_beam_context(
    beam_id: str,
    envelope: Dict[str, Any],
    annotations: List[Dict[str, Any]],
    physical_bars: List[Dict[str, Any]],
    leaders: List[Dict[str, Any]],
    depth_mm: float,
    entities: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    ext = envelope.get("extent") or [
        envelope.get("xmin"),
        envelope.get("ymin"),
        envelope.get("xmax"),
        envelope.get("ymax"),
    ]
    env = (float(ext[0]), float(ext[1]), float(ext[2]), float(ext[3]))
    axis = envelope.get("axis") or {}
    axis_y = float(axis.get("mark_y") or axis.get("centroid_y") or (env[1] + env[3]) / 2)
    axis_x0 = float(axis.get("dxf_start_x") or env[0])
    axis_x1 = float(axis.get("dxf_end_x") or env[2])

    ann_pts = []
    for a in annotations:
        try:
            ann_pts.append((float(a["x"]), float(a["y"]), str(a.get("clean_text") or "")))
        except Exception:
            continue

    outline_y = (envelope.get("meta") or {}).get("outline_y_mm")
    body_y0, body_y1, body_reason = _resolve_body_band(
        env, axis_y, depth_mm, ann_pts, entities, outline_y
    )
    body_mid = 0.5 * (body_y0 + body_y1)

    # Bar Y bands from physical bars inside the resolved body band
    bar_ys_top: List[float] = []
    bar_ys_bot: List[float] = []
    body_bars: List[Dict[str, Any]] = []
    for b in physical_bars:
        try:
            y = float(b["y_position"])
            sx, ex = float(b["start_x"]), float(b["end_x"])
        except Exception:
            continue
        mid = 0.5 * (sx + ex)
        if mid < env[0] - 200 or mid > env[2] + 200:
            continue
        if y < body_y0 - 40 or y > body_y1 + 40:
            continue
        body_bars.append(b)
        place = str(b.get("vertical_placement") or "")
        if place == "TOP_FACE" or y >= body_mid:
            bar_ys_top.append(y)
        if place == "BOTTOM_FACE" or y < body_mid:
            bar_ys_bot.append(y)

    if bar_ys_top:
        top_band = (min(bar_ys_top) - 40.0, max(bar_ys_top) + 40.0)
    else:
        top_band = (body_mid + 0.05 * depth_mm, body_y1 + 20.0)
    if bar_ys_bot:
        bot_band = (min(bar_ys_bot) - 40.0, max(bar_ys_bot) + 40.0)
    else:
        bot_band = (body_y0 - 20.0, body_mid - 0.05 * depth_mm)

    stirrup_bands = (envelope.get("meta") or {}).get("stirrup_bands_mm") or []
    # Keep stirrup bands that overlap the body (reject neighbour-row bands)
    stir_keep = []
    for a, b in stirrup_bands:
        lo, hi = float(a), float(b)
        if _overlap_1d(lo, hi, body_y0 - 80, body_y1 + 80) > 0:
            stir_keep.append((lo, hi))

    leader_pts = []
    for L in leaders:
        try:
            tip_y = float(L["tip_y"])
            tail_y = float(L["tail_y"])
        except Exception:
            continue
        # Prefer leaders whose tip/tail lies near the body band
        if not (
            body_y0 - 120 <= tip_y <= body_y1 + 120
            or body_y0 - 120 <= tail_y <= body_y1 + 120
        ):
            if str(L.get("beam_id") or "") != beam_id:
                continue
        try:
            leader_pts.append((float(L["tip_x"]), tip_y, str(L.get("leader_id"))))
            leader_pts.append((float(L["tail_x"]), tail_y, str(L.get("leader_id"))))
        except Exception:
            continue

    return {
        "beam_id": beam_id,
        "env": env,
        "env_expanded": (
            env[0] - ENVELOPE_EXPAND_MM,
            env[1] - ENVELOPE_EXPAND_MM,
            env[2] + ENVELOPE_EXPAND_MM,
            env[3] + ENVELOPE_EXPAND_MM,
        ),
        "axis_y": axis_y,
        "axis_x0": axis_x0,
        "axis_x1": axis_x1,
        "depth_mm": depth_mm,
        "body_y0": body_y0,
        "body_y1": body_y1,
        "body_mid": body_mid,
        "body_reason": body_reason,
        "top_band": top_band,
        "bot_band": bot_band,
        "stirrup_bands": stir_keep,
        "ann_pts": ann_pts,
        "leader_pts": leader_pts,
        "physical_bars": body_bars,
    }


def score_entity_for_beam(
    ent: Dict[str, Any],
    ctx: Dict[str, Any],
) -> Dict[str, Any]:
    """Return ownership record for one entity vs one beam (not yet exclusive)."""
    beam_id = ctx["beam_id"]
    env = ctx["env"]
    env_x = ctx["env_expanded"]
    axis_y = ctx["axis_y"]
    depth = ctx["depth_mm"]
    dtype = ent.get("entity_type") or ""
    bb = ent.get("bounding_box")
    cent = ent.get("centroid")
    layer = ent.get("layer") or ""
    lf = _layer_flags(layer)

    evidence: Dict[str, Any] = {**lf}
    reasons: List[str] = []
    score = 0.0

    # --- Far reject ---
    if not bb:
        return {
            "handle": ent["entity_handle"],
            "type": dtype,
            "ownership": OWNERSHIP_NONE,
            "role": "UNKNOWN",
            "confidence_score": 0.0,
            "reasons": ["no_bounding_box"],
            "evidence": evidence,
            "beam_id": beam_id,
        }

    # Quick reject if completely outside expanded envelope
    if bb[2] < env_x[0] or bb[0] > env_x[2] or bb[3] < env_x[1] or bb[1] > env_x[3]:
        return {
            "handle": ent["entity_handle"],
            "type": dtype,
            "ownership": OWNERSHIP_NONE,
            "role": "UNKNOWN",
            "confidence_score": 0.0,
            "reasons": ["outside_expanded_envelope"],
            "evidence": evidence,
            "beam_id": beam_id,
        }

    overlap = _bbox_overlap_pct(bb, env)
    seg_ov = _segment_env_overlap_pct(ent, env)
    if seg_ov is not None:
        # Prefer segment overlap for LINE geometry (handles multi-beam spans)
        overlap = max(overlap, seg_ov)
        evidence["segment_overlap_pct"] = round(seg_ov, 4)
    evidence["overlap_pct"] = round(overlap, 4)
    evidence["inside_envelope"] = overlap >= 0.85
    evidence["mostly_inside_envelope"] = overlap >= 0.45
    # Beam-window X overlap for long shared bars: portion of entity X in env
    x_span = max(bb[2] - bb[0], 1e-6)
    x_ov = _overlap_1d(bb[0], bb[2], env[0], env[2]) / x_span
    evidence["x_overlap_pct"] = round(x_ov, 4)
    cx = cent[0] if cent else 0.5 * (bb[0] + bb[2])
    cy = cent[1] if cent else 0.5 * (bb[1] + bb[3])
    # For long horizontal bars, use Y of the segment (more stable than bbox mid)
    if ent.get("start_point") and ent.get("end_point"):
        cy = 0.5 * (ent["start_point"][1] + ent["end_point"][1])
        cx_clip = min(max(cx, env[0]), env[2])
        cx = cx_clip
    body_y0, body_y1 = ctx["body_y0"], ctx["body_y1"]
    body_mid = ctx.get("body_mid", 0.5 * (body_y0 + body_y1))
    d_axis = _dist_point_to_axis_y(cy, body_mid)
    evidence["distance_to_axis_mm"] = round(d_axis, 2)
    evidence["near_axis"] = d_axis <= 1.2 * depth
    evidence["inside_beam_body"] = body_y0 <= cy <= body_y1
    evidence["body_reason"] = ctx.get("body_reason")

    if evidence["inside_envelope"] and evidence["inside_beam_body"]:
        score += 0.35
        reasons.append("inside_envelope")
    elif evidence["mostly_inside_envelope"] and evidence["inside_beam_body"]:
        score += 0.20
        reasons.append(f"overlap_pct={overlap:.2f}")
    elif x_ov >= 0.15 and evidence["inside_beam_body"]:
        # Long bar crossing this beam's X window inside the body band
        score += 0.25
        reasons.append(f"beam_window_x_overlap={x_ov:.2f}")
        evidence["mostly_inside_envelope"] = True
    elif evidence["inside_envelope"] and not evidence["inside_beam_body"]:
        # Inside tall crop envelope but outside beam body → neighbour risk
        score += 0.05
        reasons.append("in_envelope_outside_body")
    else:
        score += 0.05 * overlap
        reasons.append(f"weak_overlap={overlap:.2f}")

    if evidence["near_axis"]:
        score += 0.15
        reasons.append(f"distance_to_axis={d_axis:.1f}mm")

    # Orientation
    slope = _line_slope(ent) if dtype in ("LINE", "LWPOLYLINE") else None
    if slope is not None:
        evidence["parallel_to_axis"] = slope <= AXIS_PARALLEL_SLOPE
        evidence["perpendicular_to_axis"] = slope >= AXIS_PERP_MIN_SLOPE or slope == float(
            "inf"
        )
        if evidence["parallel_to_axis"]:
            score += 0.20
            reasons.append("parallel_to_axis")
        if evidence["perpendicular_to_axis"] and _point_in_env(cx, cy, env):
            length = float(ent.get("length") or 0)
            if 15 <= length <= 1.5 * depth:
                score += 0.18
                reasons.append("short_vertical_in_envelope")
            elif length > 1.5 * depth:
                # tall vertical — support/column; keep only if near support X ends
                near_end = min(abs(cx - ctx["axis_x0"]), abs(cx - ctx["axis_x1"])) < 250
                if near_end:
                    score += 0.12
                    reasons.append("support_line_at_end")
                else:
                    score -= 0.10
                    reasons.append("tall_vertical_not_at_support")

    # Bar bands
    tb, bbnd = ctx["top_band"], ctx["bot_band"]
    evidence["inside_top_bar_band"] = tb[0] <= cy <= tb[1]
    evidence["inside_bottom_bar_band"] = bbnd[0] <= cy <= bbnd[1]
    if evidence["inside_top_bar_band"] and evidence.get("parallel_to_axis"):
        score += 0.15
        reasons.append("inside_top_bar_band")
    if evidence["inside_bottom_bar_band"] and evidence.get("parallel_to_axis"):
        score += 0.15
        reasons.append("inside_bottom_bar_band")

    # Stirrup bands
    in_stir = False
    for lo, hi in ctx["stirrup_bands"]:
        if lo - 50 <= cy <= hi + 50 and env[0] <= cx <= env[2]:
            in_stir = True
            break
    evidence["inside_stirrup_band"] = in_stir
    if in_stir and dtype in ("LINE", "DIMENSION", "LWPOLYLINE"):
        score += 0.12
        reasons.append("inside_stirrup_band")

    # Layer bonuses
    if lf["layer_reinf"] and evidence["mostly_inside_envelope"]:
        score += 0.10
        reasons.append("layer_reinf")
    if lf["layer_stirup"] and evidence["mostly_inside_envelope"]:
        score += 0.12
        reasons.append("layer_stirup")

    # Annotation reference (TEXT/MTEXT near this beam's R.1 anchors)
    text = ent.get("text") or ent.get("dimension_text") or ""
    ann_hit = False
    if dtype in ("TEXT", "MTEXT", "ATTRIB") and ent.get("start_point"):
        sx, sy = ent["start_point"]
        for ax, ay, atxt in ctx["ann_pts"]:
            if math.hypot(sx - ax, sy - ay) <= ANN_MATCH_TOL_MM:
                ann_hit = True
                reasons.append("annotation_anchor_match")
                break
            if atxt and text and atxt[:20] in text:
                if abs(sy - ay) < 400 and env[0] <= sx <= env[2]:
                    ann_hit = True
                    reasons.append("annotation_text_match")
                    break
        # Beam mark for this beam
        if re.search(rf"\b{re.escape(beam_id)}\s*\(", text.replace("%%U", ""), re.I):
            if abs(sy - axis_y) < 2.5 * depth and env[0] - 200 <= sx <= env[2] + 200:
                ann_hit = True
                score += 0.25
                reasons.append("beam_mark_text")
    evidence["annotation_reference"] = ann_hit
    if ann_hit:
        score += 0.30
        reasons.append("annotation_reference")

    # Leader attachment
    leader_hit = False
    if dtype == "LEADER" and ent.get("start_point"):
        tip = ent["start_point"]
        if _point_in_env(tip[0], tip[1], env_x):
            leader_hit = True
            score += 0.25
            reasons.append("leader_tip_in_envelope")
    for lx, ly, _lid in ctx["leader_pts"]:
        if cent and math.hypot(cent[0] - lx, cent[1] - ly) <= LEADER_MATCH_TOL_MM:
            leader_hit = True
            score += 0.10
            reasons.append("near_beam_leader")
            break
    evidence["attached_to_leader"] = leader_hit

    # Physical bar coordinate match
    bar_hit = False
    if dtype in ("LINE", "LWPOLYLINE") and ent.get("start_point") and ent.get("end_point"):
        sx, sy = ent["start_point"]
        ex, ey = ent["end_point"]
        ymid = 0.5 * (sy + ey)
        x0, x1 = min(sx, ex), max(sx, ex)
        for b in ctx["physical_bars"]:
            try:
                by = float(b["y_position"])
                bx0, bx1 = float(b["start_x"]), float(b["end_x"])
            except Exception:
                continue
            if abs(ymid - by) <= BAR_MATCH_TOL_MM and _overlap_1d(x0, x1, bx0, bx1) > 100:
                if env[0] - 100 <= 0.5 * (bx0 + bx1) <= env[2] + 100:
                    bar_hit = True
                    score += 0.20
                    reasons.append("physical_bar_match")
                    break
    evidence["physical_bar_match"] = bar_hit

    # DIMENSION inside envelope
    if dtype == "DIMENSION" and evidence["mostly_inside_envelope"]:
        score += 0.15
        reasons.append("dimension_in_envelope")

    # INSERT: only if insertion point inside envelope
    if dtype == "INSERT" and ent.get("start_point"):
        if _point_in_env(ent["start_point"][0], ent["start_point"][1], env):
            score += 0.20
            reasons.append("insert_point_in_envelope")
        else:
            score -= 0.20
            reasons.append("insert_point_outside_envelope")

    # Clamp / classify
    score = max(0.0, min(1.0, score))
    # Deterministic HIGH promotions for clear engineering geometry
    promote_reinf_bar = (
        dtype in ("LINE", "LWPOLYLINE")
        and evidence.get("parallel_to_axis")
        and (lf["layer_reinf"] or bar_hit)
        and evidence.get("inside_beam_body")
        and x_ov >= 0.12
    )
    promote_short_tick = (
        dtype in ("LINE", "LWPOLYLINE")
        and evidence.get("perpendicular_to_axis")
        and evidence.get("mostly_inside_envelope")
        and evidence.get("inside_beam_body")
        and 15 <= float(ent.get("length") or 0) <= 1.5 * depth
    )
    if score >= 0.55 and evidence.get("mostly_inside_envelope"):
        ownership = OWNERSHIP_HIGH
    elif score >= 0.55 and ann_hit:
        ownership = OWNERSHIP_HIGH
    elif promote_reinf_bar and score >= 0.40:
        ownership = OWNERSHIP_HIGH
        reasons.append("promote_reinf_bar_in_beam_window")
        score = max(score, 0.70)
    elif promote_short_tick and score >= 0.35:
        ownership = OWNERSHIP_HIGH
        reasons.append("promote_short_tick_in_envelope")
        score = max(score, 0.65)
    elif score >= 0.40:
        ownership = OWNERSHIP_MEDIUM
    elif score >= 0.20:
        ownership = OWNERSHIP_LOW
    else:
        ownership = OWNERSHIP_NONE

    # Hard veto: entity mostly outside and no annotation/leader/bar hit
    # Use segment/x-window evidence so long shared bars are not vetoed.
    if (
        overlap < 0.12
        and x_ov < 0.12
        and not ann_hit
        and not leader_hit
        and not bar_hit
        and not promote_reinf_bar
    ):
        ownership = OWNERSHIP_NONE
        reasons.append("veto_outside_no_anchor")

    # Neighbour-body veto: geometry whose Y is outside the beam body band
    # cannot be HIGH (annotations / beam marks near axis are exempt).
    if (
        ownership == OWNERSHIP_HIGH
        and dtype in ("LINE", "LWPOLYLINE", "ARC", "CIRCLE", "SPLINE", "INSERT")
        and not evidence.get("inside_beam_body")
        and not ann_hit
    ):
        ownership = OWNERSHIP_NONE
        reasons.append("veto_outside_beam_body")

    # Leaders / dims whose tip/centroid is far from the body: demote
    if (
        ownership in (OWNERSHIP_HIGH, OWNERSHIP_MEDIUM)
        and dtype in ("LEADER",)
        and not evidence.get("inside_beam_body")
        and d_axis > 2.0 * depth
    ):
        ownership = OWNERSHIP_LOW
        reasons.append("demote_leader_far_from_body")

    role = _role_guess(ent, evidence, axis_y)
    return {
        "handle": ent["entity_handle"],
        "type": dtype,
        "ownership": ownership,
        "role": role,
        "confidence_score": round(score, 3),
        "reasons": reasons,
        "evidence": {k: v for k, v in evidence.items() if not isinstance(v, float) or True},
        "beam_id": beam_id,
        "layer": layer,
    }


def resolve_ownership(
    inventory: Dict[str, Any],
    envelopes_by_beam: Dict[str, Dict[str, Any]],
    annotations_by_beam: Dict[str, List[Dict[str, Any]]],
    physical_bars: List[Dict[str, Any]],
    leaders: List[Dict[str, Any]],
    geometries_by_beam: Optional[Dict[str, Dict[str, Any]]] = None,
    beam_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Score every entity against every beam independently.

    An entity handle may appear under multiple beams when segment/window
    evidence independently qualifies (shared long bars spanning several
    beam windows). Within a single beam list each handle appears once.
    Competing annotations/leaders that are HIGH for only one beam remain
    single-owned via scoring, not via forced exclusivity that would strip
    shared reinf geometry from neighbouring renders.
    """
    geometries_by_beam = geometries_by_beam or {}
    entities = inventory.get("entities") or []
    ids = beam_ids or [
        b
        for b, e in envelopes_by_beam.items()
        if e.get("extent") or (e.get("xmin") is not None)
    ]

    contexts = {}
    for bid in ids:
        env = envelopes_by_beam.get(bid) or {}
        if not env.get("extent") and env.get("xmin") is None:
            continue
        depth = float(
            env.get("depth_mm")
            or (geometries_by_beam.get(bid) or {}).get("depth_mm")
            or 600.0
        )
        contexts[bid] = _build_beam_context(
            bid,
            env,
            annotations_by_beam.get(bid) or [],
            physical_bars,
            leaders,
            depth,
            entities=entities,
        )

    by_beam: Dict[str, List[Dict[str, Any]]] = {bid: [] for bid in contexts}
    # Track primary (highest-score) beam per handle for diagnostics
    primary: Dict[str, Dict[str, Any]] = {}
    seen_handles = set()
    unowned = 0

    for ent in entities:
        handle = str(ent["entity_handle"]).upper()
        seen_handles.add(handle)
        best_rec = None
        any_owned = False
        for bid, ctx in contexts.items():
            rec = score_entity_for_beam(ent, ctx)
            if best_rec is None or rec["confidence_score"] > best_rec["confidence_score"]:
                best_rec = rec
            if rec["ownership"] == OWNERSHIP_NONE:
                continue
            any_owned = True
            by_beam[bid].append(
                {
                    "handle": rec["handle"],
                    "type": rec["type"],
                    "ownership": rec["ownership"],
                    "role": rec["role"],
                    "confidence_score": rec["confidence_score"],
                    "reasons": rec["reasons"],
                    "layer": rec.get("layer"),
                }
            )
        if best_rec is not None:
            primary[handle] = {
                "beam_id": best_rec["beam_id"],
                "ownership": best_rec["ownership"],
                "confidence_score": best_rec["confidence_score"],
            }
        if not any_owned:
            unowned += 1

    for bid in by_beam:
        # Deduplicate handle within beam (keep highest score)
        best_h: Dict[str, Dict[str, Any]] = {}
        for r in by_beam[bid]:
            h = r["handle"]
            if h not in best_h or r["confidence_score"] > best_h[h]["confidence_score"]:
                best_h[h] = r
        by_beam[bid] = sorted(
            best_h.values(), key=lambda r: (-r["confidence_score"], r["handle"])
        )

    return {
        "phase_id": "T1.6",
        "model_version": MODEL_VERSION,
        "beam_count": len(by_beam),
        "entities_scanned": len(entities),
        "entities_unowned": unowned,
        "by_beam": by_beam,
        "primary_owner": primary,
        "assignment_policy": "independent_per_beam_deduped; shared geometry may multi-own",
        "render_policy": "ownership==HIGH only",
    }


def high_handles_for_beam(ownership: Dict[str, Any], beam_id: str) -> List[str]:
    rows = (ownership.get("by_beam") or {}).get(beam_id) or []
    return [r["handle"] for r in rows if r.get("ownership") == OWNERSHIP_HIGH]
