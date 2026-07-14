"""
Orientation Feature Extractor — angle and direction of the bar.
Observations only. No semantic meaning assigned.
"""

from __future__ import annotations

from typing import Any, Dict

from engineering_feature_model import (
    OrientationFeatures,
    ORI_LONGITUDINAL, ORI_TRANSVERSE, ORI_VERTICAL, ORI_DIAGONAL, ORI_UNKNOWN,
    ZONE_TRANSVERSE, ZONE_SIDE,
)

# Position zones that map to transverse orientation
_TRANSVERSE_ZONES = {"TRANSVERSE_ZONE", "TRANSVERSE"}
_SIDE_ZONES = {"SIDE_ZONE", "SIDE"}


class OrientationFeatureExtractor:
    """Extract orientation observations — purely from position zone and spacing."""

    def extract(
        self,
        bar: Dict[str, Any],
        beam_model: Dict[str, Any],
    ) -> OrientationFeatures:
        zone = (bar.get("position_zone") or "").upper()
        spacing = bar.get("spacing_mm")

        # Stirrups/links are transverse; side bars are longitudinal; all others are longitudinal
        if zone in _TRANSVERSE_ZONES or spacing is not None:
            orientation = ORI_TRANSVERSE
            angle_deg = 90.0
            parallel = False
            perpendicular = True
        elif zone in _SIDE_ZONES:
            orientation = ORI_LONGITUDINAL
            angle_deg = 0.0
            parallel = True
            perpendicular = False
        else:
            orientation = ORI_LONGITUDINAL
            angle_deg = 0.0
            parallel = True
            perpendicular = False

        return OrientationFeatures(
            orientation=orientation,
            orientation_angle_deg=angle_deg,
            parallel_to_beam=parallel,
            perpendicular_to_beam=perpendicular,
        )
