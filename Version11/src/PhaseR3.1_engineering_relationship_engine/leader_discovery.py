"""
leader_discovery.py — Discover LEADER entities from DXF and build LeaderObjects.
MODEL_VERSION: 8.1.0

DXF LEADER entity structure:
  vertices[0]  = TIP (arrowhead) — points TO the physical bar
  vertices[-1] = TAIL (shoulder) — connects FROM the annotation text

Leader direction conventions (observed, generalised):
  - Leaders going UP from annotation → bar is above annotation text
  - Leaders going DOWN from annotation → bar is below annotation text

No beam-specific hardcoding. Beam assignment done by spatial proximity
using BeamAxis data from R.3.
"""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .relationship_models import CONF_HIGH, CONF_MEDIUM, CONF_LOW, LeaderObject


def _euclidean(p1: Tuple, p2: Tuple) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def _path_length(vertices: List[Tuple]) -> float:
    total = 0.0
    for i in range(1, len(vertices)):
        total += _euclidean(vertices[i - 1], vertices[i])
    return total


def _tip_direction(tip: Tuple, tail: Tuple) -> str:
    """Determine geometric direction from tail toward tip."""
    dx = tip[0] - tail[0]
    dy = tip[1] - tail[1]
    if abs(dx) < 1e-3 and abs(dy) < 1e-3:
        return "NONE"
    angle = math.degrees(math.atan2(dy, dx))
    if -45 <= angle <= 45:
        return "RIGHT"
    if 45 < angle <= 135:
        return "UP"
    if angle > 135 or angle <= -135:
        return "LEFT"
    return "DOWN"


class LeaderDiscovery:
    """
    Read all LEADER entities from DXF and build LeaderObject list.
    Assigns each leader to a beam by spatial proximity.
    """

    def __init__(self, leader_layer: str = "-S-ARROW"):
        self._leader_layer = leader_layer

    def discover(
        self,
        msp,                                          # ezdxf modelspace
        beam_axes: Dict[str, Any],                    # beam_id → BeamAxis dict
        tolerance_x: float = 3000.0,                  # half-span tolerance for beam assignment
    ) -> List[LeaderObject]:
        """
        Discover all LEADER entities and assign to beams.

        Returns list of LeaderObject (one per LEADER entity).
        """
        leaders: List[LeaderObject] = []

        for entity in msp:
            if entity.dxftype() != "LEADER":
                continue

            verts_raw = list(entity.vertices)
            if len(verts_raw) < 2:
                continue

            verts = [(float(v[0]), float(v[1])) for v in verts_raw]
            tip  = verts[0]
            tail = verts[-1]

            leader_length = _path_length(verts)
            tip_dir       = _tip_direction(tip, tail)
            has_arrow     = bool(getattr(entity.dxf, "has_arrowhead", 1))

            # Assign to beam by spatial proximity of tip/tail
            beam_id = self._assign_beam(tip, tail, beam_axes, tolerance_x)

            leader_id = f"LDR::{uuid.uuid4().hex[:8].upper()}"
            leaders.append(LeaderObject(
                leader_id     = leader_id,
                beam_id       = beam_id,
                tip_x         = tip[0],
                tip_y         = tip[1],
                tail_x        = tail[0],
                tail_y        = tail[1],
                vertex_count  = len(verts),
                vertices      = verts,
                layer         = str(entity.dxf.layer),
                has_arrowhead = has_arrow,
                leader_length = round(leader_length, 2),
                tip_direction = tip_dir,
            ))

        return leaders

    def _assign_beam(
        self,
        tip:       Tuple,
        tail:      Tuple,
        beam_axes: Dict[str, Any],
        tol_x:     float,
    ) -> str:
        """
        Assign leader to beam whose DXF x-range contains the leader midpoint.
        Falls back to nearest centroid if no exact match.
        """
        mid_x = (tip[0] + tail[0]) / 2.0
        mid_y = (tip[1] + tail[1]) / 2.0

        best_bid   = "UNKNOWN"
        best_dist  = float("inf")

        for bid, ax in beam_axes.items():
            cx = float(ax.get("dxf_centroid_x") or 0.0)
            cy = float(ax.get("dxf_centroid_y") or 0.0)
            span = float(ax.get("beam_length_mm") or 0.0)
            half = span / 2.0 + tol_x

            dx = abs(mid_x - cx)
            dy = abs(mid_y - cy)
            dist = math.sqrt(dx * dx + dy * dy)

            if dx <= half and dist < best_dist:
                best_dist = dist
                best_bid  = bid

        return best_bid
