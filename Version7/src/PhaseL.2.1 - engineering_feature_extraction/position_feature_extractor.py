"""
Position Feature Extractor — where the bar sits within the beam cross-section.
Observations only. No semantic meaning assigned.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engineering_feature_model import (
    PositionFeatures,
    ZONE_TOP, ZONE_MIDDLE, ZONE_BOTTOM, ZONE_SIDE, ZONE_TRANSVERSE, ZONE_UNKNOWN,
)

# Mapping from L.2 position_zone to L.2.1 observation zone
_ZONE_MAP = {
    "TOP_ZONE": ZONE_TOP,
    "BOTTOM_ZONE": ZONE_BOTTOM,
    "SIDE_ZONE": ZONE_SIDE,
    "TRANSVERSE_ZONE": ZONE_TRANSVERSE,
    "UNKNOWN_ZONE": ZONE_UNKNOWN,
    "TOP": ZONE_TOP,
    "BOTTOM": ZONE_BOTTOM,
    "SIDE": ZONE_SIDE,
    "TRANSVERSE": ZONE_TRANSVERSE,
    "UNKNOWN": ZONE_UNKNOWN,
}

# Typical cover values (mm) — observational defaults
TOP_COVER = 25.0
BOTTOM_COVER = 25.0
SIDE_COVER = 25.0
BAR_DIAMETER_DEFAULT = 16.0  # used if diameter not known


class PositionFeatureExtractor:
    """Extract position features from a bar relative to its beam geometry."""

    def extract(
        self,
        bar: Dict[str, Any],
        beam_model: Dict[str, Any],
        all_bars_in_beam: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> PositionFeatures:
        geom = beam_model.get("geometry") or {}
        depth = geom.get("depth_mm") or 600.0
        width = geom.get("width_mm") or 200.0
        span = geom.get("clear_span_mm")

        top_cover = geom.get("top_cover_mm") or config.get("top_cover_mm", TOP_COVER)
        bottom_cover = geom.get("bottom_cover_mm") or config.get("bottom_cover_mm", BOTTOM_COVER)
        dia = float(bar.get("diameter_mm") or BAR_DIAMETER_DEFAULT)

        zone_raw = bar.get("position_zone") or ZONE_UNKNOWN
        zone = _ZONE_MAP.get(zone_raw, ZONE_UNKNOWN)

        # Estimate distance from faces based on zone
        if zone == ZONE_TOP:
            dist_from_top = top_cover + dia / 2
            dist_from_bottom = depth - dist_from_top
        elif zone == ZONE_BOTTOM:
            dist_from_bottom = bottom_cover + dia / 2
            dist_from_top = depth - dist_from_bottom
        elif zone == ZONE_SIDE:
            dist_from_top = depth / 2  # mid-height
            dist_from_bottom = depth / 2
        elif zone == ZONE_TRANSVERSE:
            dist_from_top = top_cover
            dist_from_bottom = bottom_cover
        else:
            dist_from_top = None
            dist_from_bottom = None

        # Beam depth ratio (0.0 = top, 1.0 = bottom)
        depth_ratio = None
        if dist_from_top is not None and depth > 0:
            depth_ratio = round(dist_from_top / depth, 3)

        # Horizontal position (coverage extent)
        coverage = bar.get("coverage_ratio") or 0.0
        dist_left = None
        dist_right = None
        ext = (bar.get("extent") or "").upper()
        if span:
            if "LEFT_SUPPORT_ONLY" in ext:
                dist_left = 0.0
                dist_right = span * (1 - coverage)
            elif "RIGHT_SUPPORT_ONLY" in ext:
                dist_right = 0.0
                dist_left = span * (1 - coverage)
            elif "FULL" in ext or "BOTH" in ext:
                dist_left = 0.0
                dist_right = 0.0
            else:
                dist_left = span * (1 - coverage) / 2
                dist_right = dist_left

        # Distance from beam centroid
        centroid_dist = None
        if dist_from_top is not None and depth > 0:
            centroid_dist = round(abs(dist_from_top - depth / 2), 1)

        # Vertical rank — sort bars in beam by zone (TOP=1, SIDE=2, BOTTOM=3, TRANSVERSE=4)
        zone_order = {ZONE_TOP: 1, ZONE_SIDE: 2, ZONE_MIDDLE: 3, ZONE_BOTTOM: 4, ZONE_TRANSVERSE: 5, ZONE_UNKNOWN: 6}
        v_rank = zone_order.get(zone, 6)

        return PositionFeatures(
            vertical_rank=v_rank,
            horizontal_rank=1,
            distance_from_top_face_mm=round(dist_from_top, 1) if dist_from_top is not None else None,
            distance_from_bottom_face_mm=round(dist_from_bottom, 1) if dist_from_bottom is not None else None,
            distance_from_left_support_mm=round(dist_left, 1) if dist_left is not None else None,
            distance_from_right_support_mm=round(dist_right, 1) if dist_right is not None else None,
            distance_from_centroid_mm=centroid_dist,
            beam_depth_ratio=depth_ratio,
            beam_width_ratio=None,
            position_zone=zone,
        )
