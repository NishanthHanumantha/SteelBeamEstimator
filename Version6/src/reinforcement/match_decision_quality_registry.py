"""Registry export for match decision quality metadata."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.match_decision_quality import (
    ALGORITHM_VERSION,
    build_quality_summary,
    shared_algorithm_node,
)


class MatchDecisionQualityRegistry:
    """Build project-level decision quality registry and algorithm export."""

    @staticmethod
    def build_registry(decisions: List[dict[str, Any]]) -> dict[str, Any]:
        entries = [
            {
                "decision_id": item.get("decision_id"),
                "detail_identity_id": item.get("detail_identity_id"),
                "confidence_level": item.get("confidence_level"),
                "algorithm_version": item.get("algorithm_info", {}).get(
                    "algorithm_version", ALGORITHM_VERSION
                ),
                "quality_status": item.get("decision_quality", {}).get("quality_status"),
                "requires_manual_review": item.get("requires_manual_review"),
            }
            for item in decisions
        ]
        return {
            "namespace": "DECISION_QUALITY",
            "decision_count": len(entries),
            "decision_algorithm_version": ALGORITHM_VERSION,
            "decision_quality_summary": build_quality_summary(decisions),
            "entries": entries,
        }

    @staticmethod
    def build_quality_export(decisions: List[dict[str, Any]]) -> dict[str, Any]:
        return {
            "phase": "Phase G.2.7",
            "decision_algorithm_version": ALGORITHM_VERSION,
            "decision_quality_summary": build_quality_summary(decisions),
            "match_decisions": decisions,
        }

    @staticmethod
    def build_algorithm_export() -> dict[str, Any]:
        return {
            "phase": "Phase G.2.7",
            "algorithm_version": ALGORITHM_VERSION,
            "algorithms": [shared_algorithm_node()],
        }
