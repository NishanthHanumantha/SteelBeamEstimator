"""
intent_normalizer.py — Remove premature engineering intent.
MODEL_VERSION: 7.12.0

This is the core of Phase R.2.1C.

R.2.1B assigned meanings like TOP_MAIN, BOTTOM_MAIN purely from position zone.
This is premature because:

  Without geometry, 2-Y16 at TOP could be:
    - TOP_MAIN          (runs full span, no curtailment)
    - TOP_EXTRA         (short bar, only over supports)
    - CONTINUOUS_TOP    (same bar crosses multiple spans)
    - SUPPORT_TOP       (bar provided specifically at support zone)

  Only bar extent + support location (from R.3) can resolve this.

Reference drawings:
  B1: "Top Bar Extra" label on bars at both ends of span that are shorter.
      2-Y16 at TOP near supports ≠ 2-Y16 at TOP for full span.
  B2: "Bottom Bar Extra" = 2-Y20 short bars at supports, not mid-span.
      2-Y12 mid-span = actual "Bottom Bar" for bending resistance.
  B8-B10: Same 2-Y16 appears at TOP across three beam spans,
           showing continuous reinforcement pattern.

Therefore all intent is set to UNKNOWN here.

Only two exceptions where candidates are definitively singular:
  STIRRUP     → only candidate is STIRRUP     (transverse, not affected by span)
  SIDE_FACE   → only candidate is SIDE_FACE_REINFORCEMENT (S.F.R. explicit)

Engineering note template for each case explains WHY intent is deferred.
"""
from __future__ import annotations

from typing import List

from .fact_models import (
    INTENT_UNKNOWN,
    ROLE_MAIN_BAR,
    ROLE_EXTRA_BAR,
    ROLE_STIRRUP,
    ROLE_SPACER_BAR,
    ROLE_SIDE_FACE,
    ROLE_UNKNOWN,
    PLACEMENT_TOP,
    PLACEMENT_BOTTOM,
    PLACEMENT_SIDE,
    PLACEMENT_BOTH_FACE,
    PLACEMENT_UNKNOWN,
    CANDIDATE_TOP_MAIN,
    CANDIDATE_TOP_EXTRA,
    CANDIDATE_CONTINUOUS_TOP,
    CANDIDATE_SUPPORT_TOP,
    CANDIDATE_CURTAILMENT_TOP,
    CANDIDATE_BOTTOM_MAIN,
    CANDIDATE_BOTTOM_EXTRA,
    CANDIDATE_CONTINUOUS_BOTTOM,
    CANDIDATE_SUPPORT_BOTTOM,
    CANDIDATE_CURTAILMENT_BOTTOM,
    CANDIDATE_CURTAILMENT_BAR,
    CANDIDATE_SUPPORT_BAR,
    CANDIDATE_SPACER_BAR,
    CANDIDATE_CHAIR_BAR,
    CANDIDATE_STIRRUP,
    CANDIDATE_SIDE_FACE_REINF,
    CANDIDATE_UNKNOWN,
)

# ── Engineering geometry requirements per role ────────────────────────────────
_GEOMETRY_REASON = {
    ROLE_MAIN_BAR: (
        "Bar extent (start/end offset) and support location required to distinguish "
        "MAIN (full-span) from EXTRA (support-zone only) vs CONTINUOUS (multi-span)."
    ),
    ROLE_EXTRA_BAR: (
        "Bar curtailment point required to confirm EXTRA vs CURTAILMENT_BAR. "
        "Support width needed to confirm SUPPORT_BAR."
    ),
    ROLE_SPACER_BAR: (
        "Position confirms SPACER function; CHAIR_BAR variant needs beam width geometry."
    ),
    ROLE_UNKNOWN: (
        "Role itself is unknown — geometry needed to classify."
    ),
}

