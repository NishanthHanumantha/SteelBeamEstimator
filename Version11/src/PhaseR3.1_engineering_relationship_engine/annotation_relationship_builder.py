"""
annotation_relationship_builder.py — Associate annotations with leaders.
MODEL_VERSION: 8.1.0

Association algorithm:
  For each annotation (known from reinforcement_annotations.json):
    1. Find LEADER whose TAIL is nearest to the annotation insert position
    2. Accept if distance ≤ LEADER_TAIL_TO_ANN_MAX_MM
    3. Build AnnotationRelationship

Verified distance from DXF analysis: ~62.7mm for confident matches.
Threshold set to 300mm to handle varied drawing styles generically.

No hardcoding of beam names or annotation IDs.
"""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional

from . import LEADER_TAIL_TO_ANN_MAX_MM
from .relationship_models import (
    CONF_HIGH, CONF_MEDIUM, CONF_LOW, CONF_UNKNOWN,
    AnnotationRelationship, LeaderObject,
)


def _dist(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


class AnnotationRelationshipBuilder:
    """
    Associate every annotation with its nearest leader.
    """

    def build(
        self,
        annotations: Dict[str, Dict[str, Any]],   # annotation_id → {x, y, beam_id}
        leaders:     List[LeaderObject],
    ) -> List[AnnotationRelationship]:
        """
        Returns one AnnotationRelationship per annotation.
        Unmatched annotations get a NONE relationship with UNKNOWN confidence.
        """
        relationships: List[AnnotationRelationship] = []

        # Index leaders by beam for efficiency
        leaders_by_beam: Dict[str, List[LeaderObject]] = {}
        for ldr in leaders:
            leaders_by_beam.setdefault(ldr.beam_id, []).append(ldr)

        for ann_id, ann_data in annotations.items():
            ann_x   = float(ann_data.get("x") or 0.0)
            ann_y   = float(ann_data.get("y") or 0.0)
            beam_id = str(ann_data.get("beam_id") or "UNKNOWN")

            # Search leaders for this beam (+ UNKNOWN beam leaders as fallback)
            candidate_leaders = (
                leaders_by_beam.get(beam_id, []) +
                leaders_by_beam.get("UNKNOWN", [])
            )

            best_ldr  = None
            best_dist = float("inf")
            for ldr in candidate_leaders:
                d = _dist((ann_x, ann_y), (ldr.tail_x, ldr.tail_y))
                if d < best_dist:
                    best_dist = d
                    best_ldr  = ldr

            if best_ldr and best_dist <= LEADER_TAIL_TO_ANN_MAX_MM:
                conf = (
                    CONF_HIGH   if best_dist <= 100   else
                    CONF_MEDIUM if best_dist <= 200   else
                    CONF_LOW
                )
                reason = (
                    f"Leader tail {best_dist:.1f}mm from annotation"
                    f" (threshold={LEADER_TAIL_TO_ANN_MAX_MM}mm)"
                )
            else:
                best_ldr  = None
                best_dist = float("inf") if not best_ldr else best_dist
                conf      = CONF_UNKNOWN
                reason    = (
                    f"No leader within {LEADER_TAIL_TO_ANN_MAX_MM}mm "
                    f"(nearest={best_dist:.1f}mm)"
                    if candidate_leaders
                    else "No leaders for this beam"
                )

            relationships.append(AnnotationRelationship(
                relationship_id     = f"REL::{uuid.uuid4().hex[:8].upper()}",
                beam_id             = beam_id,
                annotation_id       = ann_id,
                leader_id           = best_ldr.leader_id if best_ldr else None,
                arrow_id            = None,  # filled in by orchestrator
                physical_bar_id     = None,  # filled in after bar detection
                leader_distance     = round(best_dist, 2) if best_dist < 1e9 else -1.0,
                bar_distance        = -1.0,
                relationship_confidence = conf,
                relationship_reason     = reason,
            ))

        return relationships
