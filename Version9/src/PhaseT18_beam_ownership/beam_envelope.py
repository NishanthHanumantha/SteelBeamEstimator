"""
T1.8 — Deterministic Beam Ownership Envelope (not the crop window).
MODEL_VERSION: 9.5.0
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple

MODEL_VERSION = "9.5.0"

# Engineering constants (mm)
ANN_REACH_DEPTH_FACTOR = 4.0
SUPPORT_EXT_MM = 350.0
STIRRUP_BAND_PAD_MM = 120.0
WEB_FRAC = 0.35  # side-face near mid-depth of body


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


def build_beam_envelope(
    beam_id: str,
    geometry_envelope: Dict[str, Any],
    physical_bars: List[Dict[str, Any]],
    annotations: List[Dict[str, Any]],
    *,
    inventory_bar_ys: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Build the physical engineering ownership zone for a beam.

    Prefers reinforcement elevation on the annotation-facing side of the
    beam mark (stacked neighbour rows sit on the opposite side).
    """
    ext = geometry_envelope.get("extent") or [
        geometry_envelope.get("xmin"),
        geometry_envelope.get("ymin"),
        geometry_envelope.get("xmax"),
        geometry_envelope.get("ymax"),
    ]
    crop = (float(ext[0]), float(ext[1]), float(ext[2]), float(ext[3]))
    axis = geometry_envelope.get("axis") or {}
    mark_y = float(axis.get("mark_y") or axis.get("centroid_y") or (crop[1] + crop[3]) / 2)
    mark_x = float(axis.get("mark_x") or axis.get("centroid_x") or (crop[0] + crop[2]) / 2)
    x0 = float(axis.get("dxf_start_x") or crop[0])
    x1 = float(axis.get("dxf_end_x") or crop[2])
    depth = float(geometry_envelope.get("depth_mm") or 600.0)
    meta = geometry_envelope.get("meta") or {}
    outline = meta.get("outline_y_mm")
    stirrup_bands = [(float(a), float(b)) for a, b in (meta.get("stirrup_bands_mm") or [])]

    # Candidate bar elevations inside the crop X window
    bar_ys: List[float] = []
    for b in physical_bars:
        try:
            y = float(b["y_position"])
            sx, ex = float(b["start_x"]), float(b["end_x"])
        except Exception:
            continue
        mid = 0.5 * (sx + ex)
        if mid < crop[0] - 200 or mid > crop[2] + 200:
            continue
        if y < crop[1] - 100 or y > crop[3] + 100:
            continue
        bar_ys.append(y)
    for y in inventory_bar_ys or []:
        if crop[1] - 100 <= y <= crop[3] + 100:
            bar_ys.append(float(y))

    ann_ys = []
    for a in annotations:
        try:
            ay = float(a.get("y") if "y" in a else a["attributes"]["y"])
            ax = float(a.get("x") if "x" in a else a["attributes"]["x"])
        except Exception:
            continue
        if crop[0] - 400 <= ax <= crop[2] + 400:
            ann_ys.append(ay)

    # Target elevation: median annotation Y on denser side of mark, else mark
    above = [y for y in ann_ys if y >= mark_y]
    below = [y for y in ann_ys if y < mark_y]
    if len(above) >= len(below) and above:
        target = statistics.median(above)
        side = "ABOVE_MARK"
    elif below:
        target = statistics.median(below)
        side = "BELOW_MARK"
    else:
        target = mark_y
        side = "AT_MARK"

    clusters = _cluster_ys(bar_ys, gap=max(400.0, 0.7 * depth))
    if clusters:
        best = min(clusters, key=lambda c: abs(statistics.median(c) - target))
        best_med = statistics.median(best)
        absorb = list(best)
        for y in bar_ys:
            same_side = (y - mark_y) * (best_med - mark_y) >= 0
            near = abs(y - best_med) <= 1.8 * depth
            if same_side or near:
                if abs(y - target) <= 3.0 * depth or near:
                    absorb.append(y)
        body_y0, body_y1 = min(absorb) - 40.0, max(absorb) + 40.0
        # Do not cross the mark into the neighbour row
        if best_med >= mark_y:
            body_y0 = max(body_y0, mark_y - 60.0)
            side = "ABOVE_MARK"
        else:
            body_y1 = min(body_y1, mark_y + 60.0)
            side = "BELOW_MARK"
        body_reason = "annotation_nearest_bar_cluster"
    elif outline and len(outline) >= 2:
        o0, o1 = float(min(outline)), float(max(outline))
        mid = 0.5 * (o0 + o1)
        if target >= mid:
            body_y0, body_y1 = mid - 40.0, o1 + 40.0
            side = "ABOVE_MARK"
        else:
            body_y0, body_y1 = o0 - 40.0, mid + 40.0
            side = "BELOW_MARK"
        body_reason = "outline_half"
    else:
        half = 1.35 * depth
        body_y0, body_y1 = target - half, target + half
        body_reason = "annotation_median_depth"

    # Clamp lightly to crop (ownership envelope may be tighter than crop)
    body_y0 = max(body_y0, crop[1] - 50.0)
    body_y1 = min(body_y1, crop[3] + 50.0)
    body_mid = 0.5 * (body_y0 + body_y1)

    top_zone = (body_mid, body_y1 + 0.15 * depth)
    bot_zone = (body_y0 - 0.15 * depth, body_mid)
    # Annotation reach: same side of mark as body, up to ANN_REACH * depth beyond body
    reach = ANN_REACH_DEPTH_FACTOR * depth
    if side == "ABOVE_MARK":
        ann_y0 = mark_y - 80.0
        ann_y1 = body_y1 + reach
    elif side == "BELOW_MARK":
        ann_y0 = body_y0 - reach
        ann_y1 = mark_y + 80.0
    else:
        ann_y0 = body_y0 - reach
        ann_y1 = body_y1 + reach

    # Stirrup region: body + stirrup bands that overlap body
    stir_y0, stir_y1 = body_y0 - STIRRUP_BAND_PAD_MM, body_y1 + STIRRUP_BAND_PAD_MM
    for lo, hi in stirrup_bands:
        if max(lo, body_y0 - 200) <= min(hi, body_y1 + 200):
            # keep band only if on same side of mark as body
            bmid = 0.5 * (lo + hi)
            if side == "ABOVE_MARK" and bmid < mark_y - 200:
                continue
            if side == "BELOW_MARK" and bmid > mark_y + 200:
                continue
            stir_y0 = min(stir_y0, lo - STIRRUP_BAND_PAD_MM)
            stir_y1 = max(stir_y1, hi + STIRRUP_BAND_PAD_MM)

    web_half = WEB_FRAC * (body_y1 - body_y0)
    web_y0, web_y1 = body_mid - web_half, body_mid + web_half

    # Support extensions at span ends
    support_zones = [
        {
            "x0": x0 - SUPPORT_EXT_MM,
            "x1": x0 + SUPPORT_EXT_MM,
            "y0": body_y0 - 0.5 * depth,
            "y1": body_y1 + 0.5 * depth,
        },
        {
            "x0": x1 - SUPPORT_EXT_MM,
            "x1": x1 + SUPPORT_EXT_MM,
            "y0": body_y0 - 0.5 * depth,
            "y1": body_y1 + 0.5 * depth,
        },
    ]

    return {
        "beam_id": beam_id,
        "model_version": MODEL_VERSION,
        "crop_extent": list(crop),
        "centreline": {"x0": x0, "x1": x1, "y": mark_y, "mark_x": mark_x},
        "depth_mm": depth,
        "side_of_mark": side,
        "body_reason": body_reason,
        "concrete_envelope": {
            "x0": min(x0, crop[0]),
            "x1": max(x1, crop[2]),
            "y0": body_y0,
            "y1": body_y1,
        },
        "top_reinforcement_zone": {"y0": top_zone[0], "y1": top_zone[1]},
        "bottom_reinforcement_zone": {"y0": bot_zone[0], "y1": bot_zone[1]},
        "stirrup_region": {"y0": stir_y0, "y1": stir_y1},
        "side_face_web": {"y0": web_y0, "y1": web_y1},
        "annotation_reach": {"y0": ann_y0, "y1": ann_y1},
        "support_zones": support_zones,
        "development_length_extension": {
            "left": support_zones[0],
            "right": support_zones[1],
        },
    }


