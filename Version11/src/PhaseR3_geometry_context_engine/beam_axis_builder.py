"""
beam_axis_builder.py — Build BeamAxis from geometry_registry + beam_registry.
MODEL_VERSION: 8.0.0

Data sources:
  geometry_registry.json   → beam_axis (local coords), support_locations, confidence
  beam_registry.json       → centroid_x, centroid_y (DXF reference point), clear_span_mm

Coordinate model:
  Local space:  start=0 to end=beam_length_mm
  DXF space:    centroid_x ± span/2 (estimated beam extent in drawing)
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

from .geometry_models import BeamAxis, GEO_CONF_HIGH, GEO_CONF_MEDIUM, GEO_CONF_LOW


class BeamAxisBuilder:
    """
    Build BeamAxis objects from geometry registry and beam registry data.

    One BeamAxis per beam. Beam assumed horizontal in local coordinate system.
    """

    def build(
        self,
        beam_id:   str,
        geo_entry: Optional[Dict[str, Any]],
        reg_entry: Optional[Dict[str, Any]],
    ) -> BeamAxis:
        """Build BeamAxis from available data. Falls back gracefully if missing."""

        notes: list = []

        # ── Beam length ───────────────────────────────────────────────────────
        beam_length_mm = 0.0
        geo_source     = "UNKNOWN"
        geo_confidence = 0.5

        if geo_entry and geo_entry.get("beam_axis"):
            axis = geo_entry["beam_axis"]
            beam_length_mm = float(axis.get("length_mm") or 0.0)
            geo_source     = str(geo_entry.get("source") or "RECOVERED")
            geo_confidence = float(geo_entry.get("confidence") or 0.5)
            notes.append(f"Beam axis from geometry_registry ({geo_source})")
        elif reg_entry:
            beam_length_mm = float(reg_entry.get("clear_span_mm") or 0.0)
            geo_source     = "BEAM_REGISTRY"
            geo_confidence = 0.4
            notes.append(f"Beam length from beam_registry.clear_span_mm")

        if beam_length_mm <= 0:
            beam_length_mm = 8000.0  # engineering default fallback
            geo_confidence = 0.1
            notes.append("WARNING: beam length unknown, using 8000mm fallback")

        # ── DXF reference centroid ────────────────────────────────────────────
        dxf_centroid_x = 0.0
        dxf_centroid_y = 0.0
        if reg_entry:
            dxf_centroid_x = float(reg_entry.get("centroid_x") or 0.0)
            dxf_centroid_y = float(reg_entry.get("centroid_y") or 0.0)

        # ── Beam axis local coords (start=0, end=length) ──────────────────────
        start_y = 0.0
        if geo_entry and geo_entry.get("beam_axis"):
            start_y = float(geo_entry["beam_axis"].get("start_y") or 0.0)

        # ── Orientation ───────────────────────────────────────────────────────
        end_y = start_y  # horizontal beam: start_y == end_y
        if geo_entry and geo_entry.get("beam_axis"):
            end_y = float(geo_entry["beam_axis"].get("end_y") or start_y)
        dy = abs(end_y - start_y)
        orientation = "HORIZONTAL" if dy < 0.01 * beam_length_mm else "INCLINED"

        # ── Axis confidence as string ─────────────────────────────────────────
        conf_str = (
            GEO_CONF_HIGH   if geo_confidence >= 0.8 else
            GEO_CONF_MEDIUM if geo_confidence >= 0.5 else
            GEO_CONF_LOW
        )

        return BeamAxis(
            beam_id         = beam_id,
            start_x         = 0.0,
            start_y         = start_y,
            end_x           = beam_length_mm,
            end_y           = end_y,
            beam_length_mm  = beam_length_mm,
            dxf_centroid_x  = dxf_centroid_x,
            dxf_centroid_y  = dxf_centroid_y,
            orientation     = orientation,
            geometry_source = geo_source,
            axis_confidence = geo_confidence,
        )
