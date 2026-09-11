"""
support_zone_classifier.py — Determine if annotation is inside a support zone.
MODEL_VERSION: 8.0.0

Support zone = the physical extent of the beam support (column/wall width).
An annotation is "inside_support_zone" if its normalized position falls within
any support's [zone_start_fraction, zone_end_fraction].

This is PURELY geometric classification.
No engineering intent is derived here.
"""
from __future__ import annotations

from typing import List, Tuple

from .geometry_models import SupportLocation


class SupportZoneClassifier:
    """
    Classify whether a normalized position falls inside a support zone.

    Returns:
      inside_left_support:  bool
      inside_right_support: bool
      inside_support_zone:  bool (either)
      nearest_support:      "LEFT_SUPPORT" / "RIGHT_SUPPORT" / "NONE"
      distance_left_mm:     float (mm from left support centerline)
      distance_right_mm:    float (mm from right support centerline)
      nearest_support_type: str
    """

    def classify(
        self,
        normalized_pos: float,
        supports:       List[SupportLocation],
        beam_length_mm: float,
    ) -> dict:
        result = {
            "inside_left_support":  False,
            "inside_right_support": False,
            "inside_support_zone":  False,
            "nearest_support":      "NONE",
            "distance_left_mm":     beam_length_mm,
            "distance_right_mm":    beam_length_mm,
            "support_zone":         "NONE",
        }

        left  = next((s for s in supports if "LEFT"  in s.support_type), None)
        right = next((s for s in supports if "RIGHT" in s.support_type), None)

        if left:
            dist_left = abs(normalized_pos - left.position_fraction) * beam_length_mm
            result["distance_left_mm"] = round(dist_left, 1)
            if left.zone_start_fraction <= normalized_pos <= left.zone_end_fraction:
                result["inside_left_support"] = True
                result["inside_support_zone"] = True
                result["support_zone"]        = "LEFT_SUPPORT_ZONE"

        if right:
            dist_right = abs(normalized_pos - right.position_fraction) * beam_length_mm
            result["distance_right_mm"] = round(dist_right, 1)
            if right.zone_start_fraction <= normalized_pos <= right.zone_end_fraction:
                result["inside_right_support"] = True
                result["inside_support_zone"]  = True
                result["support_zone"]         = (
                    "BOTH_SUPPORT_ZONES"
                    if result["inside_left_support"]
                    else "RIGHT_SUPPORT_ZONE"
                )

        # Nearest support
        if left and right:
            if result["distance_left_mm"] <= result["distance_right_mm"]:
                result["nearest_support"] = "LEFT_SUPPORT"
            else:
                result["nearest_support"] = "RIGHT_SUPPORT"
        elif left:
            result["nearest_support"] = "LEFT_SUPPORT"
        elif right:
            result["nearest_support"] = "RIGHT_SUPPORT"

        return result
