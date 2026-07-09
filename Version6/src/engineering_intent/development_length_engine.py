"""Evaluate supplementary development length intent."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_intent.intent_rules import EngineeringIntentType, MAIN_BAR_TYPES, TENSION_ROLES


class DevelopmentLengthEngine:
    """Reconstruct development length continuation intents."""

    RULE_ID = "K.1.RULE.DEV_LENGTH.001"

    def evaluate(self, context: dict[str, Any], snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        candidates: List[dict[str, Any]] = []
        if str(context.get("role")) not in TENSION_ROLES:
            return candidates
        if str(context.get("bar_type")) not in MAIN_BAR_TYPES:
            return candidates
        if context.get("calculation_status") != "COMPLETE":
            return candidates
        if not context.get("development_length_mm"):
            return candidates
        if not context.get("engineering_object_id"):
            return candidates
        if not context.get("specification_id"):
            return candidates
        if not context.get("support_refs"):
            return candidates
        if not self._has_development_length_rule(context):
            return candidates

        for support_zone in context.get("support_zones") or []:
            intent_key = f"{context.get('bar_id')}::{EngineeringIntentType.SUPPLEMENTARY_DEVELOPMENT_LENGTH.value}::{support_zone}"
            if intent_key in snapshot.get("existing_intent_ids", set()):
                continue
            candidates.append(
                {
                    "intent_key": intent_key,
                    "intent_type": EngineeringIntentType.SUPPLEMENTARY_DEVELOPMENT_LENGTH.value,
                    "rule_id": self.RULE_ID,
                    "source_bar_id": context.get("bar_id"),
                    "source_engineering_object_id": context.get("engineering_object_id"),
                    "beam_id": context.get("beam_id"),
                    "support_zone": support_zone,
                    "support_reference": self._support_for_zone(context, support_zone),
                    "development_length_mm": context.get("development_length_mm"),
                    "development_length_rule": context.get("development_length_rule"),
                    "general_note_id": "KNOWLEDGE::GENERAL_NOTES#development_tables",
                    "engineering_rule": self.RULE_ID,
                    "geometry_reference": context.get("geometry_reference"),
                    "engineering_graph_node": context.get("engineering_graph_node"),
                    "calculation_context_id": context.get("calculation_context_id"),
                    "evidence_confidence": 100.0,
                    "engineering_justification": (
                        f"Tension bar {context.get('bar_id')} at {support_zone} requires "
                        f"Ld={context.get('development_length_mm')}mm per General Notes TABLE-1."
                    ),
                    "reconstruct": True,
                    "context": context,
                }
            )
        return candidates

    @staticmethod
    def _has_development_length_rule(context: dict[str, Any]) -> bool:
        note_rules = context.get("general_note_rules") or {}
        return bool(note_rules.get("development_tables") or context.get("development_length_entry"))

    @staticmethod
    def _support_for_zone(context: dict[str, Any], support_zone: str) -> str:
        refs = context.get("support_refs") or []
        if not refs:
            return "UNKNOWN"
        if support_zone == "LEFT_SUPPORT":
            return str(refs[0])
        if support_zone == "RIGHT_SUPPORT":
            return str(refs[-1])
        return str(refs[0])
