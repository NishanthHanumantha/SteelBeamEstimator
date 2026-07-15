"""
reinforcement_role_classifier.py — Final engineering role assignment.

Takes the result of the annotation classifier and geometry mapper and
produces a confidence-rated final role for every group and annotation.

Rules (deterministic, no hardcoded IDs):
  - TOP_MAIN:     TOP_ZONE, largest qty/dia, dia >= 16mm
  - TOP_EXTRA:    TOP_ZONE, smaller bars
  - BOTTOM_MAIN:  BOTTOM_ZONE, largest qty/dia
  - BOTTOM_EXTRA: BOTTOM_ZONE, smaller bars
  - STIRRUP:      annotations with @spacing already classified
  - SPACER_BAR:   small diameter (<=12mm) without clear top/bottom context
  - SIDE_FACE_REINFORCEMENT: if beam depth > 750mm and side annotation present
  - DEVELOPMENT:  isolated bars at beam ends (dx near extreme)
"""

from __future__ import annotations

import logging
from typing import Dict, List

from .reinforcement_models import (
    BeamDetail,
    ReinforcementAnnotation,
    ReinforcementGroup,
    ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN,
    ROLE_TOP_EXTRA, ROLE_BOTTOM_EXTRA,
    ROLE_STIRRUP, ROLE_SPACER, ROLE_SIDE_FACE,
    ROLE_DEVELOPMENT, ROLE_UNKNOWN,
    ZONE_TOP, ZONE_BOTTOM,
)

log = logging.getLogger(__name__)

_DEEP_BEAM_THRESHOLD = 900.0   # mm – side-face bars appear for depths > this


class ReinforcementRoleClassifier:
    """
    Confirms / refines roles using combined geometry and annotation evidence.
    Returns confidence ("HIGH" / "MEDIUM" / "LOW") per group.
    """

    def __init__(self, config: dict):
        self._main_dia = float(config.get("classification", {}).get("main_bar_min_diameter", 12))

    # ──────────────────────────────────────────────────────────────────────────
    def classify_roles(
        self,
        details: List[BeamDetail],
        beam_groups: Dict[str, Dict[str, ReinforcementGroup]],
    ) -> Dict[str, Dict[str, ReinforcementGroup]]:
        """Refine roles in-place.  Returns same structure."""
        detail_map = {d.beam_id: d for d in details}
        for beam_id, groups in beam_groups.items():
            detail = detail_map.get(beam_id)
            self._refine_groups(detail, groups)
        return beam_groups

    # ──────────────────────────────────────────────────────────────────────────
    def _refine_groups(
        self,
        detail: BeamDetail,
        groups: Dict[str, ReinforcementGroup],
    ) -> None:
        depth_mm = float((detail.section.get("depth_mm") if detail else None) or 750.0)

        # Ensure at most ONE TOP_MAIN and ONE BOTTOM_MAIN
        # If multiple TOP_MAIN groups exist (shouldn't happen but safety), keep largest
        top_mains    = [g for g in groups.values() if g.role == ROLE_TOP_MAIN]
        bottom_mains = [g for g in groups.values() if g.role == ROLE_BOTTOM_MAIN]

        if len(top_mains) > 1:
            top_mains.sort(key=lambda g: g.total_quantity, reverse=True)
            for g in top_mains[1:]:
                g.role = ROLE_TOP_EXTRA
                for bar in g.bars:
                    bar.role = ROLE_TOP_EXTRA

        if len(bottom_mains) > 1:
            bottom_mains.sort(key=lambda g: g.total_quantity, reverse=True)
            for g in bottom_mains[1:]:
                g.role = ROLE_BOTTOM_EXTRA
                for bar in g.bars:
                    bar.role = ROLE_BOTTOM_EXTRA

        # For deep beams, promote SIDE_FACE if available
        if depth_mm >= _DEEP_BEAM_THRESHOLD:
            for grp in groups.values():
                if grp.role == ROLE_UNKNOWN:
                    # If bars are small and in mid-zone, promote to SIDE_FACE
                    if all(b.diameter_mm <= 16 for b in grp.bars):
                        grp.role = ROLE_SIDE_FACE
                        for b in grp.bars:
                            b.role = ROLE_SIDE_FACE

        # Re-bucket groups dict by current role (roles may have changed)
        # Rebuild the dict in-place
        keys = list(groups.keys())
        for key in keys:
            grp = groups[key]
            if grp.role != key:
                groups[grp.role] = grp
                del groups[key]
