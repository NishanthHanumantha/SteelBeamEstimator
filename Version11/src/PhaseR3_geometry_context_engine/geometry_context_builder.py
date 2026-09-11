"""
geometry_context_builder.py — Assemble GeometryContext for one annotation.
MODEL_VERSION: 8.0.0

Orchestrates the 8-step geometry pipeline per annotation:
  Step 1: BeamAxis (pre-built per beam)
  Step 2: SupportLocations (pre-built per beam)
  Step 3: ProjectionEngine  → ProjectionResult
  Step 4: NormalizedPositionBuilder → normalized_position
  Step 5: SupportZoneClassifier  → inside_left/right, distances
  Step 6: SpanZoneClassifier     → span_zone
  Step 7: ExtentEvidenceBuilder  → candidate_extent, confidence, reason
  Step 8: GeometryContext assembly

Intent remains UNKNOWN throughout.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .extent_evidence_builder import ExtentEvidenceBuilder
from .geometry_models import (
    BeamAxis, SupportLocation, ProjectionResult,
    GeometryContext,
    GEO_CONF_HIGH, GEO_CONF_MEDIUM, GEO_CONF_LOW,
)
from .normalized_position_builder import NormalizedPositionBuilder
from .projection_engine import ProjectionEngine
from .span_zone_classifier import SpanZoneClassifier
from .support_zone_classifier import SupportZoneClassifier


class GeometryContextBuilder:
    """
    Build GeometryContext for a single annotation.
    """

    def __init__(self):
        self._projector     = ProjectionEngine()
        self._norm_builder  = NormalizedPositionBuilder()
        self._sup_class     = SupportZoneClassifier()
        self._span_class    = SpanZoneClassifier()
        self._extent_builder= ExtentEvidenceBuilder()

    def build(
        self,
        annotation_id: str,
        beam_axis:     BeamAxis,
        supports:      List[SupportLocation],
        ann_record:    Optional[Dict[str, Any]],
        fact_dict:     Optional[Dict[str, Any]] = None,
        group_positions: Optional[List[float]] = None,
    ) -> GeometryContext:
        """Build a complete GeometryContext for one annotation."""
        notes: List[str] = []

        # Step 3: Projection
        projection = self._projector.project(
            annotation_id, beam_axis, ann_record, fact_dict
        )
        notes.append(f"Projection source: {projection.projection_source}")

        # Step 4: Normalized position
        norm_pos, norm_notes = self._norm_builder.compute(
            projection, beam_axis.beam_length_mm
        )
        notes.extend(norm_notes)

        # Step 5: Support zone classification
        sup_result = self._sup_class.classify(
            norm_pos, supports, beam_axis.beam_length_mm
        )
        notes.append(
            f"Support zones: left={sup_result['inside_left_support']}, "
            f"right={sup_result['inside_right_support']}"
        )

        # Step 6: Span zone classification
        span_zone, span_notes = self._span_class.classify(
            norm_pos, supports, beam_axis.beam_length_mm
        )
        notes.extend(span_notes)

        # Step 7: Extent evidence
        extent, ext_conf, ext_reason = self._extent_builder.build_for_annotation(
            span_zone        = span_zone,
            normalized_pos   = norm_pos,
            inside_left      = sup_result["inside_left_support"],
            inside_right     = sup_result["inside_right_support"],
        )

        # Refine extent with group-level evidence
        if group_positions:
            extent, ext_conf, ext_reason = self._extent_builder.refine_with_beam_group(
                annotation_id, extent, ext_conf, ext_reason, group_positions
            )

        # Step 8: Overall geometry confidence
        proj_conf_score = {GEO_CONF_HIGH: 1.0, GEO_CONF_MEDIUM: 0.6, GEO_CONF_LOW: 0.3}.get(
            projection.projection_confidence, 0.3
        )
        axis_conf = beam_axis.axis_confidence
        geo_conf_score = (proj_conf_score + axis_conf) / 2.0
        geo_conf = (
            GEO_CONF_HIGH   if geo_conf_score >= 0.75 else
            GEO_CONF_MEDIUM if geo_conf_score >= 0.45 else
            GEO_CONF_LOW
        )

        notes.append(
            f"Geometry confidence: {geo_conf} "
            f"(projection={projection.projection_confidence}, axis_conf={axis_conf:.2f})"
        )

        return GeometryContext(
            beam_id                = beam_axis.beam_id,
            annotation_id          = annotation_id,
            projection_point_x     = round(projection.local_x, 2),
            projection_distance_mm = round(projection.local_x, 2),
            perpendicular_offset   = round(projection.perpendicular_offset, 2),
            projection_confidence  = projection.projection_confidence,
            normalized_position    = norm_pos,
            beam_length_mm         = beam_axis.beam_length_mm,
            nearest_support        = sup_result["nearest_support"],
            distance_left_mm       = sup_result["distance_left_mm"],
            distance_right_mm      = sup_result["distance_right_mm"],
            inside_left_support    = sup_result["inside_left_support"],
            inside_right_support   = sup_result["inside_right_support"],
            inside_support_zone    = sup_result["inside_support_zone"],
            support_zone           = sup_result["support_zone"],
            span_zone              = span_zone,
            candidate_extent       = extent,
            extent_confidence      = ext_conf,
            extent_reason          = ext_reason,
            geometry_confidence    = geo_conf,
            geometry_required      = True,
            geometry_notes         = notes,
            geometry_source        = beam_axis.geometry_source,
            position_source        = projection.projection_source,
        )
