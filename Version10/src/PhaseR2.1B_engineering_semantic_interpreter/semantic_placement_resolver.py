"""
semantic_placement_resolver.py — Resolve placement from role, modifiers and zone.
MODEL_VERSION: 7.11.0

Placement examples:
  NEAR_FACE, FAR_FACE, BOTH_FACE, SIDE_FACE, TOP, BOTTOM, UNKNOWN

Priority:
  1. Explicit face modifier (O.E.F., BOTH FACE, N.F., F.F.)
  2. Role signal (SIDE_FACE role → SIDE_FACE placement)
  3. Position zone (TOP_ZONE → TOP, BOTTOM_ZONE → BOTTOM)
  4. UNKNOWN
"""
from __future__ import annotations

from typing import List

from .semantic_models import (
    SemanticContext,
    SemanticModifier,
    ROLE_SIDE_FACE,
    ROLE_STIRRUP,
    PLACEMENT_NEAR_FACE,
    PLACEMENT_FAR_FACE,
    PLACEMENT_BOTH_FACE,
    PLACEMENT_SIDE_FACE,
    PLACEMENT_TOP,
    PLACEMENT_BOTTOM,
    PLACEMENT_UNKNOWN,
    MODIFIER_ONE_EACH_FACE,
    MODIFIER_BOTH_FACES,
    MODIFIER_NEAR_FACE,
    MODIFIER_FAR_FACE,
)

_ZONE_TO_PLACEMENT = {
    "TOP_ZONE":        PLACEMENT_TOP,
    "BOTTOM_ZONE":     PLACEMENT_BOTTOM,
    "SIDE_ZONE":       PLACEMENT_SIDE_FACE,
    "TRANSVERSE_ZONE": PLACEMENT_UNKNOWN,
    "UNKNOWN_ZONE":    PLACEMENT_UNKNOWN,
}

_MODIFIER_TO_PLACEMENT = {
    MODIFIER_ONE_EACH_FACE: PLACEMENT_BOTH_FACE,
    MODIFIER_BOTH_FACES:    PLACEMENT_BOTH_FACE,
    MODIFIER_NEAR_FACE:     PLACEMENT_NEAR_FACE,
    MODIFIER_FAR_FACE:      PLACEMENT_FAR_FACE,
}


class SemanticPlacementResolver:
    """
    Determine the placement of reinforcement bars from available evidence.

    Returns (placement: str, notes: list[str]).
    """

    def resolve(
        self,
        ctx: SemanticContext,
        modifiers: List[SemanticModifier],
        semantic_role: str,
    ) -> tuple:
        notes = []

        # ── Priority 1: Explicit face modifier ───────────────────────────────
        for mod in modifiers:
            if mod.canonical in _MODIFIER_TO_PLACEMENT:
                placement = _MODIFIER_TO_PLACEMENT[mod.canonical]
                notes.append(
                    f"Placement from modifier {mod.canonical} → {placement}"
                )
                return placement, notes

        # ── Priority 2: Role signal ──────────────────────────────────────────
        if semantic_role == ROLE_SIDE_FACE:
            # S.F.R. without explicit face modifier → default BOTH_FACE
            notes.append("Placement: SIDE_FACE role → BOTH_FACE (default)")
            return PLACEMENT_BOTH_FACE, notes

        if semantic_role == ROLE_STIRRUP:
            notes.append("Placement: STIRRUP → UNKNOWN (handled by stirrup engine)")
            return PLACEMENT_UNKNOWN, notes

        # ── Priority 3: Position zone ────────────────────────────────────────
        placement = _ZONE_TO_PLACEMENT.get(ctx.position_zone, PLACEMENT_UNKNOWN)
        notes.append(f"Placement from zone {ctx.position_zone} → {placement}")
        return placement, notes
