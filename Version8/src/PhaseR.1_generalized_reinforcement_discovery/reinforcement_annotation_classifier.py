"""
reinforcement_annotation_classifier.py — Classify annotations by role.

Uses engineering rules only.  No hardcoded beam IDs.

Classification logic:
  1. Stirrups already detected in annotation_discovery (role="STIRRUP").
  2. For rebar annotations, role is assigned from:
     a. Position zone (TOP_ZONE → candidate top, BOTTOM_ZONE → candidate bottom)
     b. Diameter (large → MAIN, small → EXTRA/SPACER)
     c. Quantity ordering within the beam (largest group = MAIN)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List

from .reinforcement_models import (
    ReinforcementAnnotation,
    ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN,
    ROLE_TOP_EXTRA, ROLE_BOTTOM_EXTRA,
    ROLE_STIRRUP, ROLE_SPACER,
    ROLE_DEVELOPMENT, ROLE_UNKNOWN,
    ZONE_TOP, ZONE_BOTTOM, ZONE_UNKNOWN,
)

log = logging.getLogger(__name__)

_SPACER_DIAMETERS   = {8, 10, 12}
_STIRRUP_ROLE       = ROLE_STIRRUP


class ReinforcementAnnotationClassifier:
    """
    Assigns semantic roles to ReinforcementAnnotation objects.

    Strategy per beam:
      - Already-classified stirrups are kept.
      - TOP_ZONE annotations:
          * Largest-quantity / largest-diameter group → TOP_MAIN
          * Others → TOP_EXTRA
      - BOTTOM_ZONE annotations:
          * Largest-quantity / largest-diameter group → BOTTOM_MAIN
          * Others → BOTTOM_EXTRA / SPACER (if small diameter)
      - UNKNOWN_ZONE annotations → heuristic based on diameter
    """

    def __init__(self, config: dict):
        self._main_dia   = float(config.get("classification", {}).get("main_bar_min_diameter", 12))
        self._spacer_dia = float(config.get("classification", {}).get("spacer_bar_max_diameter", 12))

    # ──────────────────────────────────────────────────────────────────────────
    def classify(
        self,
        beam_annotations: Dict[str, List[ReinforcementAnnotation]],
    ) -> Dict[str, List[ReinforcementAnnotation]]:
        """Classify all annotations for all beams in-place, return same dict."""
        for beam_id, anns in beam_annotations.items():
            self._classify_beam(beam_id, anns)
        return beam_annotations

    # ──────────────────────────────────────────────────────────────────────────
    def _classify_beam(self, beam_id: str, anns: List[ReinforcementAnnotation]) -> None:
        rebar = [a for a in anns if a.is_reinforcement and a.role != _STIRRUP_ROLE]
        top   = [a for a in rebar if a.position_zone == ZONE_TOP]
        bot   = [a for a in rebar if a.position_zone == ZONE_BOTTOM]
        unk   = [a for a in rebar if a.position_zone == ZONE_UNKNOWN]

        self._assign_zone(top,  ROLE_TOP_MAIN,    ROLE_TOP_EXTRA)
        self._assign_zone(bot,  ROLE_BOTTOM_MAIN, ROLE_BOTTOM_EXTRA)
        self._assign_unknown(unk)

    def _assign_zone(
        self,
        group: List[ReinforcementAnnotation],
        main_role: str,
        extra_role: str,
    ) -> None:
        if not group:
            return
        # Sort descending: larger quantity then larger diameter = "more main"
        ranked = sorted(group, key=lambda a: (a.quantity, a.diameter_mm), reverse=True)
        ranked[0].role = main_role
        for ann in ranked[1:]:
            if ann.diameter_mm <= self._spacer_dia:
                ann.role = ROLE_SPACER
            else:
                ann.role = extra_role

    def _assign_unknown(self, group: List[ReinforcementAnnotation]) -> None:
        """Annotations in UNKNOWN_ZONE are heuristically classified."""
        for ann in group:
            if ann.diameter_mm < self._main_dia:
                ann.role = ROLE_SPACER
            else:
                # Assume bottom extra if we can't determine zone
                ann.role = ROLE_BOTTOM_EXTRA
