"""
geometry_models.py — Immutable geometry data models for Phase R.3.
MODEL_VERSION: 8.0.0

All models represent geometry evidence only.
No engineering intent is stored or implied.

Coordinate conventions:
  - DXF space: raw AutoCAD drawing coordinates (large float values)
  - Local space: beam-relative coordinates, start=0, end=beam_length_mm
  - Normalized: 0.0 (left end) → 1.0 (right end)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

# ── Extent evidence labels (observable position, NOT engineering intent) ──────
EXTENT_FULL_SPAN          = "FULL_SPAN"
EXTENT_LEFT_SUPPORT_ONLY  = "LEFT_SUPPORT_ONLY"
EXTENT_RIGHT_SUPPORT_ONLY = "RIGHT_SUPPORT_ONLY"
EXTENT_MIDSPAN_ONLY       = "MIDSPAN_ONLY"
EXTENT_LEFT_TRANSITION    = "LEFT_TRANSITION"
EXTENT_RIGHT_TRANSITION   = "RIGHT_TRANSITION"
EXTENT_UNKNOWN            = "UNKNOWN"

ALL_EXTENT_LABELS = {
    EXTENT_FULL_SPAN, EXTENT_LEFT_SUPPORT_ONLY, EXTENT_RIGHT_SUPPORT_ONLY,
    EXTENT_MIDSPAN_ONLY, EXTENT_LEFT_TRANSITION, EXTENT_RIGHT_TRANSITION,
    EXTENT_UNKNOWN,
}

# ── Span zone labels ─────────────────────────────────────────────────────────
SPAN_ZONE_LEFT_SUPPORT  = "LEFT_SUPPORT_ZONE"
SPAN_ZONE_LEFT_TRANS    = "LEFT_TRANSITION_ZONE"
SPAN_ZONE_MIDSPAN       = "MIDSPAN_ZONE"
SPAN_ZONE_RIGHT_TRANS   = "RIGHT_TRANSITION_ZONE"
SPAN_ZONE_RIGHT_SUPPORT = "RIGHT_SUPPORT_ZONE"
SPAN_ZONE_UNKNOWN       = "UNKNOWN_ZONE"

# ── Geometry confidence levels ────────────────────────────────────────────────
GEO_CONF_HIGH    = "HIGH"
GEO_CONF_MEDIUM  = "MEDIUM"
GEO_CONF_LOW     = "LOW"
GEO_CONF_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class BeamAxis:
    """
    Computed beam axis in local coordinate space.

    Coordinates are in mm, referenced from the beam's left end (start=0).
    The beam axis is derived from geometry_registry data.
    """
    beam_id:          str
    start_x:          float   # local: always 0.0
    start_y:          float   # local: midpoint of beam depth
    end_x:            float   # local: = beam_length_mm
    end_y:            float   # local: same as start_y for horizontal beam
    beam_length_mm:   float   # total beam length
    dxf_centroid_x:   float   # DXF reference centroid x (from beam_registry)
    dxf_centroid_y:   float   # DXF reference centroid y
    orientation:      str     # HORIZONTAL / INCLINED / UNKNOWN
    geometry_source:  str     # ORIGINAL / RECOVERED
    axis_confidence:  float   # 0.0 - 1.0

    @property
    def unit_vector_x(self) -> float:
        """Unit vector component along beam axis (always 1.0 for horizontal)."""
        span = self.end_x - self.start_x
        return span / self.beam_length_mm if self.beam_length_mm > 0 else 0.0

    @property
    def dxf_start_x(self) -> float:
        """Estimated DXF x coordinate of beam left end."""
        return self.dxf_centroid_x - self.beam_length_mm / 2.0

    @property
    def dxf_end_x(self) -> float:
        """Estimated DXF x coordinate of beam right end."""
        return self.dxf_centroid_x + self.beam_length_mm / 2.0


@dataclass(frozen=True)
class SupportLocation:
    """
    A beam support location with its zone extent.

    position_fraction: 0.0 = left end, 1.0 = right end
    support_width_mm:  physical column/wall width the beam bears on
    """
    support_id:         str
    beam_id:            str
    support_type:       str    # LEFT_SUPPORT / RIGHT_SUPPORT / INTERMEDIATE
    position_fraction:  float  # normalized position of support centerline
    position_mm:        float  # local mm position of support centerline
    support_width_mm:   float  # physical width of support
    zone_start_fraction:float  # start of support zone (normalized)
    zone_end_fraction:  float  # end of support zone (normalized)
    confidence:         float  # 0.0 - 1.0


@dataclass(frozen=True)
class ProjectionResult:
    """
    Result of projecting an annotation's DXF position onto the beam axis.

    The projection collapses the 2D DXF position to a 1D position along
    the beam's local axis.
    """
    annotation_id:         str
    beam_id:               str
    dxf_x:                 float   # original DXF x
    dxf_y:                 float   # original DXF y
    local_x:               float   # mm from beam start (projection)
    perpendicular_offset:  float   # |dxf_y - beam_centroid_y| in DXF units
    projection_confidence: str     # HIGH / MEDIUM / LOW
    projection_source:     str     # what data sourced this position


@dataclass(frozen=True)
class GeometryContext:
    """
    Complete geometry context for one reinforcement annotation.

    This is the R.3 output object consumed by R.4.

    Intent remains UNKNOWN — this object contains geometry evidence ONLY.
    All fields describe WHERE the annotation is, not WHAT IT MEANS.
    """
    beam_id:                str
    annotation_id:          str

    # ── Projection data ───────────────────────────────────────────────────────
    projection_point_x:     float   # local mm position along beam axis
    projection_distance_mm: float   # same as projection_point_x
    perpendicular_offset:   float   # how far annotation text is from beam axis
    projection_confidence:  str

    # ── Normalized position ───────────────────────────────────────────────────
    normalized_position:    float   # 0.0 (left) → 1.0 (right)
    beam_length_mm:         float

    # ── Support relationships ─────────────────────────────────────────────────
    nearest_support:        str     # LEFT_SUPPORT / RIGHT_SUPPORT / NONE
    distance_left_mm:       float   # distance from left support centerline
    distance_right_mm:      float   # distance from right support centerline
    inside_left_support:    bool    # annotation in left support zone
    inside_right_support:   bool    # annotation in right support zone
    inside_support_zone:    bool    # in either support zone

    # ── Zone classification ───────────────────────────────────────────────────
    support_zone:           str     # LEFT_SUPPORT_ZONE / RIGHT_SUPPORT_ZONE / NONE
    span_zone:              str     # SPAN_ZONE_* constant

    # ── Extent evidence ───────────────────────────────────────────────────────
    candidate_extent:       str     # EXTENT_* constant (observable, NOT intent)
    extent_confidence:      str     # HIGH / MEDIUM / LOW
    extent_reason:          str

    # ── Overall geometry confidence ───────────────────────────────────────────
    geometry_confidence:    str
    geometry_required:      bool    # always True — R.4 still needs this
    geometry_notes:         List[str]

    # ── Source traceability ───────────────────────────────────────────────────
    geometry_source:        str     # where geometry data came from
    position_source:        str     # where annotation position came from
