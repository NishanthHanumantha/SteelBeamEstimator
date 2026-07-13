"""
Support Feature Extractor — how the bar interacts with support zones.
Observations only. No semantic meaning assigned.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from engineering_feature_model import (
    SupportFeatures,
    SUPP_LEFT, SUPP_RIGHT, SUPP_BOTH, SUPP_INTERMEDIATE, SUPP_NONE, SUPP_UNKNOWN,
)

SUPPORT_ZONE_FRACTION = 0.25  # 0-25% and 75-100% of span are support zones


class SupportFeatureExtractor:
    """Extract support-zone interaction observations."""

    def extract(
        self,
        bar: Dict[str, Any],
        beam_model: Dict[str, Any],
        config: Dict[str, Any],
    ) -> SupportFeatures:
        geom = beam_model.get("geometry") or {}
        span = geom.get("clear_span_mm") or 0.0
        coverage = bar.get("coverage_ratio") or 0.0
        extent = (bar.get("extent") or "").upper()
        support_zone_bar = bar.get("support_zone") or ""
        frac = config.get("support_zone_fraction", SUPPORT_ZONE_FRACTION)
        support_width = 200.0  # default support width mm

        # Determine support overlaps from extent
        left_overlap = (
            "LEFT" in extent
            or "FULL" in extent
            or "BOTH" in extent
            or "LEFT" in support_zone_bar.upper()
        )
        right_overlap = (
            "RIGHT" in extent
            or "FULL" in extent
            or "BOTH" in extent
            or "RIGHT" in support_zone_bar.upper()
        )
        intermediate_overlap = False  # determined by topology (multi-span beams)

        # Estimate support region length
        support_region_mm: Optional[float] = None
        if span > 0:
            support_region_mm = round(min(span * frac, support_width), 1)

        # Support region ratio
        support_zone_ratio: Optional[float] = None
        if span > 0:
            overlap_length = 0.0
            if left_overlap:
                overlap_length += support_region_mm or 0
            if right_overlap:
                overlap_length += support_region_mm or 0
            support_zone_ratio = round(overlap_length / span, 3) if span > 0 else None

        # Support region type
        if left_overlap and right_overlap:
            region_type = SUPP_BOTH
        elif left_overlap:
            region_type = SUPP_LEFT
        elif right_overlap:
            region_type = SUPP_RIGHT
        elif intermediate_overlap:
            region_type = SUPP_INTERMEDIATE
        elif "NONE" in extent.upper() or coverage < 0.1:
            region_type = SUPP_NONE
        else:
            region_type = SUPP_NONE

        return SupportFeatures(
            left_support_overlap=left_overlap,
            right_support_overlap=right_overlap,
            intermediate_support_overlap=intermediate_overlap,
            support_zone_ratio=support_zone_ratio,
            support_region_length_mm=support_region_mm,
            support_region_type=region_type,
        )
