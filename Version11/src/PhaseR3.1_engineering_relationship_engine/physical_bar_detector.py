"""
physical_bar_detector.py — Detect physical reinforcement bars from DXF geometry.
MODEL_VERSION: 8.1.0

Physical bars in engineering drawings appear as:
  - Horizontal LINE entities on '-STR-REINF' or 'rein' layers
  - Horizontal LWPOLYLINE entities on reinforcement layers

Verified from drawing analysis:
  - Leader TIP connects to horizontal LINE with distance=0 (exact match)
  - Bars run along x-axis with y=constant (within HORIZONTAL_SLOPE tolerance)
  - Bars lengths range from a few hundred mm to full-span (~8000mm+)

Bar vertical placement (geometry-only, not intent):
  - y_position > beam centroid_y + fraction*depth → TOP_FACE
  - y_position < beam centroid_y - fraction*depth → BOTTOM_FACE
  - else → UNKNOWN

Does NOT classify bars as TOP_MAIN, BOTTOM_MAIN, etc.
"""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from . import HORIZONTAL_LINE_MAX_SLOPE, MIN_BAR_LENGTH_MM, LAYER_REINF, LAYER_REINF2
from .relationship_models import (
    CONF_HIGH, CONF_MEDIUM, CONF_LOW,
    PhysicalBar,
    PLACEMENT_TOP, PLACEMENT_BOTTOM, PLACEMENT_SIDE, PLACEMENT_UNKNOWN,
)


def _euclidean(p1: Tuple, p2: Tuple) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def _pt_to_segment_dist(px, py, x1, y1, x2, y2) -> float:
    """Perpendicular distance from point to finite line segment."""
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return _euclidean((px, py), (x1, y1))
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    nx = x1 + t * dx
    ny = y1 + t * dy
    return _euclidean((px, py), (nx, ny))


