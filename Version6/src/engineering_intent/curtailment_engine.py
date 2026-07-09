"""Evaluate supplementary curtailment intent."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_intent.intent_rules import EngineeringIntentType, MAIN_BAR_TYPES, TENSION_ROLES


class CurtailmentEngine:
    """Reconstruct curtailment/lap splice continuation intents."""

    RULE_ID = "K.1.RULE.CURTAILMENT.001"

    def evaluate(self, context: dict[str, Any], snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        candidates: List[dict[str, Any]] = []
        if str(context.get("role")) not in TENSION_ROLES:
            return candidates
        if str(context.get("bar_type")) not in MAIN_BAR_TYPES:
            return candidates
        if context.get("calculation_status") != "COMPLETE":
            return candidates
        note_rules = context.get("general_note_rules") or {}
        if not note_rules.get("lap_rules"):
            return candidates
        lap_rule = context.get("lap_rule") or {}
        if int(lap_rule.get("rule_count") or 0) <= 0 and not note_rules.get("lap_rules"):
            return candidates

        intent_key = f"{context.get('bar_id')}::{EngineeringIntentType.SUPPLEMENTARY_CURTAILMENT.value}::SPAN"
        if intent_key in snapshot.get("existing_intent_ids", set()):
            return candidates

        candidates.append(
            {
                "intent_key": intent_key,
                "intent_type": EngineeringIntentType.SUPPLEMENTARY_CURTAILMENT.value,
                "rule_id": self.RULE_ID,
                "source_bar_id": context.get("bar_id"),
                "source_engineering_object_id": context.get("engineering_object_id"),
                "beam_id": context.get("beam_id"),
                "support_zone": "SPAN",
                "support_reference": context.get("beam_id"),
                "general_note_id": "RULE::PROJECT#structural_detailing_rules.lap_rules",
                "engineering_rule": self.RULE_ID,
                "geometry_reference": context.get("geometry_reference"),
                "engineering_graph_node": context.get("engineering_graph_node"),
                "calculation_context_id": context.get("calculation_context_id"),
                "evidence_confidence": 100.0,
                "engineering_justification": (
                    f"Bar {context.get('bar_id')} in span requires curtailment/lap splice "
                    f"per General Notes lap rules."
                ),
                "reconstruct": True,
                "context": context,
            }
        )
        return candidates
