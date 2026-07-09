"""Engineering intent reconstruction reporting."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_intent.intent_rules import INTENT_RULES


class IntentReporting:
    """Build intent reports and recommendations."""

    @staticmethod
    def build_report(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": result.get("phase"),
            "model_version": result.get("model_version"),
            "engine_version": result.get("engine_version"),
            "run_timestamp": result.get("run_timestamp"),
            "summary": result.get("summary"),
            "statistics": result.get("statistics"),
            "health": result.get("health"),
            "validation": result.get("validation"),
            "production_integration": result.get("production_integration"),
            "intent_object_count": len(result.get("intent_objects") or []),
        }

    @staticmethod
    def build_rules_export() -> dict[str, Any]:
        return {
            "rule_count": len(INTENT_RULES),
            "rules": INTENT_RULES,
        }

    @staticmethod
    def build_recommendations(
        candidates: List[dict[str, Any]],
        decisions: List[dict[str, Any]],
    ) -> dict[str, Any]:
        rejected = [
            {
                "intent_key": item.get("intent_key"),
                "reason": "Eligibility checks failed",
                "checks": item.get("checks"),
            }
            for item in decisions
            if item.get("decision") != "APPROVE"
        ]
        return {
            "recommendation_count": len(rejected),
            "recommendations": rejected[:50],
            "next_phase_hints": [
                "K.2 — Expand continuity rule coverage across beam groups",
                "K.3 — Curtailment zone refinement from span analysis",
                "K.4 — Intent-driven steel contribution validation",
            ],
        }
