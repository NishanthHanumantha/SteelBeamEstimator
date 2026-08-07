"""
Read-only geometry helpers for ownership explainability.
MODEL_VERSION: 10.0.3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]


def as_bbox(extent: Any) -> Optional[BBox]:
    if not extent:
        return None
    if isinstance(extent, dict):
        try:
            return (
                float(extent.get("x0", extent.get("xmin"))),
                float(extent.get("y0", extent.get("ymin"))),
                float(extent.get("x1", extent.get("xmax"))),
                float(extent.get("y1", extent.get("ymax"))),
            )
        except Exception:
            return None
    if isinstance(extent, (list, tuple)) and len(extent) >= 4:
        try:
            x0, y0, x1, y1 = map(float, extent[:4])
            if x1 < x0:
                x0, x1 = x1, x0
            if y1 < y0:
                y0, y1 = y1, y0
            return (x0, y0, x1, y1)
        except Exception:
            return None
    return None


def point_in_bbox(pt: Optional[Point], bbox: Optional[BBox], pad: float = 0.0) -> bool:
    if not pt or not bbox:
        return False
    x, y = pt
    return (
        bbox[0] - pad <= x <= bbox[2] + pad
        and bbox[1] - pad <= y <= bbox[3] + pad
    )


def dist_to_bbox(pt: Optional[Point], bbox: Optional[BBox]) -> Optional[float]:
    if not pt or not bbox:
        return None
    x, y = pt
    dx = 0.0 if bbox[0] <= x <= bbox[2] else min(abs(x - bbox[0]), abs(x - bbox[2]))
    dy = 0.0 if bbox[1] <= y <= bbox[3] else min(abs(y - bbox[1]), abs(y - bbox[3]))
    if dx == 0.0 and dy == 0.0:
        return 0.0
    return round((dx * dx + dy * dy) ** 0.5, 3)


def envelope_search_bbox(envelope: Dict[str, Any]) -> Optional[BBox]:
    """Union of crop + annotation_reach + concrete as the ownership search envelope."""
    parts = [
        as_bbox(envelope.get("crop_extent")),
        as_bbox(envelope.get("annotation_reach")),
        as_bbox(envelope.get("concrete_envelope")),
    ]
    parts = [p for p in parts if p]
    if not parts:
        return None
    return (
        min(p[0] for p in parts),
        min(p[1] for p in parts),
        max(p[2] for p in parts),
        max(p[3] for p in parts),
    )


def entity_point(attrs: Dict[str, Any], ent_type: str = "") -> Optional[Point]:
    a = attrs or {}
    for kx, ky in (("x", "y"), ("tip_x", "tip_y"), ("cx", "cy")):
        if kx in a and ky in a:
            try:
                return (float(a[kx]), float(a[ky]))
            except Exception:
                pass
    if "start_x" in a and "y_position" in a:
        try:
            sx, ex = float(a["start_x"]), float(a.get("end_x", a["start_x"]))
            return (0.5 * (sx + ex), float(a["y_position"]))
        except Exception:
            pass
    if "extent" in a:
        bb = as_bbox(a["extent"])
        if bb:
            return ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0)
    return None


def axis_projection(
    pt: Optional[Point], centreline: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    if not pt or not centreline:
        return {"projection": None, "perpendicular_offset": None}
    try:
        x0 = float(centreline.get("x0"))
        x1 = float(centreline.get("x1"))
        y = float(centreline.get("y") or centreline.get("mark_y") or 0.0)
        # Horizontal beam axis approximation
        proj_x = min(max(pt[0], min(x0, x1)), max(x0, x1))
        perp = abs(pt[1] - y)
        along = proj_x - min(x0, x1)
        return {
            "projection": round(along, 3),
            "perpendicular_offset": round(perp, 3),
            "axis_y": y,
        }
    except Exception:
        return {"projection": None, "perpendicular_offset": None}


def score_breakdown_from_rules(
    accepted_rules: Optional[List[str]],
    rejected_rule: Optional[str],
    ownership_score: Optional[float],
) -> Dict[str, Any]:
    """
    Expose the EXISTING T1.8 scoring formula without inventing new logic:
      score = 0.0 if rejected else min(1.0, 0.55 + 0.05 * len(accepted_rules))
    """
    rules = list(accepted_rules or [])
    components = []
    if rejected_rule:
        components.append(
            {
                "name": "rejection",
                "raw_score": 0.0,
                "normalised_score": 0.0,
                "weight": 1.0,
                "contribution": 0.0,
                "detail": rejected_rule,
            }
        )
        total = 0.0
    else:
        components.append(
            {
                "name": "base_acceptance",
                "raw_score": 0.55,
                "normalised_score": 0.55,
                "weight": 1.0,
                "contribution": 0.55,
                "detail": "T18 score_from_rules base",
            }
        )
        for r in rules:
            components.append(
                {
                    "name": f"rule:{r}",
                    "raw_score": 0.05,
                    "normalised_score": 0.05,
                    "weight": 1.0,
                    "contribution": 0.05,
                    "detail": r,
                }
            )
        total = round(min(1.0, 0.55 + 0.05 * len(rules)), 3)
    persisted = ownership_score
    return {
        "components": components,
        "computed_total": total if rejected_rule else total,
        "persisted_ownership_score": persisted,
        "score_matches_persisted": (
            persisted is None or abs(float(persisted) - float(total if not rejected_rule else 0.0)) < 1e-6
        ),
        "formula": "0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)",
    }
