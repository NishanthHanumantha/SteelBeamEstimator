"""
EngineeringFeatureModel — canonical feature contract for Phase L.2.1.

Every reinforcement bar produces exactly one EngineeringFeatureModel.
These are engineering observations only — no semantic role is assigned here.
Classification happens in Phase L.2 (Interpretation Engine) using these features.

Architecture:
  Drawing → Parser → Engineering Geometry
  → Engineering Feature Extraction (this phase)
  → Engineering Reinforcement Interpretation (L.2)
  → BeamReinforcementModel → Rules → Calculation → Steel → BBS → Excel
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

PHASE = "Phase L.2.1"
MODEL_VERSION = "6.6.3"
ENGINE_VERSION = "1.0.0"

# ── Position zones (observational only, no semantic meaning) ─────────────────
ZONE_TOP = "TOP"
ZONE_MIDDLE = "MIDDLE"
ZONE_BOTTOM = "BOTTOM"
ZONE_SIDE = "SIDE"
ZONE_TRANSVERSE = "TRANSVERSE"
ZONE_UNKNOWN = "UNKNOWN"
POSITION_ZONES = [ZONE_TOP, ZONE_MIDDLE, ZONE_BOTTOM, ZONE_SIDE, ZONE_TRANSVERSE, ZONE_UNKNOWN]

# ── Orientation types ────────────────────────────────────────────────────────
ORI_LONGITUDINAL = "LONGITUDINAL"
ORI_TRANSVERSE = "TRANSVERSE"
ORI_VERTICAL = "VERTICAL"
ORI_DIAGONAL = "DIAGONAL"
ORI_UNKNOWN = "UNKNOWN"
ORIENTATIONS = [ORI_LONGITUDINAL, ORI_TRANSVERSE, ORI_VERTICAL, ORI_DIAGONAL, ORI_UNKNOWN]

# ── Continuity types ─────────────────────────────────────────────────────────
CONT_SINGLE = "SINGLE_SPAN"
CONT_MULTI = "MULTI_SPAN"
CONT_UNKNOWN = "UNKNOWN"

# ── Support region types ─────────────────────────────────────────────────────
SUPP_LEFT = "LEFT"
SUPP_RIGHT = "RIGHT"
SUPP_BOTH = "BOTH"
SUPP_INTERMEDIATE = "INTERMEDIATE"
SUPP_NONE = "NONE"
SUPP_UNKNOWN = "UNKNOWN"

# ── Extent types ─────────────────────────────────────────────────────────────
EXT_FULL = "FULL_SPAN"
EXT_LEFT_ONLY = "LEFT_SUPPORT_ONLY"
EXT_RIGHT_ONLY = "RIGHT_SUPPORT_ONLY"
EXT_BOTH_SUPPORTS = "BOTH_SUPPORTS"
EXT_PARTIAL = "PARTIAL_SPAN"
EXT_MIDSPAN = "MIDSPAN_ONLY"
EXT_DEV_LENGTH = "DEVELOPMENT_LENGTH_EXTENSION"
EXT_ANCHORAGE = "ANCHORAGE_EXTENSION"
EXT_UNKNOWN = "UNKNOWN"


@dataclass
class GeometryFeatures:
    """Physical geometric properties of the bar — pure observations."""
    start_point: Optional[Tuple[float, float]]
    end_point: Optional[Tuple[float, float]]
    midpoint: Optional[Tuple[float, float]]
    length_mm: Optional[float]
    projected_length_mm: Optional[float]
    relative_length: Optional[float]          # bar_length / clear_span
    bounding_box: Optional[Dict[str, float]]  # {min_x, min_y, max_x, max_y}
    orientation_angle_deg: Optional[float]
    is_polyline: bool
    is_line: bool
    is_arc: bool
    is_closed: bool
    is_curved: bool
    crosses_beam_axis: bool
    touches_support: bool
    touches_beam_edge: bool


@dataclass
class PositionFeatures:
    """Where the bar sits within the beam cross-section — pure observations."""
    vertical_rank: int                 # 1 = topmost, n = bottommost
    horizontal_rank: int               # 1 = leftmost
    distance_from_top_face_mm: Optional[float]
    distance_from_bottom_face_mm: Optional[float]
    distance_from_left_support_mm: Optional[float]
    distance_from_right_support_mm: Optional[float]
    distance_from_centroid_mm: Optional[float]
    beam_depth_ratio: Optional[float]  # position_y / beam_depth (0=top, 1=bottom)
    beam_width_ratio: Optional[float]
    position_zone: str                 # TOP / MIDDLE / BOTTOM / SIDE / TRANSVERSE


@dataclass
class ContinuityFeatures:
    """Whether and how far the bar extends — pure observations."""
    is_continuous: bool                # reaches both supports (≥ 0.8 × span)
    is_single_span: bool
    is_multi_span: bool
    crosses_support: bool
    crosses_multiple_beams: bool
    number_of_beams_crossed: int
    beam_sequence: List[str]           # e.g. ["B8", "B9", "B10"]
    termination_points: List[str]      # "LEFT_SUPPORT" / "RIGHT_SUPPORT" / "MIDSPAN"
    continuity_type: str               # SINGLE_SPAN / MULTI_SPAN / UNKNOWN


@dataclass
class SupportFeatures:
    """How the bar interacts with support zones — pure observations."""
    left_support_overlap: bool
    right_support_overlap: bool
    intermediate_support_overlap: bool
    support_zone_ratio: Optional[float]   # fraction of bar in support zone
    support_region_length_mm: Optional[float]
    support_region_type: str              # LEFT / RIGHT / BOTH / INTERMEDIATE / NONE


@dataclass
class ExtentFeatures:
    """How much of the span the bar covers — pure observations."""
    full_span: bool
    left_support_only: bool
    right_support_only: bool
    both_supports: bool
    partial_span: bool
    midspan_only: bool
    development_length_extension: bool
    anchorage_extension: bool
    termination_region: Optional[str]
    coverage_ratio: Optional[float]       # bar_length / span
    extent_type: str                      # EXT_* constant


@dataclass
class OrientationFeatures:
    """Angle and direction of the bar — pure observations."""
    orientation: str                  # LONGITUDINAL / TRANSVERSE / VERTICAL / DIAGONAL
    orientation_angle_deg: Optional[float]
    parallel_to_beam: bool
    perpendicular_to_beam: bool


@dataclass
class AnnotationFeatures:
    """Properties extracted from the annotation text — pure observations."""
    callout: Optional[str]            # raw annotation string e.g. "2Y16"
    diameter_mm: Optional[float]
    quantity: Optional[int]
    spacing_mm: Optional[float]
    has_hook_symbol: bool
    leader_count: int
    leader_direction: Optional[str]
    leader_length_mm: Optional[float]
    annotation_layer: Optional[str]
    annotation_style: Optional[str]
    annotation_priority: Optional[str]  # "HIGH" / "MEDIUM" / "LOW"


@dataclass
class TopologyFeatures:
    """Connectivity and relationship observations — no semantic meaning."""
    connected_object_ids: List[str]
    parent_beam_id: Optional[str]
    adjacent_beam_ids: List[str]
    support_connection_ids: List[str]
    intersection_count: int
    crossing_count: int
    region_membership: List[str]
    engineering_graph_node_id: Optional[str]


@dataclass
class EngineeringFeatureModel:
    """
    Canonical feature record for one reinforcement bar.
    Contains only engineering observations — no semantic role assignment.
    Classification happens downstream in Phase L.2.
    """

    feature_id: str
    bar_id: str
    beam_id: str
    annotation_id: Optional[str]
    geometry_reference: Optional[str]
    engineering_object_reference: Optional[str]

    # Feature groups (all observational)
    geometry: GeometryFeatures
    position: PositionFeatures
    continuity: ContinuityFeatures
    support: SupportFeatures
    extent: ExtentFeatures
    orientation: OrientationFeatures
    annotation: AnnotationFeatures
    topology: TopologyFeatures

    # Meta
    traceability: Dict[str, Any]
    feature_completeness_score: float  # 0.0–1.0 (ratio of non-None features)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "bar_id": self.bar_id,
            "beam_id": self.beam_id,
            "annotation_id": self.annotation_id,
            "geometry_reference": self.geometry_reference,
            "engineering_object_reference": self.engineering_object_reference,
            "feature_completeness_score": self.feature_completeness_score,
            "geometry": self._geom(),
            "position": self._pos(),
            "continuity": self._cont(),
            "support": self._supp(),
            "extent": self._ext(),
            "orientation": self._ori(),
            "annotation": self._ann(),
            "topology": self._top(),
            "traceability": self.traceability,
        }

    def _geom(self) -> Dict:
        g = self.geometry
        return {
            "start_point": list(g.start_point) if g.start_point else None,
            "end_point": list(g.end_point) if g.end_point else None,
            "midpoint": list(g.midpoint) if g.midpoint else None,
            "length_mm": g.length_mm,
            "projected_length_mm": g.projected_length_mm,
            "relative_length": g.relative_length,
            "bounding_box": g.bounding_box,
            "orientation_angle_deg": g.orientation_angle_deg,
            "is_polyline": g.is_polyline,
            "is_line": g.is_line,
            "is_arc": g.is_arc,
            "is_closed": g.is_closed,
            "is_curved": g.is_curved,
            "crosses_beam_axis": g.crosses_beam_axis,
            "touches_support": g.touches_support,
            "touches_beam_edge": g.touches_beam_edge,
        }

    def _pos(self) -> Dict:
        p = self.position
        return {
            "vertical_rank": p.vertical_rank,
            "horizontal_rank": p.horizontal_rank,
            "distance_from_top_face_mm": p.distance_from_top_face_mm,
            "distance_from_bottom_face_mm": p.distance_from_bottom_face_mm,
            "distance_from_left_support_mm": p.distance_from_left_support_mm,
            "distance_from_right_support_mm": p.distance_from_right_support_mm,
            "distance_from_centroid_mm": p.distance_from_centroid_mm,
            "beam_depth_ratio": p.beam_depth_ratio,
            "beam_width_ratio": p.beam_width_ratio,
            "position_zone": p.position_zone,
        }

    def _cont(self) -> Dict:
        c = self.continuity
        return {
            "is_continuous": c.is_continuous,
            "is_single_span": c.is_single_span,
            "is_multi_span": c.is_multi_span,
            "crosses_support": c.crosses_support,
            "crosses_multiple_beams": c.crosses_multiple_beams,
            "number_of_beams_crossed": c.number_of_beams_crossed,
            "beam_sequence": c.beam_sequence,
            "termination_points": c.termination_points,
            "continuity_type": c.continuity_type,
        }

    def _supp(self) -> Dict:
        s = self.support
        return {
            "left_support_overlap": s.left_support_overlap,
            "right_support_overlap": s.right_support_overlap,
            "intermediate_support_overlap": s.intermediate_support_overlap,
            "support_zone_ratio": s.support_zone_ratio,
            "support_region_length_mm": s.support_region_length_mm,
            "support_region_type": s.support_region_type,
        }

    def _ext(self) -> Dict:
        e = self.extent
        return {
            "full_span": e.full_span,
            "left_support_only": e.left_support_only,
            "right_support_only": e.right_support_only,
            "both_supports": e.both_supports,
            "partial_span": e.partial_span,
            "midspan_only": e.midspan_only,
            "development_length_extension": e.development_length_extension,
            "anchorage_extension": e.anchorage_extension,
            "termination_region": e.termination_region,
            "coverage_ratio": e.coverage_ratio,
            "extent_type": e.extent_type,
        }

    def _ori(self) -> Dict:
        o = self.orientation
        return {
            "orientation": o.orientation,
            "orientation_angle_deg": o.orientation_angle_deg,
            "parallel_to_beam": o.parallel_to_beam,
            "perpendicular_to_beam": o.perpendicular_to_beam,
        }

    def _ann(self) -> Dict:
        a = self.annotation
        return {
            "callout": a.callout,
            "diameter_mm": a.diameter_mm,
            "quantity": a.quantity,
            "spacing_mm": a.spacing_mm,
            "has_hook_symbol": a.has_hook_symbol,
            "leader_count": a.leader_count,
            "leader_direction": a.leader_direction,
            "leader_length_mm": a.leader_length_mm,
            "annotation_layer": a.annotation_layer,
            "annotation_style": a.annotation_style,
            "annotation_priority": a.annotation_priority,
        }

    def _top(self) -> Dict:
        t = self.topology
        return {
            "connected_object_ids": t.connected_object_ids,
            "parent_beam_id": t.parent_beam_id,
            "adjacent_beam_ids": t.adjacent_beam_ids,
            "support_connection_ids": t.support_connection_ids,
            "intersection_count": t.intersection_count,
            "crossing_count": t.crossing_count,
            "region_membership": t.region_membership,
            "engineering_graph_node_id": t.engineering_graph_node_id,
        }


def make_feature_id(bar_id: str) -> str:
    return f"EFM::L2.1::{bar_id}"