# ── Candidate table: (role, placement) → candidates ──────────────────────────
# Derived from reference drawings B1, B2, B8-B10 engineering rules.
_CANDIDATE_TABLE: dict = {

    # MAIN_BAR ---
    (ROLE_MAIN_BAR, PLACEMENT_TOP): [
        CANDIDATE_TOP_MAIN,
        CANDIDATE_TOP_EXTRA,
        CANDIDATE_CONTINUOUS_TOP,
        CANDIDATE_SUPPORT_TOP,
    ],
    (ROLE_MAIN_BAR, PLACEMENT_BOTTOM): [
        CANDIDATE_BOTTOM_MAIN,
        CANDIDATE_BOTTOM_EXTRA,
        CANDIDATE_CONTINUOUS_BOTTOM,
        CANDIDATE_SUPPORT_BOTTOM,
    ],
    (ROLE_MAIN_BAR, PLACEMENT_UNKNOWN): [
        CANDIDATE_TOP_MAIN,
        CANDIDATE_BOTTOM_MAIN,
        CANDIDATE_TOP_EXTRA,
        CANDIDATE_BOTTOM_EXTRA,
        CANDIDATE_CONTINUOUS_TOP,
        CANDIDATE_CONTINUOUS_BOTTOM,
    ],

    # EXTRA_BAR ---
    (ROLE_EXTRA_BAR, PLACEMENT_TOP): [
        CANDIDATE_TOP_EXTRA,
        CANDIDATE_CURTAILMENT_TOP,
        CANDIDATE_SUPPORT_TOP,
    ],
    (ROLE_EXTRA_BAR, PLACEMENT_BOTTOM): [
        CANDIDATE_BOTTOM_EXTRA,
        CANDIDATE_CURTAILMENT_BOTTOM,
        CANDIDATE_SUPPORT_BOTTOM,
        CANDIDATE_SUPPORT_BAR,
    ],
    (ROLE_EXTRA_BAR, PLACEMENT_UNKNOWN): [
        CANDIDATE_TOP_EXTRA,
        CANDIDATE_BOTTOM_EXTRA,
        CANDIDATE_CURTAILMENT_BAR,
        CANDIDATE_SUPPORT_BAR,
    ],

    # STIRRUP — settled (transverse, geometry-independent)
    (ROLE_STIRRUP, PLACEMENT_UNKNOWN): [CANDIDATE_STIRRUP],
    (ROLE_STIRRUP, PLACEMENT_TOP):     [CANDIDATE_STIRRUP],
    (ROLE_STIRRUP, PLACEMENT_BOTTOM):  [CANDIDATE_STIRRUP],
    (ROLE_STIRRUP, PLACEMENT_SIDE):    [CANDIDATE_STIRRUP],

    # SPACER_BAR
    (ROLE_SPACER_BAR, PLACEMENT_TOP):    [CANDIDATE_SPACER_BAR, CANDIDATE_CHAIR_BAR],
    (ROLE_SPACER_BAR, PLACEMENT_BOTTOM): [CANDIDATE_SPACER_BAR, CANDIDATE_CHAIR_BAR],
    (ROLE_SPACER_BAR, PLACEMENT_UNKNOWN):[CANDIDATE_SPACER_BAR, CANDIDATE_CHAIR_BAR],

    # SIDE_FACE — settled (explicitly annotated)
    (ROLE_SIDE_FACE, PLACEMENT_BOTH_FACE): [CANDIDATE_SIDE_FACE_REINF],
    (ROLE_SIDE_FACE, PLACEMENT_SIDE):      [CANDIDATE_SIDE_FACE_REINF],
    (ROLE_SIDE_FACE, PLACEMENT_UNKNOWN):   [CANDIDATE_SIDE_FACE_REINF],

    # UNKNOWN
    (ROLE_UNKNOWN, PLACEMENT_TOP):    [
        CANDIDATE_TOP_MAIN, CANDIDATE_TOP_EXTRA, CANDIDATE_UNKNOWN,
    ],
    (ROLE_UNKNOWN, PLACEMENT_BOTTOM): [
        CANDIDATE_BOTTOM_MAIN, CANDIDATE_BOTTOM_EXTRA, CANDIDATE_UNKNOWN,
    ],
    (ROLE_UNKNOWN, PLACEMENT_UNKNOWN): [CANDIDATE_UNKNOWN],
    (ROLE_UNKNOWN, PLACEMENT_SIDE):    [CANDIDATE_SIDE_FACE_REINF, CANDIDATE_UNKNOWN],
}


class IntentNormalizer:
    """
    Remove premature intent from a semantic object and generate candidates.

    Returns (intent, candidates, deferred_reason, geometry_required, notes).
    """

    def normalize(self, role: str, placement: str, eso_meaning: str) -> tuple:
        """
        intent            = INTENT_UNKNOWN (always)
        candidates        = plausible intents from (role, placement) table
        deferred_reason   = engineering explanation string
        geometry_required = True (except for settled roles)
        notes             = audit trail
        """
        notes = []

        # Look up candidates
        candidates = self._get_candidates(role, placement)

        # Geometry requirement
        geometry_required = role not in (ROLE_STIRRUP, ROLE_SIDE_FACE)
        if geometry_required:
            deferred_reason = _GEOMETRY_REASON.get(
                role,
                "Geometry required to resolve intent."
            )
        else:
            deferred_reason = (
                "Intent settled by explicit annotation (STIRRUP or SIDE_FACE_REINFORCEMENT). "
                "No geometry needed."
            )

        # If R.2.1B had assigned a premature meaning, note the removal
        if eso_meaning and eso_meaning not in (
            "UNKNOWN", "STIRRUP", "SIDE_FACE_REINFORCEMENT"
        ):
            notes.append(
                f"Premature intent removed: ESO.engineering_meaning={eso_meaning!r} -> UNKNOWN. "
                f"Reason: {deferred_reason}"
            )
        elif eso_meaning in ("STIRRUP", "SIDE_FACE_REINFORCEMENT"):
            notes.append(
                f"Intent retained as settled candidate: {eso_meaning!r}"
            )
        else:
            notes.append("Intent already UNKNOWN in ESO — no removal needed.")

        notes.append(
            f"Generated {len(candidates)} candidate(s): {candidates}"
        )

        return INTENT_UNKNOWN, candidates, deferred_reason, geometry_required, notes

    # ── Private ──────────────────────────────────────────────────────────────

    def _get_candidates(self, role: str, placement: str) -> List[str]:
        """Lookup candidates from table, with fallback."""
        key = (role, placement)
        if key in _CANDIDATE_TABLE:
            return list(_CANDIDATE_TABLE[key])

        # Fallback: try (role, UNKNOWN)
        fallback_key = (role, PLACEMENT_UNKNOWN)
        if fallback_key in _CANDIDATE_TABLE:
            return list(_CANDIDATE_TABLE[fallback_key])

        return [CANDIDATE_UNKNOWN]
