"""
bar_geometry_builder.py — Compute geometry evidence for a physical bar.
MODEL_VERSION: 8.1.0

Given a PhysicalBar and beam axis + support data, compute:
  - Normalized start/end positions (already on PhysicalBar, here we refine)
  - Extent evidence label (observable geometry, NOT engineering intent)
  - Support crossing evidence

No engineering interpretation.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .relationship_models import (
    PhysicalBar,
    EXTENT_FULL_SPAN, EXTENT_LEFT_SUPPORT_ONLY, EXTENT_RIGHT_SUPPORT_ONLY,
    EXTENT_LEFT_TO_MIDSPAN, EXTENT_MIDSPAN_TO_RIGHT, EXTENT_CENTER_ONLY,
    EXTENT_UNKNOWN,
    CONF_HIGH, CONF_MEDIUM, CONF_LOW,
)

# Thresholds for extent classification
_SUPPORT_ZONE_THRESHOLD   = 0.25   # normalized — if bar reaches within 25% of span end
_MIDSPAN_CENTER_MAX       = 0.35   # normalized — if bar doesn't reach either support
_OVERSHOOT_TOLERANCE      = 0.15   # bar can extend up to 15% beyond span (into column)


class BarGeometryBuilder:
    """
    Compute extent evidence and crossing counts for a PhysicalBar.
    Returns (extent_label, confidence, reason, left_crossed, right_crossed)
    """

    def compute_extent(
        self,
        bar:          PhysicalBar,
        support_data: List[Dict[str, Any]],  # from SupportLocations.json
    ):
        """
        Returns (extent_label, confidence, reason, left_crossed, right_crossed).
        """
        ns = bar.normalized_start
        ne = bar.normalized_end

        # Clamp ne at 1.0 + overshoot for comparison
        ns_eff = max(0.0, ns)
        ne_eff = min(1.0 + _OVERSHOOT_TOLERANCE, ne)

        # Find support boundaries
        left_frac  = 0.0
        right_frac = 1.0
        left_width = 0.0
        right_width= 0.0

        for sup in support_data:
            if "LEFT" in str(sup.get("support_type", "")):
                left_frac   = float(sup.get("zone_end_fraction") or 0.0)
                left_width  = float(sup.get("support_width_mm") or 200.0)
            elif "RIGHT" in str(sup.get("support_type", "")):
                right_frac  = float(sup.get("zone_start_fraction") or 1.0)
                right_width = float(sup.get("support_width_mm") or 200.0)

        left_crossed  = ns_eff <= left_frac + _SUPPORT_ZONE_THRESHOLD
        right_crossed = ne_eff >= right_frac - _SUPPORT_ZONE_THRESHOLD

        if left_crossed and right_crossed:
            label  = EXTENT_FULL_SPAN
            conf   = CONF_HIGH
            reason = (
                f"Bar x=[{ns:.3f},{ne:.3f}] spans both support zones "
                f"(left<={left_frac:.3f}, right>={right_frac:.3f})"
            )
        elif left_crossed and ne_eff < 0.65:
            label  = EXTENT_LEFT_TO_MIDSPAN
            conf   = CONF_HIGH
            reason = f"Bar reaches left support (ns={ns:.3f}) but not right (ne={ne:.3f})"
        elif right_crossed and ns_eff > 0.35:
            label  = EXTENT_MIDSPAN_TO_RIGHT
            conf   = CONF_HIGH
            reason = f"Bar reaches right support (ne={ne:.3f}) but not left (ns={ns:.3f})"
        elif left_crossed:
            label  = EXTENT_LEFT_SUPPORT_ONLY
            conf   = CONF_MEDIUM
            reason = f"Bar only within left support zone (ns={ns:.3f}, ne={ne:.3f})"
        elif right_crossed:
            label  = EXTENT_RIGHT_SUPPORT_ONLY
            conf   = CONF_MEDIUM
            reason = f"Bar only within right support zone (ns={ns:.3f}, ne={ne:.3f})"
        elif ns_eff > _MIDSPAN_CENTER_MAX and ne_eff < 1.0 - _MIDSPAN_CENTER_MAX:
            label  = EXTENT_CENTER_ONLY
            conf   = CONF_MEDIUM
            reason = f"Bar entirely in center zone [{ns:.3f},{ne:.3f}]"
        else:
            label  = EXTENT_UNKNOWN
            conf   = CONF_LOW
            reason = f"Bar extent indeterminate [{ns:.3f},{ne:.3f}]"

        return label, conf, reason, left_crossed, right_crossed
