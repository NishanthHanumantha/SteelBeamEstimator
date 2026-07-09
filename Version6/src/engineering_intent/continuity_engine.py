"""Evaluate supplementary continuity intent."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_intent.intent_rules import EngineeringIntentType, MAIN_BAR_TYPES, TENSION_ROLES


class ContinuityEngine:
    """Reconstruct structural continuity reinforcement intents."""

    RULE_ID = "K.1.RULE.CONTINUITY.001"

    def evaluate(self, context: dict[str, Any], snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        candidates: List[dict[str, Any]] = []
        if str(context.get("role")) not in TENSION_ROLES:
            return candidates
        if str(context.get("bar_type")) not in MAIN_BAR_TYPES:
            return candidates
        if context.get("calculation_status") != "COMPLETE":
            return candidates
        continuity_beams = context.get("continuity_beams") or []
        if not continuity_beams:
            return candidates
        if not context.get("support_refs"):
            return candidates

        for adjacent_beam in continuity_beams:
            intent_key = (
                f"{context.get('bar_id')}::{EngineeringIntentType.SUPPLEMENTARY_CONTINUATION.value}::{adjacent_beam}"
            )
            if intent_key in snapshot.get("existing_intent_ids", set()):
                continue
            candidates.append(
                {
                    "intent_key": intent_key,
                    "intent_type": EngineeringIntentType.SUPPLEMENTARY_CONTINUATION.value,
                    "rule_id": self.RULE_ID,
                    "source_bar_id": context.get("bar_id"),
                    "source_engineering_object_id": context.get("engineering_object_id"),
                    "beam_id": context.get("beam_id"),
                    "adjacent_beam_id": adjacent_beam,
                    "support_zone": "SHARED_SUPPORT",
                    "support_reference": (context.get("support_refs") or ["UNKNOWN"])[0],
                    "general_note_id": "KNOWLEDGE::GENERAL_NOTES",
                    "engineering_rule": self.RULE_ID,
                    "geometry_reference": context.get("geometry_reference"),
                    "engineering_graph_node": context.get("engineering_graph_node"),
                    "calculation_context_id": context.get("calculation_context_id"),
                    "evidence_confidence": 100.0,
                    "engineering_justification": (
                        f"Beam {context.get('beam_id')} shares support with {adjacent_beam}; "
                        f"bar {context.get('bar_id')} requires continuity reinforcement."
                    ),
                    "reconstruct": True,
                    "context": context,
                }
            )
        return candidates
