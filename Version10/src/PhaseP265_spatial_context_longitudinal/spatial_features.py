"""
Production-visible spatial feature extraction.

Uses BeamOwnership envelope + T18 BeamScoped annotation/leader/physical-bar
geometry. Does not invent coordinates. Missing geometry is marked unavailable.
Native DXF model-space millimetres are preserved (no silent unit conversion).
"""
from __future__ import annotations

import math
from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PhaseP263_longitudinal_aware_gate.longitudinal_coverage import (
    parse_longitudinal_annotation,
)

from .config import (
    CLEARANCE_RATIO,
    CLUSTER_GAP_RATIO,
    COORDINATE_SPACE,
    LEADER_TAIL_ASSOCIATION_MM,
    REPEAT_SEPARATION_RATIO,
    SAME_LOCATION_RATIO,
)


def _f(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _band(zone: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(zone, dict):
        return None
    y0 = _f(zone.get("y0"))
    y1 = _f(zone.get("y1"))
    if y0 is None or y1 is None:
        return None
    return (min(y0, y1), max(y0, y1))


def band_distance(y: Optional[float], zone: Any) -> Optional[float]:
    if y is None:
        return None
    b = _band(zone)
    if b is None:
        return None
    lo, hi = b
    if lo <= y <= hi:
        return 0.0
    return min(abs(y - lo), abs(y - hi))


def in_band(y: Optional[float], zone: Any) -> Optional[bool]:
    d = band_distance(y, zone)
    if d is None:
        return None
    return d == 0.0


def _bbox(extent: Any) -> Optional[Tuple[float, float, float, float]]:
    if not isinstance(extent, (list, tuple)) or len(extent) < 4:
        return None
    vals = [_f(v) for v in extent[:4]]
    if any(v is None for v in vals):
        return None
    x0, y0, x1, y1 = vals  # type: ignore[misc]
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _norm_text(text: Any) -> str:
    return "".join(str(text or "").split()).upper()


def _attrs(node: Dict[str, Any]) -> Dict[str, Any]:
    a = node.get("attributes")
    return a if isinstance(a, dict) else {}


def _nodes_of(scoped: Optional[Dict[str, Any]], ntype: str) -> List[Dict[str, Any]]:
    if not isinstance(scoped, dict):
        return []
    return [n for n in (scoped.get("nodes") or []) if isinstance(n, dict) and n.get("type") == ntype]


def _ann_xy(ann: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    return _f(ann.get("x")), _f(ann.get("y"))


def _point_dist(
    a: Tuple[Optional[float], Optional[float]],
    b: Tuple[Optional[float], Optional[float]],
) -> Optional[float]:
    if None in a or None in b:
        return None
    return math.hypot(a[0] - b[0], a[1] - b[1])  # type: ignore[operator]


def _stat(vals: Sequence[float]) -> Dict[str, Optional[float]]:
    if not vals:
        return {"min": None, "median": None, "max": None, "count": 0}
    return {
        "min": min(vals),
        "median": float(median(vals)),
        "max": max(vals),
        "count": len(vals),
    }


def _cluster_1d(values: List[float], gap: float) -> List[List[float]]:
    if not values:
        return []
    ordered = sorted(values)
    groups: List[List[float]] = [[ordered[0]]]
    for v in ordered[1:]:
        if v - groups[-1][-1] > gap:
            groups.append([v])
        else:
            groups[-1].append(v)
    return groups


def _associate_leader(
    ann_node: Dict[str, Any],
    xy: Tuple[Optional[float], Optional[float]],
    leaders: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    rels = ann_node.get("relationships") or []
    attached = [
        r.get("other_id")
        for r in rels
        if isinstance(r, dict) and r.get("type") == "ATTACHED_TO"
    ]
    for lid in attached:
        for n in leaders:
            if n.get("id") == lid:
                return n, "ATTACHED_TO"
    if xy[0] is None or xy[1] is None:
        return None, None
    best = None
    best_d = None
    for n in leaders:
        a = _attrs(n)
        d = _point_dist(xy, (_f(a.get("tail_x")), _f(a.get("tail_y"))))
        if d is None:
            continue
        if best_d is None or d < best_d:
            best_d = d
            best = n
    if best is None or best_d is None or best_d > LEADER_TAIL_ASSOCIATION_MM:
        return None, None
    return best, "NEAREST_TAIL"


def extract_spatial_features(
    *,
    rec: Dict[str, Any],
    scoped: Optional[Dict[str, Any]],
    production_features: Optional[Dict[str, Any]] = None,
    clearance_ratio: float = CLEARANCE_RATIO,
    repeat_ratio: float = REPEAT_SEPARATION_RATIO,
) -> Dict[str, Any]:
    feat = production_features or {}
    env = rec.get("envelope") if isinstance(rec.get("envelope"), dict) else {}
    crop = _bbox(env.get("crop_extent"))
    cl = env.get("centreline") if isinstance(env.get("centreline"), dict) else {}
    top_zone = env.get("top_reinforcement_zone")
    bot_zone = env.get("bottom_reinforcement_zone")
    depth = _f(env.get("depth_mm")) or _f(feat.get("depth_mm"))
    if depth is None or depth <= 0:
        depth = 600.0
        depth_source = "DEFAULT_600"
    else:
        depth_source = "ENVELOPE"
    clearance = clearance_ratio * depth
    repeat_sep = repeat_ratio * depth
    same_loc = SAME_LOCATION_RATIO * depth
    cluster_gap = CLUSTER_GAP_RATIO * depth

    scoped = scoped or {}
    scoped_anns = [a for a in (scoped.get("annotations") or []) if isinstance(a, dict)]
    leaders = _nodes_of(scoped, "Leader")
    bars = _nodes_of(scoped, "PhysicalBar")
    ann_nodes = {n.get("id"): n for n in _nodes_of(scoped, "Annotation")}

    accepted = rec.get("accepted_annotations") or []
    long_parsed: List[Dict[str, Any]] = []
    for a in accepted:
        row = parse_longitudinal_annotation(a if isinstance(a, dict) else {"text": str(a)})
        if row is not None:
            row["ann_id"] = (a.get("id") if isinstance(a, dict) else None)
            long_parsed.append(row)

    bar_pts: List[Dict[str, Any]] = []
    for b in bars:
        a = _attrs(b)
        y = _f(a.get("y_position"))
        x0 = _f(a.get("start_x"))
        x1 = _f(a.get("end_x"))
        xm = None if x0 is None or x1 is None else 0.5 * (x0 + x1)
        place = str(a.get("vertical_placement") or "UNKNOWN").upper()
        family = "TOP" if "TOP" in place else ("BOTTOM" if "BOTTOM" in place else "UNKNOWN")
        bar_pts.append(
            {
                "id": b.get("id"),
                "x": xm,
                "y": y,
                "family": family,
                "placement": place,
                "synthetic": bool(a.get("synthetic")),
            }
        )

    per_ann: List[Dict[str, Any]] = []
    for parsed in long_parsed:
        text = parsed.get("text")
        matches = [
            a
            for a in scoped_anns
            if a.get("id") == parsed.get("ann_id")
            or _norm_text(a.get("text")) == _norm_text(text)
        ]
        if not matches:
            per_ann.append(
                {
                    "text": text,
                    "quantity": parsed.get("quantity"),
                    "diameter_mm": parsed.get("diameter_mm"),
                    "role": parsed.get("role") or "UNKNOWN",
                    "geometry_available": False,
                    "x": None,
                    "y": None,
                    "unavailable": ["annotation_xy"],
                }
            )
            continue
        for ann in matches:
            x, y = _ann_xy(ann)
            node = ann_nodes.get(ann.get("id")) or {}
            attrs = _attrs(node)
            leader, assoc = _associate_leader(node, (x, y), leaders)
            la = _attrs(leader) if leader else {}
            tip = (_f(la.get("tip_x")), _f(la.get("tip_y")))
            tail = (_f(la.get("tail_x")), _f(la.get("tail_y")))
            tip_dir = la.get("tip_direction")
            d_all: List[float] = []
            d_top: List[float] = []
            d_bot: List[float] = []
            d_dia: List[float] = []
            nearest_bar = None
            for bp in bar_pts:
                d = _point_dist((x, y), (bp.get("x"), bp.get("y")))
                if d is None and y is not None and bp.get("y") is not None:
                    d = abs(y - float(bp["y"]))
                if d is None:
                    continue
                d_all.append(d)
                if bp["family"] == "TOP":
                    d_top.append(d)
                elif bp["family"] == "BOTTOM":
                    d_bot.append(d)
                if nearest_bar is None or d < nearest_bar["distance"]:
                    nearest_bar = {"id": bp["id"], "family": bp["family"], "distance": d}
            dx = dy = ndx = ndy = None
            if crop and x is not None and y is not None:
                cx = 0.5 * (crop[0] + crop[2])
                cy = 0.5 * (crop[1] + crop[3])
                dx = x - cx
                dy = y - cy
                w = crop[2] - crop[0] or 1.0
                h = crop[3] - crop[1] or 1.0
                ndx = dx / w
                ndy = dy / h
            cl_dy = None if y is None or _f(cl.get("y")) is None else y - float(cl["y"])
            unavailable: List[str] = []
            if x is None or y is None:
                unavailable.append("annotation_xy")
            if leader is None:
                unavailable.append("leader")
            if not bar_pts:
                unavailable.append("physical_bar")
            per_ann.append(
                {
                    "text": text,
                    "ann_id": ann.get("id"),
                    "quantity": parsed.get("quantity"),
                    "diameter_mm": parsed.get("diameter_mm"),
                    "role": parsed.get("role") or "UNKNOWN",
                    "geometry_available": x is not None and y is not None,
                    "coordinate_space": COORDINATE_SPACE,
                    "x": x,
                    "y": y,
                    "dx_from_crop_centre": dx,
                    "dy_from_crop_centre": dy,
                    "normalized_dx": ndx,
                    "normalized_dy": ndy,
                    "dy_from_centreline": cl_dy,
                    "position_zone": attrs.get("position_zone"),
                    "dist_top_zone": band_distance(y, top_zone),
                    "dist_bottom_zone": band_distance(y, bot_zone),
                    "in_top_zone": in_band(y, top_zone),
                    "in_bottom_zone": in_band(y, bot_zone),
                    "leader_association": assoc,
                    "leader_tip_direction": tip_dir,
                    "leader_tip_x": tip[0],
                    "leader_tip_y": tip[1],
                    "leader_tail_x": tail[0],
                    "leader_tail_y": tail[1],
                    "leader_length": _f(la.get("leader_length")),
                    "dist_tip_top_zone": band_distance(tip[1], top_zone),
                    "dist_tip_bottom_zone": band_distance(tip[1], bot_zone),
                    "tip_in_top_zone": in_band(tip[1], top_zone),
                    "tip_in_bottom_zone": in_band(tip[1], bot_zone),
                    "nearest_object_distance": min(d_all) if d_all else None,
                    "nearest_top_object_distance": min(d_top) if d_top else None,
                    "nearest_bottom_object_distance": min(d_bot) if d_bot else None,
                    "nearest_same_quantity_object_distance": None,
                    "object_distance_stats": _stat(d_all),
                    "nearest_bar": nearest_bar,
                    "unavailable": unavailable,
                }
            )

    xs_ys = [(r["x"], r["y"]) for r in per_ann if r.get("x") is not None and r.get("y") is not None]
    max_repeat_dy = 0.0
    max_repeat_dist = 0.0
    same_location_repeats = 0
    separate_repeats = 0
    for i, a in enumerate(per_ann):
        for b in per_ann[i + 1 :]:
            if _norm_text(a.get("text")) != _norm_text(b.get("text")):
                continue
            if a.get("y") is None or b.get("y") is None:
                continue
            dy = abs(float(a["y"]) - float(b["y"]))
            dist = _point_dist((a.get("x"), a.get("y")), (b.get("x"), b.get("y"))) or dy
            max_repeat_dy = max(max_repeat_dy, dy)
            max_repeat_dist = max(max_repeat_dist, dist)
            if dy <= same_loc:
                same_location_repeats += 1
            if dy >= repeat_sep:
                separate_repeats += 1

    bar_ys = [float(b["y"]) for b in bar_pts if b.get("y") is not None]
    bar_clusters = _cluster_1d(bar_ys, cluster_gap)
    ann_ys = [float(r["y"]) for r in per_ann if r.get("y") is not None]
    ann_clusters = _cluster_1d(ann_ys, cluster_gap)

    top_n = int(feat.get("long_top_object_count") or 0)
    bot_n = int(feat.get("long_bottom_object_count") or 0)
    populated = feat.get("populated_layer")
    if not populated:
        if (top_n > 0) != (bot_n > 0):
            populated = "TOP" if top_n else "BOTTOM"

    tip_layers: List[str] = []
    for r in per_ann:
        dt = r.get("dist_tip_top_zone")
        db = r.get("dist_tip_bottom_zone")
        if dt is None or db is None:
            continue
        if r.get("tip_in_top_zone") and (db is None or db >= clearance):
            tip_layers.append("TOP")
        elif r.get("tip_in_bottom_zone") and (dt is None or dt >= clearance):
            tip_layers.append("BOTTOM")
        elif r.get("tip_in_top_zone") or r.get("tip_in_bottom_zone"):
            tip_layers.append("BOUNDARY")
        elif dt < db:
            tip_layers.append("NEAR_TOP")
        else:
            tip_layers.append("NEAR_BOTTOM")

    return {
        "coordinate_space": COORDINATE_SPACE,
        "geometry_source": "T18_BEAMSCOPED_PLUS_OWNERSHIP_ENVELOPE",
        "depth_mm": depth,
        "depth_source": depth_source,
        "clearance_mm": clearance,
        "repeat_separation_mm": repeat_sep,
        "crop_extent": list(crop) if crop else None,
        "centreline": dict(cl) if cl else None,
        "top_zone_available": _band(top_zone) is not None,
        "bottom_zone_available": _band(bot_zone) is not None,
        "annotation_xy_count": len(xs_ys),
        "leader_count": len(leaders),
        "physical_bar_count": len(bar_pts),
        "physical_bar_top_count": sum(1 for b in bar_pts if b["family"] == "TOP"),
        "physical_bar_bottom_count": sum(1 for b in bar_pts if b["family"] == "BOTTOM"),
        "physical_bar_geometry_available": len(bar_pts) > 0,
        "leader_geometry_available": len(leaders) > 0,
        "annotation_xy_available": len(xs_ys) > 0,
        "envelope_available": bool(crop or top_zone or bot_zone),
        "populated_layer": populated,
        "long_annotation_count": len(long_parsed),
        "per_annotation": per_ann,
        "max_repeat_dy": max_repeat_dy,
        "max_repeat_distance": max_repeat_dist,
        "same_location_repeat_pairs": same_location_repeats,
        "separate_repeat_pairs": separate_repeats,
        "repeated_separate_location": separate_repeats > 0,
        "repeated_same_location": same_location_repeats > 0 and separate_repeats == 0,
        "physical_bar_cluster_count": len(bar_clusters),
        "annotation_cluster_count": len(ann_clusters),
        "annotation_cluster_separation": len(ann_clusters) >= 2,
        "tip_layer_votes": tip_layers,
        "min_object_distance": min(
            (r["nearest_object_distance"] for r in per_ann if r.get("nearest_object_distance") is not None),
            default=None,
        ),
        "unavailable_features": sorted(
            {
                u
                for r in per_ann
                for u in (r.get("unavailable") or [])
            }
            | (
                {"physical_bar"}
                if not bar_pts
                else set()
            )
            | ({"leader"} if not leaders else set())
            | ({"annotation_xy"} if not xs_ys else set())
        ),
    }


__all__ = ["band_distance", "extract_spatial_features", "in_band"]
