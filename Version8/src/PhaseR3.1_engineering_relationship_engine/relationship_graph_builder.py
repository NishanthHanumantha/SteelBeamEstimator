"""
relationship_graph_builder.py — Build the complete drawing relationship graph.
MODEL_VERSION: 8.1.0

Assembles the final EngineeringDrawingRelationship objects by combining:
  - AnnotationRelationship (annotation → leader → arrow)
  - PhysicalBar (leader tip → bar)
  - SupportCrossing (bar → supports)
  - Bar extent evidence

Each node in the graph has a reason and confidence.
Intent remains UNKNOWN.
"""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional

from . import LEADER_TIP_TO_BAR_MAX_MM
from .relationship_models import (
    CONF_HIGH, CONF_MEDIUM, CONF_LOW, CONF_UNKNOWN,
    AnnotationRelationship, ArrowObject, EngineeringDrawingRelationship,
    LeaderObject, PhysicalBar, SupportCrossing,
    EXTENT_UNKNOWN,
)


def _euclidean(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def _conf_score(c: str) -> float:
    return {CONF_HIGH: 1.0, CONF_MEDIUM: 0.6, CONF_LOW: 0.3, CONF_UNKNOWN: 0.0}.get(c, 0.0)


def _score_to_conf(s: float) -> str:
    return CONF_HIGH if s >= 0.8 else CONF_MEDIUM if s >= 0.5 else CONF_LOW


class RelationshipGraphBuilder:
    """
    Assemble EngineeringDrawingRelationship for every annotation.
    """

    def build(
        self,
        ann_rels:       List[AnnotationRelationship],
        leaders_by_id:  Dict[str, LeaderObject],
        arrows_by_ldr:  Dict[str, ArrowObject],      # leader_id → ArrowObject
        bars_by_id:     Dict[str, PhysicalBar],
        crossings_by_bar:Dict[str, List[SupportCrossing]],
        extents_by_bar: Dict[str, tuple],            # bar_id → (label, conf, reason, left, right)
        detector,                                    # PhysicalBarDetector for tip→bar match
        bars_flat:      List[PhysicalBar],
        geo_context_by_ann: Dict[str, Any],          # annotation_id → R.3 GeometryContext
    ) -> List[EngineeringDrawingRelationship]:

        result: List[EngineeringDrawingRelationship] = []

        for ann_rel in ann_rels:
            ann_id  = ann_rel.annotation_id
            beam_id = ann_rel.beam_id
            notes   = [f"AnnotationRelationship: {ann_rel.relationship_reason}"]
            conv    = []

            # ── Leader resolution ─────────────────────────────────────────────
            leader      = leaders_by_id.get(ann_rel.leader_id) if ann_rel.leader_id else None
            leader_len  = leader.leader_length if leader else 0.0

            # ── Arrow resolution ──────────────────────────────────────────────
            arrow     = arrows_by_ldr.get(ann_rel.leader_id) if ann_rel.leader_id else None
            arrow_id  = arrow.arrow_id if arrow else None
            if arrow:
                conv.append(
                    f"Arrow direction: {arrow.direction} "
                    f"(annotation on {arrow.annotation_side} side of bar)"
                )

            # ── Physical bar association via leader tip ────────────────────────
            bar       = None
            bar_dist  = -1.0
            if leader:
                bar = detector.nearest_bar_to_point(
                    leader.tip_x, leader.tip_y,
                    [b for b in bars_flat if b.beam_id == beam_id or b.beam_id == "UNKNOWN"],
                    LEADER_TIP_TO_BAR_MAX_MM,
                )
                if bar:
                    bar_dist = _euclidean(
                        (leader.tip_x, leader.tip_y),
                        (bar.start_x,  bar.y_position),
                    )
                    notes.append(
                        f"Leader tip->bar distance: {bar_dist:.1f}mm "
                        f"(bar {bar.bar_id})"
                    )
                    conv.append(
                        f"Bar vertical placement: {bar.vertical_placement} "
                        f"(y={bar.y_position:.0f}, bar_len={bar.bar_length_mm:.0f}mm)"
                    )
                else:
                    notes.append(
                        f"No physical bar within {LEADER_TIP_TO_BAR_MAX_MM}mm of leader tip"
                    )

            # ── Extent evidence ───────────────────────────────────────────────
            ext_label  = EXTENT_UNKNOWN
            ext_conf   = CONF_UNKNOWN
            ext_reason = "No physical bar resolved"
            left_x     = False
            right_x    = False
            bar_len    = 0.0
            bar_ns     = 0.0
            bar_ne     = 0.0
            placement  = "UNKNOWN"
            support_ids: List[str] = []
            sup_crossings = 0

            if bar:
                bar_id = bar.bar_id
                ext_label, ext_conf, ext_reason, left_x, right_x = extents_by_bar.get(
                    bar_id, (EXTENT_UNKNOWN, CONF_UNKNOWN, "extent not computed", False, False)
                )
                bar_len    = bar.bar_length_mm
                bar_ns     = bar.normalized_start
                bar_ne     = bar.normalized_end
                placement  = bar.vertical_placement

                crossings = crossings_by_bar.get(bar_id, [])
                support_ids = list({c.support_id for c in crossings if c.crosses})
                sup_crossings = sum(1 for c in crossings if c.crosses)

                notes.append(f"Extent: {ext_label} (conf={ext_conf})")
                notes.append(f"Support crossings: {sup_crossings}")

            # ── R.3 geometry context link ─────────────────────────────────────
            geo_ctx = geo_context_by_ann.get(ann_id)
            geo_ctx_id = f"GEO::{ann_id}" if geo_ctx else None
            if geo_ctx:
                notes.append(
                    f"R.3 geometry context: pos={geo_ctx.get('normalized_position',0):.3f} "
                    f"zone={geo_ctx.get('span_zone','?')}"
                )

            # ── Overall relationship confidence ───────────────────────────────
            scores = [
                _conf_score(ann_rel.relationship_confidence),
                _conf_score(ext_conf),
            ]
            if arrow:
                scores.append(_conf_score(arrow.confidence))
            if bar:
                scores.append(_conf_score(bar.bar_confidence))
            overall_score = sum(scores) / len(scores)
            overall_conf  = _score_to_conf(overall_score)

            overall_reason = (
                f"Leader={bool(leader)}, Arrow={bool(arrow)}, "
                f"Bar={bool(bar)}, Extent={ext_label}"
            )

            result.append(EngineeringDrawingRelationship(
                relationship_id       = f"EREL::{uuid.uuid4().hex[:10].upper()}",
                beam_id               = beam_id,
                annotation_id         = ann_id,
                leader_id             = ann_rel.leader_id,
                arrow_id              = arrow_id,
                physical_bar_id       = bar.bar_id if bar else None,
                projection_id         = f"PROJ::{ann_id}",
                geometry_context_id   = geo_ctx_id,
                support_ids           = support_ids,
                extent_label          = ext_label,
                extent_confidence     = ext_conf,
                extent_reason         = ext_reason,
                support_crossings     = sup_crossings,
                left_support_crossed  = left_x,
                right_support_crossed = right_x,
                leader_length         = round(leader_len, 2),
                bar_length            = round(bar_len, 2),
                bar_normalized_start  = round(bar_ns, 4),
                bar_normalized_end    = round(bar_ne, 4),
                bar_vertical_placement= placement,
                relationship_confidence= overall_conf,
                relationship_reason    = overall_reason,
                convention_evidence    = conv,
                geometry_notes         = notes,
            ))

        return result
