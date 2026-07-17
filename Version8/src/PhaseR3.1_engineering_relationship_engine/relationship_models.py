"""
relationship_models.py — Data models for Phase R.3.1.
MODEL_VERSION: 8.1.0

All models represent drawing relationships and geometry evidence.
No engineering intent is stored or inferred.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# ── Extent evidence labels (observable geometry, NOT engineering intent) ──────
EXTENT_FULL_SPAN           = "FULL_SPAN"
EXTENT_LEFT_SUPPORT_ONLY   = "LEFT_SUPPORT_ONLY"
EXTENT_RIGHT_SUPPORT_ONLY  = "RIGHT_SUPPORT_ONLY"
EXTENT_LEFT_TO_MIDSPAN     = "LEFT_SUPPORT_TO_MIDSPAN"
EXTENT_MIDSPAN_TO_RIGHT    = "MIDSPAN_TO_RIGHT_SUPPORT"
EXTENT_CENTER_ONLY         = "CENTER_ONLY"
EXTENT_UNKNOWN             = "UNKNOWN"

# ── Confidence levels ─────────────────────────────────────────────────────────
CONF_HIGH    = "HIGH"
CONF_MEDIUM  = "MEDIUM"
CONF_LOW     = "LOW"
CONF_UNKNOWN = "UNKNOWN"

# ── Bar vertical placement evidence (geometry only) ───────────────────────────
PLACEMENT_TOP    = "TOP_FACE"
PLACEMENT_BOTTOM = "BOTTOM_FACE"
PLACEMENT_SIDE   = "SIDE_FACE"
PLACEMENT_UNKNOWN= "UNKNOWN"


@dataclass
class LeaderObject:
    """
    A leader entity from the DXF drawing.

    tip   = vertices[0] — arrowhead, points to physical bar
    tail  = vertices[-1] — shoulder, connects to annotation text

    No engineering interpretation stored.
    """
    leader_id:          str
    beam_id:            str          # assigned by spatial proximity
    tip_x:              float        # arrowhead x
    tip_y:              float        # arrowhead y
    tail_x:             float        # shoulder x
    tail_y:             float        # shoulder y
    vertex_count:       int
    vertices:           List         # list of (x, y) tuples
    layer:              str
    has_arrowhead:      bool
    leader_length:      float        # total path length
    tip_direction:      str          # UP / DOWN / LEFT / RIGHT / DIAGONAL


@dataclass
class ArrowObject:
    """
    Arrow resolved from a leader entity.

    The arrow represents the geometric connection between
    the leader line and the physical reinforcement.
    """
    arrow_id:           str
    leader_id:          str
    beam_id:            str
    tip_x:              float
    tip_y:              float
    direction:          str          # UP / DOWN / LEFT / RIGHT
    annotation_side:    str          # the annotation is on this side of the bar
    confidence:         str


@dataclass
class PhysicalBar:
    """
    A physical reinforcement bar detected in the DXF drawing.

    Derived from horizontal LINE / LWPOLYLINE entities on reinforcement layers.
    No engineering classification made here.
    """
    bar_id:             str
    beam_id:            str          # assigned by spatial overlap
    entity_type:        str          # LINE / LWPOLYLINE / POLYLINE
    layer:              str
    start_x:            float        # leftmost x in DXF space
    end_x:              float        # rightmost x in DXF space
    y_position:         float        # representative y coordinate
    bar_length_mm:      float        # end_x - start_x (approximate length)
    vertical_placement: str          # TOP_FACE / BOTTOM_FACE / SIDE_FACE / UNKNOWN
    normalized_start:   float        # 0.0 → 1.0 relative to beam
    normalized_end:     float        # 0.0 → 1.0 relative to beam
    bar_confidence:     str


@dataclass
class SupportCrossing:
    """
    Evidence that a physical bar crosses (reaches into) a support zone.
    Pure geometry — no intent.
    """
    crossing_id:        str
    bar_id:             str
    beam_id:            str
    support_id:         str
    support_type:       str          # LEFT_SUPPORT / RIGHT_SUPPORT
    crosses:            bool
    normalized_depth:   float        # how far into support zone the bar extends
    crossing_confidence:str


@dataclass
class AnnotationRelationship:
    """
    Association between an annotation, its leader, and the physical bar.

    Chain: annotation → leader → arrow → physical_bar
    """
    relationship_id:    str
    beam_id:            str
    annotation_id:      str
    leader_id:          Optional[str]
    arrow_id:           Optional[str]
    physical_bar_id:    Optional[str]
    leader_distance:    float        # distance from leader tail to annotation
    bar_distance:       float        # distance from leader tip to bar
    relationship_confidence: str
    relationship_reason:    str


@dataclass
class EngineeringDrawingRelationship:
    """
    Complete drawing relationship context for one annotation.
    Consumed by Phase R.4 to resolve engineering intent.

    Intent MUST remain UNKNOWN — this object stores geometry relationships only.
    """
    relationship_id:     str
    beam_id:             str
    annotation_id:       str
    leader_id:           Optional[str]
    arrow_id:            Optional[str]
    physical_bar_id:     Optional[str]
    projection_id:       Optional[str]
    geometry_context_id: Optional[str]
    support_ids:         List[str]

    # ── Extent evidence ───────────────────────────────────────────────────────
    extent_label:        str         # EXTENT_* constant (geometry, not intent)
    extent_confidence:   str
    extent_reason:       str

    # ── Support crossings ─────────────────────────────────────────────────────
    support_crossings:   int         # how many supports bar crosses/reaches
    left_support_crossed:bool
    right_support_crossed:bool

    # ── Bar geometry ──────────────────────────────────────────────────────────
    leader_length:       float
    bar_length:          float
    bar_normalized_start:float
    bar_normalized_end:  float
    bar_vertical_placement: str      # TOP_FACE / BOTTOM_FACE / SIDE_FACE / UNKNOWN

    # ── Relationship quality ──────────────────────────────────────────────────
    relationship_confidence: str
    relationship_reason:     str
    convention_evidence:     List[str]  # observable drawing conventions
    geometry_notes:          List[str]


@dataclass
class ConventionEvidence:
    """
    Observable engineering drawing convention extracted from DXF.
    Based on spatial analysis of actual drawing patterns — NOT beam-specific.

    Used by R.4 as context for intent resolution.
    """
    convention_id:      str
    convention_type:    str          # e.g. LEADER_DIRECTION, BAR_POSITION, etc.
    description:        str
    evidence_value:     str          # the observed geometric value
    confidence:         str
    source:             str          # which drawing entity provided this
