"""Registry export for match decisions."""

from __future__ import annotations

from typing import Any, List


class MatchDecisionRegistry:
    """Build project-level match decision registry."""

    @staticmethod
    def build(
        decisions: List[dict[str, Any]],
        drawing_id: str = "",
        drawing_set_id: str = "",
        floor_id: str = "",
    ) -> dict[str, Any]:
        entries = [
            {
                "decision_id": item.get("decision_id"),
                "detail_identity_id": item.get("detail_identity_id"),
                "recommended_candidate_id": item.get("recommended_candidate_id"),
                "recommended_beam_context_id": item.get("recommended_beam_context_id"),
                "decision_status": item.get("decision_status"),
                "decision_reason": item.get("decision_reason"),
                "requires_manual_review": item.get("requires_manual_review"),
                "confidence": item.get("confidence"),
                "candidate_count": item.get("candidate_count", 0),
                "confidence_level": item.get("confidence_level"),
                "algorithm_version": item.get("algorithm_info", {}).get("algorithm_version"),
                "quality_status": item.get("decision_quality", {}).get("quality_status"),
            }
            for item in decisions
        ]
        return {
            "namespace": "MATCH_DECISION",
            "drawing_id": drawing_id,
            "drawing_set_id": drawing_set_id,
            "floor_id": floor_id,
            "decision_count": len(entries),
            "decisions": entries,
        }
