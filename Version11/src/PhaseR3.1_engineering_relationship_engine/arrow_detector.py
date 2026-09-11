"""
arrow_detector.py — Detect and characterise arrowheads from leaders.
MODEL_VERSION: 8.1.0

LEADER entities with has_arrowhead=1 have an implicit arrowhead at their
first vertex (tip). This module extracts ArrowObject from each qualified leader.

Arrow direction convention (geometric, not intent):
  - Arrow pointing UP   → the bar is ABOVE the annotation text
  - Arrow pointing DOWN → the bar is BELOW the annotation text
  - This provides a geometric PLACEMENT hint only

No engineering classification. Placement evidence only.
"""
from __future__ import annotations

import math
import uuid
from typing import List

from .relationship_models import (
    CONF_HIGH, CONF_MEDIUM, CONF_LOW,
    ArrowObject, LeaderObject,
)


def _arrow_direction(leader: LeaderObject) -> str:
    """
    Determine direction arrow points (from annotation toward bar).
    Uses tip_direction (already computed in LeaderDiscovery).
    """
    return leader.tip_direction


def _annotation_side(direction: str) -> str:
    """
    Given arrow points in direction D, annotation is on opposite side.
    """
    opposites = {"UP": "BELOW", "DOWN": "ABOVE", "LEFT": "RIGHT", "RIGHT": "LEFT"}
    return opposites.get(direction, "UNKNOWN")


class ArrowDetector:
    """
    Build ArrowObject for every leader that has an arrowhead.
    """

    def detect(self, leaders: List[LeaderObject]) -> List[ArrowObject]:
        arrows: List[ArrowObject] = []

        for ldr in leaders:
            if not ldr.has_arrowhead:
                continue

            direction   = _arrow_direction(ldr)
            ann_side    = _annotation_side(direction)
            confidence  = CONF_HIGH if ldr.leader_length > 50 else CONF_MEDIUM

            arrows.append(ArrowObject(
                arrow_id        = f"ARR::{uuid.uuid4().hex[:8].upper()}",
                leader_id       = ldr.leader_id,
                beam_id         = ldr.beam_id,
                tip_x           = ldr.tip_x,
                tip_y           = ldr.tip_y,
                direction       = direction,
                annotation_side = ann_side,
                confidence      = confidence,
            ))

        return arrows
