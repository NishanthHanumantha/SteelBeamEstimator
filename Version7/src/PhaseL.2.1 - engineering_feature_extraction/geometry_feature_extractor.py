"""
Geometry Feature Extractor — extract physical shape properties.
Observations only. No semantic meaning assigned.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from engineering_feature_model import GeometryFeatures


class GeometryFeatureExtractor:
    """
    Extract geometry features from a bar record.

    Source: L.2 BeamReinforcementModel bars, V5 engineering objects.
    Strategy: derive from available data (length, extent, position_zone, continuity).
    """

    def extract(
        self,
        bar: Dict[str, Any],
        beam_model: Dict[str, Any],
        config: Dict[str, Any],
    ) -> GeometryFeatures:
        geom = beam_model.get("geometry") or {}
        span = geom.get("clear_span_mm")
        coverage = bar.get("coverage_ratio")
        extent = bar.get("extent") or ""
        orientation = bar.get("position_zone") or ""
        spacing = bar.get("spacing_mm")

        # Estimate bar length from coverage × span
        length_mm: Optional[float] = None
        if coverage is not None and span:
            length_mm = round(coverage * span, 1)

        # Derive start/end/midpoints (along beam axis) from extent type
        start_pt, end_pt, mid_pt = self._estimate_points(extent, span, length_mm)

        # Bounding box
        bbox = None
        if start_pt and end_pt:
            bbox = {
                "min_x": min(start_pt[0], end_pt[0]),
                "min_y": min(start_pt[1], end_pt[1]),
                "max_x": max(start_pt[0], end_pt[0]),
                "max_y": max(start_pt[1], end_pt[1]),
            }

        # Orientation angle (0° = horizontal longitudinal, 90° = vertical transverse)
        is_transverse = orientation in ("TRANSVERSE_ZONE", "TRANSVERSE")
        angle_deg = 90.0 if is_transverse else 0.0

        # Closed link / stirrup → is_closed
        is_closed = is_transverse
        is_curved = is_closed

        # Touches support if extent reaches support
        touches_support = (
            "SUPPORT" in extent.upper()
            or "FULL" in extent.upper()
            or (coverage is not None and coverage >= 0.8)
        )

        return GeometryFeatures(
            start_point=start_pt,
            end_point=end_pt,
            midpoint=mid_pt,
            length_mm=length_mm,
            projected_length_mm=length_mm,  # horizontal beam → projected = actual
            relative_length=coverage,
            bounding_box=bbox,
            orientation_angle_deg=angle_deg,
            is_polyline=is_transverse,   # stirrups are typically polylines
            is_line=not is_transverse,
            is_arc=False,
            is_closed=is_closed,
            is_curved=is_curved,
            crosses_beam_axis=is_transverse,
            touches_support=touches_support,
            touches_beam_edge=touches_support,
        )

    def _estimate_points(
        self,
        extent: str,
        span: Optional[float],
        length: Optional[float],
    ) -> Tuple[Optional[Tuple], Optional[Tuple], Optional[Tuple]]:
        if not span:
            return None, None, None
        ext = extent.upper()
        if "FULL" in ext:
            sx, ex = 0.0, span
        elif "LEFT_SUPPORT_ONLY" in ext:
            sx, ex = 0.0, (length or span * 0.25)
        elif "RIGHT_SUPPORT_ONLY" in ext:
            ex = span
            sx = ex - (length or span * 0.25)
        elif "BOTH_SUPPORTS" in ext or "SUPPORT_BOTH" in ext:
            # Appears at both supports — represent as two segments (use left here)
            sx, ex = 0.0, (length or span * 0.35)
        elif "MIDSPAN" in ext:
            mid = span / 2
            half = (length or span * 0.3) / 2
            sx, ex = mid - half, mid + half
        else:
            sx, ex = 0.0, (length or span)

        sx, ex = max(0.0, sx), min(span, ex)
        mid_x = (sx + ex) / 2
        y = 0.0  # beam centroid y (relative)
        return (sx, y), (ex, y), (mid_x, y)