class PhysicalBarDetector:
    """
    Detect horizontal reinforcement bar entities from DXF modelspace.
    Assigns each bar to a beam by spatial overlap.
    """

    REINF_LAYERS = {LAYER_REINF, LAYER_REINF2}

    def detect(
        self,
        msp,
        beam_axes:  Dict[str, Any],   # beam_id → BeamAxis dict
        beam_centroids: Dict[str, Tuple], # beam_id → (centroid_x, centroid_y)
        beam_depths:    Dict[str, float], # beam_id → depth_mm
    ) -> List[PhysicalBar]:
        bars: List[PhysicalBar] = []

        # ── Horizontal LINE entities on reinforcement layers ──────────────────
        for entity in msp:
            if entity.dxftype() == "LINE" and entity.dxf.layer in self.REINF_LAYERS:
                bar = self._from_line(entity, beam_axes, beam_centroids, beam_depths)
                if bar:
                    bars.append(bar)

        # ── LWPOLYLINE entities on reinforcement layers ───────────────────────
        for entity in msp:
            if entity.dxftype() == "LWPOLYLINE" and entity.dxf.layer in self.REINF_LAYERS:
                bar = self._from_lwpolyline(entity, beam_axes, beam_centroids, beam_depths)
                if bar:
                    bars.append(bar)

        return bars

    def _from_line(self, entity, beam_axes, centroids, depths) -> Optional[PhysicalBar]:
        s = entity.dxf.start
        e = entity.dxf.end
        sx, sy = float(s[0]), float(s[1])
        ex, ey = float(e[0]), float(e[1])

        length = _euclidean((sx, sy), (ex, ey))
        if length < MIN_BAR_LENGTH_MM:
            return None

        dy = abs(ey - sy)
        dx = abs(ex - sx)
        slope = dy / dx if dx > 1e-6 else float("inf")
        if slope > HORIZONTAL_LINE_MAX_SLOPE:
            return None  # not horizontal enough

        x1, x2 = min(sx, ex), max(sx, ex)
        y_pos   = (sy + ey) / 2.0

        beam_id, norm_start, norm_end, placement = self._assign_beam(
            x1, x2, y_pos, beam_axes, centroids, depths
        )
        if not beam_id:
            return None

        conf = CONF_HIGH if length > 500 else CONF_MEDIUM

        return PhysicalBar(
            bar_id             = f"BAR::{uuid.uuid4().hex[:8].upper()}",
            beam_id            = beam_id,
            entity_type        = "LINE",
            layer              = str(entity.dxf.layer),
            start_x            = round(x1, 2),
            end_x              = round(x2, 2),
            y_position         = round(y_pos, 2),
            bar_length_mm      = round(length, 2),
            vertical_placement = placement,
            normalized_start   = round(norm_start, 6),
            normalized_end     = round(norm_end, 6),
            bar_confidence     = conf,
        )

    def _from_lwpolyline(self, entity, beam_axes, centroids, depths) -> Optional[PhysicalBar]:
        pts = list(entity.get_points())
        if len(pts) < 2:
            return None

        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
        x1, x2 = min(xs), max(xs)
        y_pos   = sum(ys) / len(ys)

        dy = max(ys) - min(ys)
        dx = x2 - x1
        length = math.sqrt(dx * dx + dy * dy)
        if length < MIN_BAR_LENGTH_MM:
            return None

        slope = dy / dx if dx > 1e-6 else float("inf")
        if slope > HORIZONTAL_LINE_MAX_SLOPE:
            return None

        beam_id, norm_start, norm_end, placement = self._assign_beam(
            x1, x2, y_pos, beam_axes, centroids, depths
        )
        if not beam_id:
            return None

        return PhysicalBar(
            bar_id             = f"BAR::{uuid.uuid4().hex[:8].upper()}",
            beam_id            = beam_id,
            entity_type        = "LWPOLYLINE",
            layer              = str(entity.dxf.layer),
            start_x            = round(x1, 2),
            end_x              = round(x2, 2),
            y_position         = round(y_pos, 2),
            bar_length_mm      = round(length, 2),
            vertical_placement = placement,
            normalized_start   = round(norm_start, 6),
            normalized_end     = round(norm_end, 6),
            bar_confidence     = CONF_MEDIUM,
        )

    def _assign_beam(
        self, x1, x2, y_pos, beam_axes, centroids, depths
    ):
        """
        Assign bar to beam by checking if bar's x-range overlaps beam x-range.
        Returns (beam_id, norm_start, norm_end, placement) or (None, ...)
        """
        bar_cx = (x1 + x2) / 2.0
        best_bid    = None
        best_overlap= 0.0
        best_norm_start = 0.0
        best_norm_end   = 1.0
        best_placement  = PLACEMENT_UNKNOWN

        for bid, ax in beam_axes.items():
            beam_start = float(ax.get("dxf_start_x") or 0.0)
            beam_end   = float(ax.get("dxf_end_x")   or 0.0)
            span       = float(ax.get("beam_length_mm") or 1.0)
            cx         = float(ax.get("dxf_centroid_x") or 0.0)
            cy         = float(ax.get("dxf_centroid_y") or 0.0)

            if beam_start >= beam_end:
                continue

            # Overlap of bar x-range with beam x-range
            overlap_start = max(x1, beam_start)
            overlap_end   = min(x2, beam_end)
            overlap       = max(0.0, overlap_end - overlap_start)
            overlap_frac  = overlap / span if span > 0 else 0.0

            if overlap_frac < 0.05:
                continue

            if overlap_frac > best_overlap:
                best_overlap = overlap_frac
                best_bid     = bid
                norm_start   = max(0.0, (x1 - beam_start) / span)
                norm_end     = min(1.5, (x2 - beam_start) / span)   # allow slight overshoot
                best_norm_start = norm_start
                best_norm_end   = norm_end

                # Vertical placement relative to beam centroid_y
                depth = depths.get(bid, 750.0)
                if y_pos > cy + 0.2 * depth:
                    best_placement = PLACEMENT_TOP
                elif y_pos < cy - 0.2 * depth:
                    best_placement = PLACEMENT_BOTTOM
                else:
                    best_placement = PLACEMENT_UNKNOWN

        return best_bid, best_norm_start, best_norm_end, best_placement

    def nearest_bar_to_point(
        self,
        px: float, py: float,
        bars: List[PhysicalBar],
        max_dist: float,
    ) -> Optional[PhysicalBar]:
        """Find closest bar whose horizontal line passes within max_dist of point."""
        best_bar  = None
        best_dist = max_dist

        for bar in bars:
            d = _pt_to_segment_dist(
                px, py,
                bar.start_x, bar.y_position,
                bar.end_x,   bar.y_position,
            )
            if d < best_dist:
                best_dist = d
                best_bar  = bar

        return best_bar
