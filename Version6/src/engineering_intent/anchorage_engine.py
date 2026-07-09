"""Evaluate supplementary anchorage intent."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_intent.intent_rules import EngineeringIntentType, MAIN_BAR_TYPES, TENSION_ROLES


class AnchorageEngine:
    """Reconstruct anchorage continuation intents."""

    RULE_ID = "K.1.RULE.ANCHORAGE.001"

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
        anchorage_rule = context.get("anchorage_rule") or {}
        if int(anchorage_rule.get("rule_count") or 0) <= 0:
            return candidates
        note_rules = context.get("general_note_rules") or {}
        if not note_rules.get("anchorage_rules"):
            return candidates
        if not context.get("support_refs"):
            return candidates

        for support_zone in context.get("support_zones") or []:
            intent_key = f"{context.get('bar_id')}::{EngineeringIntentType.SUPPLEMENTARY_ANCHORAGE.value}::{support_zone}"
            if intent_key in snapshot.get("existing_intent_ids", set()):
                continue
            candidates.append(
                {
                    "intent_key": intent_key,
                    "intent_type": EngineeringIntentType.SUPPLEMENTARY_ANCHORAGE.value,
                    "rule_id": self.RULE_ID,
                    "source_bar_id": context.get("bar_id"),
                    "source_engineering_object_id": context.get("engineering_object_id"),
                    "beam_id": context.get("beam_id"),
                    "support_zone": support_zone,
                    "support_reference": (context.get("support_refs") or ["UNKNOWN"])[
                        0 if support_zone == "LEFT_SUPPORT" else -1
                    ],
                    "development_length_mm": context.get("development_length_mm"),
                    "development_length_rule": context.get("development_length_rule"),
                    "general_note_id": "RULE::PROJECT#structural_detailing_rules.anchorage_rules",
                    "engineering_rule": self.RULE_ID,
                    "geometry_reference": context.get("geometry_reference"),
                    "engineering_graph_node": context.get("engineering_graph_node"),
                    "calculation_context_id": context.get("calculation_context_id"),
                    "evidence_confidence": 100.0,
                    "engineering_justification": (
                        f"Tension bar {context.get('bar_id')} at {support_zone} requires anchorage "
                        f"continuation per General Notes anchorage rules."
                    ),
                    "reconstruct": True,
                    "context": context,
                }
            )
        return candidates
