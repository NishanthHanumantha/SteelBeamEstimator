"""
reinforcement_geometry_mapper.py — Associate annotations with engineering geometry.

Determines:
  - Beam zone (TOP / BOTTOM / SIDE_FACE based on dy relative to centroid and section depth)
  - Support zone (LEFT / RIGHT / MIDSPAN based on dx relative to centroid)
  - Extent (FULL_SPAN / PARTIAL_SPAN)

Uses the beam section depth (available from V.ROOT.1) to compute zone boundaries
in DXF drawing units.  Assumes 1 DXF unit ≈ 1 mm for this drawing.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from .reinforcement_models import (
    BeamDetail,
    ReinforcementAnnotation,
    ZONE_TOP, ZONE_BOTTOM, ZONE_SIDE, ZONE_UNKNOWN,
)

log = logging.getLogger(__name__)

# ── Engineering zone fractions of beam depth ─────────────────────────────────
# Top zone: dy > +TOP_FRACTION * depth
# Bottom zone: dy < -BOTTOM_FRACTION * depth
# Side zone: |dy| < SIDE_FRACTION * depth
TOP_FRACTION    = 0.15
BOTTOM_FRACTION = 0.15


class ReinforcementGeometryMapper:
    """
    Refines position_zone using beam section geometry.
    Also annotates support_zone (LEFT / MIDSPAN / RIGHT) from dx.
    """

    def __init__(self, config: dict):
        self._neutral = float(
            config.get("geometry", {}).get("neutral_zone_half_height", 200.0)
        )

    # ──────────────────────────────────────────────────────────────────────────
    def map_geometry(
        self,
        details:          List[BeamDetail],
        beam_annotations: Dict[str, List[ReinforcementAnnotation]],
    ) -> None:
        """Refine zones in-place for all annotations."""
        detail_map = {d.beam_id: d for d in details}
        for beam_id, anns in beam_annotations.items():
            detail = detail_map.get(beam_id)
            if detail is None:
                continue
            self._refine_beam(detail, anns)

    # ──────────────────────────────────────────────────────────────────────────
    def _refine_beam(
        self, detail: BeamDetail, anns: List[ReinforcementAnnotation]
    ) -> None:
        depth_mm = float(detail.section.get("depth_mm", 750.0) or 750.0)
        top_threshold    =  TOP_FRACTION    * depth_mm
        bottom_threshold = -BOTTOM_FRACTION * depth_mm

        for ann in anns:
            if not ann.is_reinforcement:
                continue
            dy = ann.dy_from_centroid

            if dy > top_threshold:
                ann.position_zone = ZONE_TOP
            elif dy < bottom_threshold:
                ann.position_zone = ZONE_BOTTOM
            else:
                # If already flagged as TOP or BOTTOM from initial parse, keep it
                if ann.position_zone not in (ZONE_TOP, ZONE_BOTTOM):
                    ann.position_zone = ZONE_UNKNOWN
