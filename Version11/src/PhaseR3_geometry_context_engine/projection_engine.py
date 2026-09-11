"""
projection_engine.py — Project annotation DXF position onto beam local axis.
MODEL_VERSION: 8.0.0

Coordinate transformation:
  DXF space → Local beam space

  DXF annotation (x_dxf, y_dxf)
    ↓
  Local x = x_dxf - beam_dxf_start_x
           where beam_dxf_start_x = centroid_x - beam_length_mm / 2

  Perpendicular offset = |y_dxf - centroid_y|

  This gives the annotation's position along the beam span.

For annotations without DXF coordinates (no reinforcement_annotations entry),
the projection returns UNKNOWN with the position_zone from the ESO as fallback.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .geometry_models import (
    BeamAxis,
    ProjectionResult,
    GEO_CONF_HIGH,
    GEO_CONF_MEDIUM,
    GEO_CONF_LOW,
)

# Zone to fallback normalized position mapping
_ZONE_TO_FALLBACK = {
    "TOP_ZONE":       0.5,
    "BOTTOM_ZONE":    0.5,
    "SIDE_FACE_ZONE": 0.5,
    "UNKNOWN_ZONE":   0.5,
}


class ProjectionEngine:
    """
    Project annotations onto beam axis.

    Primary source: DXF (x, y) from reinforcement_annotations.json
    Fallback source: position_zone from R.1 annotation → fixed normalized position
    """

    def project(
        self,
        annotation_id:  str,
        beam_axis:      BeamAxis,
        ann_record:     Optional[Dict[str, Any]],
        fact_dict:      Optional[Dict[str, Any]] = None,
    ) -> ProjectionResult:
        """
        Project one annotation onto the beam axis.

        ann_record: row from reinforcement_annotations.json (has x, y, dy_from_centroid)
        fact_dict:  R.2.1D fact (fallback source if ann_record missing)
        """
        # ── Primary: DXF coordinates ──────────────────────────────────────────
        if ann_record and ann_record.get("x") is not None:
            dxf_x = float(ann_record["x"])
            dxf_y = float(ann_record.get("y") or 0.0)
            local_x = dxf_x - beam_axis.dxf_start_x
            perp    = abs(dxf_y - beam_axis.dxf_centroid_y)
            source  = "REINFORCEMENT_ANNOTATIONS_DXF"
            conf    = GEO_CONF_HIGH
        else:
            # ── Fallback: use position_zone → centre of beam ─────────────────
            zone    = ""
            if fact_dict and fact_dict.get("original_semantic_object"):
                eso = fact_dict["original_semantic_object"]
                zone = str(eso.get("position_zone") or "")
            local_x = _ZONE_TO_FALLBACK.get(zone, 0.5) * beam_axis.beam_length_mm
            dxf_x   = beam_axis.dxf_start_x + local_x
            dxf_y   = beam_axis.dxf_centroid_y
            perp    = 0.0
            source  = "POSITION_ZONE_FALLBACK"
            conf    = GEO_CONF_LOW

        return ProjectionResult(
            annotation_id          = annotation_id,
            beam_id                = beam_axis.beam_id,
            dxf_x                  = dxf_x,
            dxf_y                  = dxf_y,
            local_x                = local_x,
            perpendicular_offset   = perp,
            projection_confidence  = conf,
            projection_source      = source,
        )
