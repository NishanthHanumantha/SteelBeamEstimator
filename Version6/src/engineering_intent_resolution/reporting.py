"""Reporting helpers for engineering intent resolution."""

from __future__ import annotations

from typing import Any, Dict, List

from src.engineering_intent_resolution.resolution_collector import MODEL_VERSION, PHASE


class ResolutionReporting:
    """Build report and recommendations payloads."""

    @staticmethod
    def build_report(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": result.get("run_timestamp"),
            "statistics": result.get("statistics"),
            "health": result.get("health"),
            "summary": result.get("summary"),
            "production_integration": result.get("production_integration"),
            "validation_status": (result.get("validation") or {}).get("status"),
            "decision_count": len(result.get("decisions") or []),
            "conflict_count": len(result.get("conflicts") or []),
            "merge_count": len(result.get("merges") or []),
            "graph_count": len(result.get("graphs") or []),
        }

    @staticmethod
    def build_recommendations(
        decisions: List[dict[str, Any]],
        conflicts: List[dict[str, Any]],
    ) -> dict[str, Any]:
        hold_decisions = [
            {
                "decision_id": item.get("decision_id"),
                "reason": "production_eligibility=HOLD",
            }
            for item in decisions
            if item.get("production_eligibility") == "HOLD"
        ]
        return {
            "hold_decisions": hold_decisions,
            "unresolved_conflict_hints": [
                item.get("conflict_id")
                for item in conflicts
                if not item.get("resolved")
            ],
            "next_phase_hints": [
                "Future phases should consume Engineering Decisions for execution behaviour.",
                "K.2+ should not re-evaluate raw overlapping intents for production detailing.",
            ],
        }
