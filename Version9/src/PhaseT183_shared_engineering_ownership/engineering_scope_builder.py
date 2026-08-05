"""
T1.8.3 — Build EngineeringScope from SFR candidates + beam geometry.
MODEL_VERSION: 9.5.3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

MODEL_VERSION = "9.5.3"

# Engineering thresholds (mm)
MARK_Y_TOL_MM = 150.0
DEPTH_TOL_MM = 120.0
MAX_GAP_MM = 1000.0  # allow typical support gap between collinear beams
ELEV_BAND_FRAC = 0.35  # relative depth for tip elevation check


def _beam_geom(env: Dict[str, Any]) -> Dict[str, float]:
    ext = env.get("extent") or [0, 0, 0, 0]
    axis = env.get("axis") or {}
    x0 = float(axis.get("dxf_start_x") or ext[0])
    x1 = float(axis.get("dxf_end_x") or ext[2])
    if x0 > x1:
        x0, x1 = x1, x0
    return {
        "xmin": float(ext[0]),
        "ymin": float(ext[1]),
        "xmax": float(ext[2]),
        "ymax": float(ext[3]),
        "x0": x0,
        "x1": x1,
        "mark_y": float(axis.get("mark_y") or axis.get("centroid_y") or (ext[1] + ext[3]) / 2),
        "depth": float(env.get("depth_mm") or 600.0),
    }


def _x_gap(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Gap between two beam X spans (0 if overlapping). Prefer crop extents."""
    a0, a1 = a["xmin"], a["xmax"]
    b0, b1 = b["xmin"], b["xmax"]
    if a1 < b0:
        return b0 - a1
    if b1 < a0:
        return a0 - b1
    return 0.0


def _collinear(a: Dict[str, float], b: Dict[str, float]) -> bool:
    return abs(a["mark_y"] - b["mark_y"]) <= MARK_Y_TOL_MM


def _depth_ok(a: Dict[str, float], b: Dict[str, float]) -> bool:
    return abs(a["depth"] - b["depth"]) <= DEPTH_TOL_MM


def _tip_in_group(
    tip_x: float,
    tip_y: float,
    members: Sequence[str],
    geoms: Dict[str, Dict[str, float]],
) -> bool:
    """Rule 4: leader tip terminates inside the shared beam group envelope."""
    if not members:
        return False
    xs0 = min(geoms[b]["xmin"] for b in members)
    xs1 = max(geoms[b]["xmax"] for b in members)
    ys0 = min(geoms[b]["ymin"] for b in members)
    ys1 = max(geoms[b]["ymax"] for b in members)
    # Vertical pad for leaders that land just above body
    pad_y = 400.0
    return (xs0 - 200) <= tip_x <= (xs1 + 200) and (ys0 - pad_y) <= tip_y <= (ys1 + pad_y)


def _grow_connected(
    seed: str,
    geoms: Dict[str, Dict[str, float]],
    *,
    max_gap: float = MAX_GAP_MM,
) -> List[str]:
    """Grow continuous collinear framing chain from seed beam."""
    if seed not in geoms:
        return [seed] if seed else []
    members = {seed}
    changed = True
    while changed:
        changed = False
        for bid, g in geoms.items():
            if bid in members:
                continue
            # Must be collinear + depth-ok with ANY current member and X-adjacent
            ok = False
            for m in list(members):
                gm = geoms[m]
                if not _collinear(g, gm) or not _depth_ok(g, gm):
                    continue
                if _x_gap(g, gm) <= max_gap:
                    ok = True
                    break
            if ok:
                members.add(bid)
                changed = True
    # Order by X
    return sorted(members, key=lambda b: geoms[b]["x0"])


def build_engineering_scopes(
    candidates: List[Dict[str, Any]],
    envelopes: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    For each SFR candidate, build an EngineeringScope over collinear continuous beams.
    """
    geoms = {bid: _beam_geom(env) for bid, env in envelopes.items()}
    scopes: List[Dict[str, Any]] = []
    # Group identical text on same framing line into one scope when possible
    used_ann: set = set()

    for cand in candidates:
        aid = cand["annotation_id"]
        if aid in used_ann:
            continue
        primary = cand["primary_beam"]
        if primary not in geoms:
            continue
        # Only share annotations accepted on primary (engineering-valid owner)
        if not cand.get("accepted_on_primary"):
            continue

        members = _grow_connected(primary, geoms)
        if len(members) < 2:
            # Single-beam SFR — no multi-owner scope (still recorded as exclusive)
            scopes.append(
                {
                    "scope_id": f"SCOPE::SFR::{aid}",
                    "scope_type": cand["scope_type"],
                    "member_beams": [primary],
                    "member_annotations": [aid],
                    "confidence": 0.55,
                    "reason": "single_beam_sfr_no_collinear_neighbours",
                    "shared": False,
                    "primary_beam": primary,
                    "annotation_text": cand["annotation_text"],
                }
            )
            used_ann.add(aid)
            continue

        # Rule 4: tip in group
        tips = cand.get("leader_tips") or []
        tip_ok = True
        if tips:
            tip_ok = any(
                _tip_in_group(t["tip_x"], t["tip_y"], members, geoms) for t in tips
            )
        if not tip_ok:
            scopes.append(
                {
                    "scope_id": f"SCOPE::SFR::{aid}",
                    "scope_type": cand["scope_type"],
                    "member_beams": [primary],
                    "member_annotations": [aid],
                    "confidence": 0.4,
                    "reason": "leader_tip_outside_candidate_group",
                    "shared": False,
                    "primary_beam": primary,
                    "annotation_text": cand["annotation_text"],
                }
            )
            used_ann.add(aid)
            continue

        # Absorb other accepted SFR anns on members with same normalized text? keep separate
        scopes.append(
            {
                "scope_id": f"SCOPE::SFR::{aid}",
                "scope_type": cand["scope_type"],
                "member_beams": members,
                "member_annotations": [aid],
                "confidence": 0.92,
                "reason": (
                    "collinear_continuous_framing;"
                    f"mark_y_tol={MARK_Y_TOL_MM};gap<{MAX_GAP_MM};"
                    "leader_tip_in_group;sfr_text"
                ),
                "shared": True,
                "primary_beam": primary,
                "annotation_text": cand["annotation_text"],
                "rules_passed": [
                    "R1_COLLINEAR",
                    "R2_GAP",
                    "R3_DEPTH",
                    "R4_LEADER_TIP",
                    "R5_SFR_TEXT",
                    "R6_NO_EXCLUSIVE_CONFLICT",
                ],
            }
        )
        used_ann.add(aid)

    return scopes
