"""
placement_normalizer.py — Normalize placement from R.2.1B to R.2.1C model.
MODEL_VERSION: 7.12.0

Placement is observable and preserved. It is derived from:
  - Position zone (TOP_ZONE → TOP)
  - Explicit modifier (O.E.F., BOTH FACE → BOTH_FACE)
  - Side face role → SIDE

Placement is NOT inferred. Only observable evidence is used.

Reference drawing observations:
  - B1: "Top Bar Extra" bars appear at TOP, even though their INTENT is TOP_EXTRA
  - B2: "Bottom Bar Extra" bars appear at BOTTOM, even though INTENT is BOTTOM_EXTRA
  - Placement is always independently confirmable from position zone alone.
"""
from __future__ import annotations

from typing import Any, Dict

from .fact_models import (
    PLACEMENT_TOP,
    PLACEMENT_BOTTOM,
    PLACEMENT_SIDE,
    PLACEMENT_BOTH_FACE,
    PLACEMENT_UNKNOWN,
    ROLE_SIDE_FACE,
)

_ESO_PLACEMENT_MAP: Dict[str, str] = {
    "TOP":         PLACEMENT_TOP,
    "BOTTOM":      PLACEMENT_BOTTOM,
    "SIDE":        PLACEMENT_SIDE,
    "SIDE_FACE":   PLACEMENT_SIDE,
    "BOTH_FACE":   PLACEMENT_BOTH_FACE,
    "BOTH_FACES":  PLACEMENT_BOTH_FACE,
    "NEAR_FACE":   PLACEMENT_SIDE,
    "FAR_FACE":    PLACEMENT_SIDE,
    "UNKNOWN":     PLACEMENT_UNKNOWN,
}


class PlacementNormalizer:
    """
    Normalize the placement from a R.2.1B semantic object.

    Returns (placement: str, notes: list[str]).
    """

    def normalize(self, eso: Dict[str, Any], role: str) -> tuple:
        notes = []
        eso_placement = eso.get("placement", "UNKNOWN") or "UNKNOWN"
        placement = _ESO_PLACEMENT_MAP.get(eso_placement, PLACEMENT_UNKNOWN)

        # SIDE_FACE role always implies SIDE or BOTH_FACE placement
        if role == ROLE_SIDE_FACE and placement not in (PLACEMENT_SIDE, PLACEMENT_BOTH_FACE):
            placement = PLACEMENT_BOTH_FACE
            notes.append(
                f"Placement overridden to BOTH_FACE: SIDE_FACE role implies bilateral placement"
            )

        notes.append(
            f"Placement normalized from ESO.placement={eso_placement!r} -> {placement}"
        )
        return placement, notes
