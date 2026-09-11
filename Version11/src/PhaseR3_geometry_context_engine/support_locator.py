"""
support_locator.py — Extract SupportLocation objects from geometry registry.
MODEL_VERSION: 8.0.0

Support data comes from geometry_registry.json which has:
  - support_locations: [{support_id, support_type, position_fraction, support_width_mm}]

For recovered beams, supports default to:
  - Left:  position_fraction=0.0, support_width_mm=200
  - Right: position_fraction=1.0, support_width_mm=200

No engineering assumptions about support behaviour. Only geometry.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .geometry_models import SupportLocation


_DEFAULT_SUPPORT_WIDTH_MM = 200.0  # typical column width when not specified


class SupportLocator:
    """
    Extract SupportLocation objects for a beam from geometry registry.
    """

    def locate(
        self,
        beam_id:          str,
        geo_entry:        Optional[Dict[str, Any]],
        beam_length_mm:   float,
    ) -> List[SupportLocation]:
        """
        Returns list of SupportLocation objects for the beam.
        Falls back to default left/right supports if geometry missing.
        """
        raw_supports = []
        if geo_entry:
            raw_supports = geo_entry.get("support_locations") or []

        if not raw_supports:
            # Fallback: assume simple beam with left + right supports
            raw_supports = [
                {
                    "support_id":      f"SUP::DEFAULT::{beam_id}::LEFT",
                    "support_type":    "LEFT_SUPPORT",
                    "position_fraction": 0.0,
                    "support_width_mm": _DEFAULT_SUPPORT_WIDTH_MM,
                },
                {
                    "support_id":      f"SUP::DEFAULT::{beam_id}::RIGHT",
                    "support_type":    "RIGHT_SUPPORT",
                    "position_fraction": 1.0,
                    "support_width_mm": _DEFAULT_SUPPORT_WIDTH_MM,
                },
            ]

        result: List[SupportLocation] = []
        for raw in raw_supports:
            pos_frac = float(raw.get("position_fraction", 0.0))
            width_mm = float(raw.get("support_width_mm") or _DEFAULT_SUPPORT_WIDTH_MM)
            pos_mm   = pos_frac * beam_length_mm
            half_w   = width_mm / 2.0 / beam_length_mm if beam_length_mm > 0 else 0.0

            confidence = 0.9 if "REC" in str(raw.get("support_id", "")) else 1.0
            # Original geometry has higher confidence; recovered slightly lower
            if "DEFAULT" in str(raw.get("support_id", "")):
                confidence = 0.5

            result.append(SupportLocation(
                support_id           = str(raw.get("support_id") or ""),
                beam_id              = beam_id,
                support_type         = str(raw.get("support_type") or "UNKNOWN"),
                position_fraction    = pos_frac,
                position_mm          = pos_mm,
                support_width_mm     = width_mm,
                zone_start_fraction  = max(0.0, pos_frac - half_w),
                zone_end_fraction    = min(1.0, pos_frac + half_w),
                confidence           = confidence,
            ))

        return result
