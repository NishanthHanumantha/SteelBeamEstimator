"""
semantic_candidate_builder.py — Generate intent candidates from semantic evidence.
MODEL_VERSION: 7.12.0

Extends the base candidate table from IntentNormalizer with additional semantic
signals from modifiers and flags to produce a richer, more precise candidate set.

Examples from reference drawings:
  B1:  S.F.R.  → only candidate: SIDE_FACE_REINFORCEMENT (no geometry needed)
  B1:  O.E.F.  → confirms BOTH_FACE placement, adds bilateral intent note
  B8:  2-Y16@TOP near span boundary → both TOP_MAIN and TOP_EXTRA are plausible
  B2:  2-Y20@BOTTOM near support    → BOTTOM_EXTRA plausible (short bar evidence)
"""
from __future__ import annotations

from typing import Any, Dict, List

from .fact_models import (
    ROLE_STIRRUP,
    ROLE_SIDE_FACE,
    PLACEMENT_TOP,
    PLACEMENT_BOTTOM,
    CANDIDATE_TOP_MAIN,
    CANDIDATE_TOP_EXTRA,
    CANDIDATE_BOTTOM_MAIN,
    CANDIDATE_BOTTOM_EXTRA,
    CANDIDATE_SIDE_FACE_REINF,
    CANDIDATE_STIRRUP,
    CANDIDATE_SUPPORT_TOP,
    CANDIDATE_SUPPORT_BOTTOM,
)


class SemanticCandidateBuilder:
    """
    Refine intent candidates using semantic signals (modifiers, flags, ESO data).

    Does NOT resolve intent — only adjusts candidate probabilities/ordering.
    Candidates are returned as an ordered list (higher confidence first).
    """

    def refine(
        self,
        base_candidates: List[str],
        role: str,
        placement: str,
        modifiers: List[str],
        semantic_flags: List[str],
        eso: Dict[str, Any],
    ) -> tuple:
        """
        Returns (refined_candidates: list[str], refinement_notes: list[str]).
        """
        candidates = list(base_candidates)
        notes = []

        # ── Settled roles: return immediately ────────────────────────────────
        if role == ROLE_STIRRUP:
            return [CANDIDATE_STIRRUP], ["STIRRUP: single settled candidate"]

        if role == ROLE_SIDE_FACE:
            return [CANDIDATE_SIDE_FACE_REINF], [
                "SIDE_FACE: single settled candidate (S.F.R. explicit)"
            ]

        # ── Semantic modifier signals ─────────────────────────────────────────
        mod_set = set(modifiers)
        flag_set = set(semantic_flags)

        if "ONE_EACH_FACE" in mod_set or "BOTH_FACES" in mod_set:
            # Bilateral placement confirmed — likely side face or bilateral top/bottom
            notes.append(
                "ONE_EACH_FACE/BOTH_FACES modifier: bilateral placement confirmed"
            )

        if "U_BAR" in mod_set:
            # U-bar typically used as side face reinforcement or support bar
            if CANDIDATE_SIDE_FACE_REINF not in candidates:
                candidates.insert(0, CANDIDATE_SIDE_FACE_REINF)
            notes.append("U_BAR modifier: SIDE_FACE_REINFORCEMENT promoted to front")

        # ── R.2.1B original role signals ──────────────────────────────────────
        original_r1 = eso.get("original_r1_role", "")

        # If R.1 originally said TOP_EXTRA or BOTTOM_EXTRA, that candidate
        # should be listed early (it was based on relative-qty within-beam heuristic)
        if original_r1 == "TOP_EXTRA" and CANDIDATE_TOP_EXTRA in candidates:
            candidates = [CANDIDATE_TOP_EXTRA] + [
                c for c in candidates if c != CANDIDATE_TOP_EXTRA
            ]
            notes.append(
                f"R.1 original role TOP_EXTRA: promoted to front of candidates"
            )
        elif original_r1 == "BOTTOM_EXTRA" and CANDIDATE_BOTTOM_EXTRA in candidates:
            candidates = [CANDIDATE_BOTTOM_EXTRA] + [
                c for c in candidates if c != CANDIDATE_BOTTOM_EXTRA
            ]
            notes.append(
                f"R.1 original role BOTTOM_EXTRA: promoted to front of candidates"
            )

        # ── Diameter-based heuristics (engineering rule) ──────────────────────
        diameter = float(eso.get("diameter") or 0.0)
        if diameter > 0:
            if placement == PLACEMENT_TOP and diameter >= 20.0:
                # Large-diameter TOP bar: more likely to be TOP_MAIN (max moment region)
                if CANDIDATE_TOP_MAIN in candidates and candidates[0] != CANDIDATE_TOP_MAIN:
                    candidates = [CANDIDATE_TOP_MAIN] + [
                        c for c in candidates if c != CANDIDATE_TOP_MAIN
                    ]
                    notes.append(
                        f"Large diameter ({diameter}mm) at TOP: TOP_MAIN promoted"
                    )
            elif placement == PLACEMENT_BOTTOM and diameter >= 20.0:
                if CANDIDATE_BOTTOM_MAIN in candidates and candidates[0] != CANDIDATE_BOTTOM_MAIN:
                    candidates = [CANDIDATE_BOTTOM_MAIN] + [
                        c for c in candidates if c != CANDIDATE_BOTTOM_MAIN
                    ]
                    notes.append(
                        f"Large diameter ({diameter}mm) at BOTTOM: BOTTOM_MAIN promoted"
                    )

        if not notes:
            notes.append("No semantic refinement applied — base candidates retained")

        return candidates, notes
