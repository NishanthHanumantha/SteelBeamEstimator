"""
hypothesis_ranker.py — Generate deterministically ranked IntentHypotheses.
MODEL_VERSION: 7.12.1

Two-stage pipeline per annotation:

  Stage 1: Base ranking
    Lookup (role, placement) in BASE_RANKINGS table.
    Produces ordered (intent, reason) list.

  Stage 2: Deterministic reordering
    Apply REORDER_RULES in sequence.
    Each rule may move one intent to priority 1.
    Later rules win over earlier rules.
    Priority sequence always starts at 1, increments by 1.

No geometry. No ML. No probabilities.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .evidence_models import IntentHypothesis, INTENT_UNKNOWN
from .hypothesis_rules import (
    BASE_RANKINGS,
    REORDER_RULES,
    TOP_MAIN, TOP_EXTRA, CONTINUOUS_TOP, SUPPORT_TOP,
    BOTTOM_MAIN, BOTTOM_EXTRA, CONTINUOUS_BOTTOM, SUPPORT_BOTTOM,
    SIDE_FACE_REINF, UNKNOWN_INTENT,
)


class HypothesisRanker:
    """
    Generate a deterministically ranked list of IntentHypothesis objects.

    Input:  role, placement, observable_evidence dict (diameter, modifiers, flags, r1_role)
    Output: List[IntentHypothesis] with sequential priorities starting at 1.
    """

    def rank(
        self,
        role:      str,
        placement: str,
        evidence:  Dict[str, Any],
    ) -> Tuple[List[IntentHypothesis], List[str]]:
        """
        Returns (hypotheses, applied_rules_log).
        hypotheses:       ordered list of IntentHypothesis
        applied_rules_log: which reorder rules fired
        """
        applied: List[str] = []

        # Stage 1: Base ranking
        ranked_pairs = self._get_base_ranking(role, placement)

        # Stage 2: Apply deterministic reorder rules
        ranked_pairs, applied = self._apply_reorder_rules(
            ranked_pairs, evidence, role, placement
        )

        # Assign sequential priorities, build frozen hypotheses
        hypotheses = [
            IntentHypothesis(intent=intent, priority=idx + 1, reason=reason)
            for idx, (intent, reason) in enumerate(ranked_pairs)
        ]

        return hypotheses, applied

    # ── Stage 1 ───────────────────────────────────────────────────────────────

    def _get_base_ranking(
        self, role: str, placement: str
    ) -> List[Tuple[str, str]]:
        """Lookup base ranking table; fallback to (role, UNKNOWN); then generic."""
        key = (role, placement)
        if key in BASE_RANKINGS:
            return list(BASE_RANKINGS[key])

        fallback = (role, "UNKNOWN")
        if fallback in BASE_RANKINGS:
            return list(BASE_RANKINGS[fallback])

        return [(UNKNOWN_INTENT, "Role/placement combination not in ranking table")]

    # ── Stage 2 ───────────────────────────────────────────────────────────────

    def _apply_reorder_rules(
        self,
        pairs:     List[Tuple[str, str]],
        evidence:  Dict[str, Any],
        role:      str,
        placement: str,
    ) -> Tuple[List[Tuple[str, str]], List[str]]:
        applied: List[str] = []

        for rule in REORDER_RULES:
            try:
                triggered = rule["trigger"](evidence)
            except Exception:
                continue

            if not triggered:
                continue

            # Special context-dependent rules
            if rule.get("is_diameter_rule"):
                pairs, fired = self._apply_large_diameter(pairs, role, placement, rule)
            elif rule.get("is_continuous_rule"):
                pairs, fired = self._promote(
                    pairs,
                    CONTINUOUS_TOP if placement == "TOP" else CONTINUOUS_BOTTOM,
                    rule["reason"],
                )
            elif rule.get("is_support_rule"):
                pairs, fired = self._promote(
                    pairs,
                    SUPPORT_TOP if placement == "TOP" else SUPPORT_BOTTOM,
                    rule["reason"],
                )
            else:
                target = rule.get("promote")
                if target:
                    pairs, fired = self._promote(pairs, target, rule["reason"])
                else:
                    fired = False

            if fired:
                applied.append(rule["rule_id"])

        return pairs, applied

    def _apply_large_diameter(
        self,
        pairs:     List[Tuple[str, str]],
        role:      str,
        placement: str,
        rule:      Dict[str, Any],
    ) -> Tuple[List[Tuple[str, str]], bool]:
        """Promote the contextual MAIN candidate for large-diameter bars."""
        if placement == "TOP":
            target = TOP_MAIN
        elif placement == "BOTTOM":
            target = BOTTOM_MAIN
        else:
            return pairs, False
        return self._promote(pairs, target, rule["reason"])

    @staticmethod
    def _promote(
        pairs:  List[Tuple[str, str]],
        intent: str,
        reason: str,
    ) -> Tuple[List[Tuple[str, str]], bool]:
        """
        Move `intent` to position 0 with updated `reason`.
        If intent is not in the list, do nothing.
        Returns (updated_pairs, did_fire).
        """
        for i, (cand, _) in enumerate(pairs):
            if cand == intent:
                if i == 0:
                    # Already at front — update reason
                    pairs[0] = (intent, reason)
                else:
                    pairs.pop(i)
                    pairs.insert(0, (intent, reason))
                return pairs, True
        return pairs, False