def point_in_y_band(y: float, y0: float, y1: float, pad: float = 0.0) -> bool:
    return (y0 - pad) <= y <= (y1 + pad)


def point_in_rect(x: float, y: float, r: Dict[str, float], pad: float = 0.0) -> bool:
    return (
        r["x0"] - pad <= x <= r["x1"] + pad
        and r["y0"] - pad <= y <= r["y1"] + pad
    )


def bar_in_envelope(bar_attrs: Dict[str, Any], envelope: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        y = float(bar_attrs["y_position"])
        sx, ex = float(bar_attrs["start_x"]), float(bar_attrs["end_x"])
    except Exception:
        return False, "bar_missing_geometry"
    ce = envelope["concrete_envelope"]
    # Continuous bars often span multiple beams — require X-range overlap
    # with this beam's envelope, not midpoint containment.
    bar_x0, bar_x1 = (sx, ex) if sx <= ex else (ex, sx)
    overlap = min(bar_x1, ce["x1"] + 150.0) - max(bar_x0, ce["x0"] - 150.0)
    if overlap < 80.0:
        return False, "bar_x_outside_envelope"
    if not point_in_y_band(y, ce["y0"], ce["y1"], pad=50.0):
        return False, "bar_y_outside_reinforcement_elevation"
    return True, "bar_inside_concrete_envelope"


def tip_in_envelope(
    tip_x: float, tip_y: float, envelope: Dict[str, Any]
) -> Tuple[bool, str]:
    ce = envelope["concrete_envelope"]
    if point_in_y_band(tip_y, ce["y0"], ce["y1"], pad=80.0) and (
        ce["x0"] - 200 <= tip_x <= ce["x1"] + 200
    ):
        return True, "tip_inside_concrete_envelope"
    for z in envelope.get("support_zones") or []:
        if point_in_rect(tip_x, tip_y, z, pad=40.0):
            return True, "tip_inside_support_extension"
    return False, "tip_outside_envelope_and_supports"
